from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import draftlens_api.engine.iterative_convergence as iterative_convergence_mod

import httpx
import pytest

from draftlens_api.config import get_settings
from draftlens_api.domain.enums import IssueCategory, IssueSeverity
from draftlens_api.domain.models import ArbitrationDecision, DocumentBlock, Issue, IterativeReviewConfig, ReviewJobConfig
from draftlens_api.engine.iterative_convergence import run_iterative_convergence
from draftlens_api.providers.errors import GeminiJobRateLimitExhausted, GeminiSkippedUnavailable
from draftlens_api.providers.gemini_adapter import GeminiProviderAdapter
from draftlens_api.providers.llm_job_runtime import LLMJobRuntime, attach_llm_job_runtime, build_llm_job_runtime, reset_llm_job_runtime
from draftlens_api.providers.openai_params import openai_chat_temperature_params
from draftlens_api.providers.structured_output import RATE_LIMIT_EXHAUSTED
from draftlens_api.services.job_runner import _clamp_iterative_for_dev


def test_openai_gpt55_omits_temperature() -> None:
    assert openai_chat_temperature_params("gpt-5.5") == {}
    assert openai_chat_temperature_params("openai/gpt-5.5") == {}
    assert openai_chat_temperature_params("gpt-4.1") == {"temperature": 0.1}


def test_gemini_429_retries_then_returns_json() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            return httpx.Response(429, json={"error": {"code": 429, "message": "slow down"}})
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": '{"summary":"s","risks":[],"questions_for_peers":[],"issues":[]}'}
                            ]
                        }
                    }
                ]
            },
        )

    class _Client(httpx.AsyncClient):
        def __init__(self, *a, **kw):
            super().__init__(transport=httpx.MockTransport(handler), *a, **kw)

    async def inner() -> None:
        ad = GeminiProviderAdapter("test-key")
        rt = LLMJobRuntime(job_id="job-1", gemini_429_budget_remaining=8, gemini_max_backoff_seconds=90.0)
        tok = attach_llm_job_runtime(rt)
        try:
            with (
                patch("draftlens_api.providers.gemini_adapter.httpx.AsyncClient", _Client),
                patch("draftlens_api.providers.gemini_adapter.asyncio.sleep", new_callable=AsyncMock),
            ):
                out = await ad._complete_once(model_id="gemini-2.0-flash", system="sys", user="{}")
            assert "issues" in out
            assert calls["n"] == 3
            assert rt.gemini_429_budget_remaining == 6
        finally:
            reset_llm_job_runtime(tok)

    asyncio.run(inner())


def test_gemini_429_exhaustion_marks_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"code": 429}})

    class _Client(httpx.AsyncClient):
        def __init__(self, *a, **kw):
            super().__init__(transport=httpx.MockTransport(handler), *a, **kw)

    async def inner() -> None:
        ad = GeminiProviderAdapter("test-key")
        rt = LLMJobRuntime(job_id="job-2", gemini_429_budget_remaining=0)
        tok = attach_llm_job_runtime(rt)
        try:
            with (
                patch("draftlens_api.providers.gemini_adapter.httpx.AsyncClient", _Client),
                patch("draftlens_api.providers.gemini_adapter.asyncio.sleep", new_callable=AsyncMock),
            ):
                with pytest.raises(GeminiJobRateLimitExhausted):
                    await ad._complete_once(model_id="gemini-2.0-flash", system="s", user="{}")
            assert rt.gemini_unavailable_for_job is True
            assert rt.gemini_skip_reason == "GEMINI_RATE_LIMITED"
            with pytest.raises(GeminiSkippedUnavailable):
                await ad._complete_once(model_id="gemini-2.0-flash", system="s", user="{}")
        finally:
            reset_llm_job_runtime(tok)

    asyncio.run(inner())


def test_iterative_skipped_when_initial_quorum_lt_two() -> None:
    async def inner() -> None:
        spy = AsyncMock(side_effect=AssertionError("_run_reviewer_role should not run"))

        arb = ArbitrationDecision(executive_summary="e", issues=[])
        cfg = ReviewJobConfig(main_original_filename="m.docx")
        state = {
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [],
            "normalized_text": "x",
            "reviewer_phase1": {"claude": {"ok": True}, "gpt": {"ok": False}, "gemini": {"ok": False}},
        }

        class _Ad:
            configured = True

            async def complete_reviewer_json(self, **kwargs):
                return None, "unused"

        reg = SimpleNamespace(adapter=lambda _rm: _Ad())
        assign = SimpleNamespace(
            author_intent=SimpleNamespace(provider="anthropic", model_id="c"),
            skeptical_reviewer=SimpleNamespace(provider="openai", model_id="g"),
            consistency_parser=SimpleNamespace(provider="google", model_id="gem"),
            arbiter=SimpleNamespace(provider="openai", model_id="arb"),
        )

        with patch("draftlens_api.engine.iterative_convergence._run_reviewer_role", spy):
            out = await run_iterative_convergence(state, cfg=cfg, registry=reg, assign=assign, emit=None)
        spy.assert_not_called()
        assert out["convergence_meta"]["convergence_status"] == "QUORUM_LOST"
        assert out["convergence_meta"]["convergence_failure_code"] == "QUORUM_LOST"

    asyncio.run(inner())


def test_iterative_cycle_records_rate_limit_when_gemini_rate_limited() -> None:
    async def inner() -> None:
        blk = DocumentBlock(block_id="b1", char_start=0, char_end=2, text="ab")
        issue_claude = Issue(
            block_id="b1",
            span_text="ab",
            char_start=0,
            char_end=2,
            category=IssueCategory.accuracy,
            severity=IssueSeverity.major,
            title="t1",
            explanation="unique accuracy explanation token zzzz1111 for convergence ledger",
            source_agents=["claude_reviewer"],
            suggested_fix="Replace ab with the defined term from schedule A.",
        )
        issue_gpt = Issue(
            block_id="b1",
            span_text="ab",
            char_start=0,
            char_end=2,
            category=IssueCategory.clarity,
            severity=IssueSeverity.minor,
            title="t2",
            explanation="unique style explanation token yyyy2222 for convergence ledger",
            source_agents=["gpt_reviewer"],
            suggested_fix="Use cd instead for exhibit consistency.",
        )
        arb = ArbitrationDecision(executive_summary="e", issues=[issue_claude, issue_gpt])
        ir = IterativeReviewConfig(enabled=True, max_cycles_review_mode=4)
        cfg = ReviewJobConfig(main_original_filename="m.docx", iterative_review=ir)
        state = {
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [blk.model_dump(mode="json")],
            "normalized_text": "ab",
            "reviewer_phase1": {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": False}},
            "review_context": "",
            "evidence_chunks": [],
            "supporting_count": 0,
        }

        async def fake_run(*, role_key: str, **kwargs):
            if role_key == "claude":
                return [], None
            if role_key == "gpt":
                return [], RATE_LIMIT_EXHAUSTED
            return [], RATE_LIMIT_EXHAUSTED

        class _Ad:
            configured = True

            async def complete_reviewer_json(self, **kwargs):
                return None, "unused"

        reg = SimpleNamespace(adapter=lambda _rm: _Ad())
        assign = SimpleNamespace(
            author_intent=SimpleNamespace(provider="anthropic", model_id="c"),
            skeptical_reviewer=SimpleNamespace(provider="openai", model_id="g"),
            consistency_parser=SimpleNamespace(provider="google", model_id="gem"),
            arbiter=SimpleNamespace(provider="openai", model_id="arb"),
        )

        with patch("draftlens_api.engine.iterative_convergence._run_reviewer_role", side_effect=fake_run):
            out = await run_iterative_convergence(state, cfg=cfg, registry=reg, assign=assign, emit=None)

        assert out["convergence_meta"]["convergence_failure_code"] == RATE_LIMIT_EXHAUSTED
        assert out["convergence_meta"]["convergence_status"] == "PARTIAL_REVIEW_COMPLETE"

    asyncio.run(inner())


def test_reviewer_chip_aggregate_success_wins_over_later_failure() -> None:
    """Keep aligned with apps/web/lib/reviewerChips.ts aggregateReviewerChips."""

    def aggregate(log: list[dict]) -> dict[str, str]:
        order = ("anthropic", "openai", "google")
        st: dict[str, str] = {}
        lb: dict[str, str] = {}

        for ev in log:
            stage = ev["stage"]
            if not stage.startswith("MODEL_REVIEW_"):
                continue
            if "_CLAUDE_" in stage:
                p = "anthropic"
            elif "_GPT_" in stage:
                p = "openai"
            elif "_GEMINI_" in stage:
                p = "google"
            else:
                continue
            det = ev.get("detail") or {}
            mid = det.get("model_id") or ""
            short = "/".join(mid.split("/")[-2:]) if "/" in mid else mid
            ec = det.get("error_code") or ""

            if stage.endswith("_COMPLETE"):
                st[p] = "complete"
                lb[p] = f"{p} · {short or '—'} · complete"
            elif stage.endswith("_FAILED"):
                if st.get(p) == "complete":
                    continue
                if ec == "not_configured":
                    st[p] = "skipped"
                    lb[p] = f"{p} · skipped"
                elif ec == "GEMINI_DISABLED":
                    st[p] = "skipped"
                    lb[p] = f"{p} · disabled"
                elif ec in ("GEMINI_UNAVAILABLE", "RATE_LIMIT_EXHAUSTED", "GEMINI_RATE_LIMITED"):
                    st[p] = "unavailable"
                    lb[p] = f"{p} · unavailable"
                else:
                    st[p] = "failed"
                    lb[p] = f"{p} · {short or '—'} · failed"
            elif stage.endswith("_STARTED"):
                cur = st.get(p)
                if cur in ("complete", "failed", "skipped", "unavailable"):
                    continue
                st[p] = "running"
                lb[p] = f"{p} · {short or '—'} · running"

        return {k: lb[k] for k in order if k in st}

    log = [
        {"stage": "MODEL_REVIEW_CLAUDE_STARTED", "detail": {"model_id": "claude-3"}},
        {"stage": "MODEL_REVIEW_CLAUDE_COMPLETE", "detail": {"model_id": "claude-3"}},
        {"stage": "MODEL_REVIEW_CLAUDE_STARTED", "detail": {"model_id": "claude-3", "cycle_number": 2}},
        {"stage": "MODEL_REVIEW_CLAUDE_FAILED", "detail": {"model_id": "claude-3", "error_code": "PROVIDER_ERROR"}},
    ]
    out = aggregate(log)
    assert out["anthropic"].endswith("complete")


def test_status_order_includes_iterative_skipped() -> None:
    from draftlens_api.engine.status_stage_order import assert_monotonic_stage_sequence

    assert_monotonic_stage_sequence(
        [
            "CHUNKING_COMPLETE",
            "MODEL_REVIEW_CLAUDE_STARTED",
            "ITERATIVE_SKIPPED_NO_QUORUM",
            "PDF_RENDER_STARTED",
        ]
    )


def test_build_llm_job_runtime_disable_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SESSION_SECRET", "x" * 40)
    monkeypatch.setenv("DRAFTLENS_DISABLE_GEMINI", "true")
    monkeypatch.setenv("DRAFTLENS_ENVIRONMENT", "development")
    get_settings.cache_clear()
    try:
        rt = build_llm_job_runtime("j1", get_settings())
        assert rt.gemini_unavailable_for_job is True
        assert rt.gemini_disabled_intentionally is True
        assert rt.gemini_skip_reason == "INTENTIONALLY_DISABLED"
    finally:
        get_settings.cache_clear()


def test_build_llm_job_runtime_dev_soft_caps_429_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SESSION_SECRET", "x" * 40)
    monkeypatch.delenv("DRAFTLENS_GEMINI_MAX_429_RETRIES", raising=False)
    monkeypatch.delenv("DRAFTLENS_GEMINI_MAX_503_RETRIES", raising=False)
    monkeypatch.delenv("DRAFTLENS_OPENAI_MAX_429_RETRIES", raising=False)
    monkeypatch.setenv("DRAFTLENS_ENVIRONMENT", "development")
    get_settings.cache_clear()
    try:
        rt = build_llm_job_runtime("j2", get_settings())
        assert rt.gemini_429_budget_remaining == 2
        assert rt.gemini_503_budget_remaining == 2
        assert rt.openai_429_budget_remaining == 2
    finally:
        get_settings.cache_clear()


def test_clamp_iterative_for_dev_respects_review_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SESSION_SECRET", "x" * 40)
    monkeypatch.setenv("DRAFTLENS_ENVIRONMENT", "development")
    monkeypatch.setenv("DRAFTLENS_CONVERGENCE_MAX_CYCLES_REVIEW_CAP", "1")
    get_settings.cache_clear()
    try:
        s = get_settings()
        cfg = ReviewJobConfig(
            main_original_filename="m.docx",
            iterative_review=IterativeReviewConfig(enabled=True, max_cycles_review_mode=8),
        )
        out = _clamp_iterative_for_dev(cfg, s)
        assert out.iterative_review.max_cycles_review_mode == 1
    finally:
        get_settings.cache_clear()


def test_clamp_iterative_not_applied_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SESSION_SECRET", "x" * 40)
    monkeypatch.setenv("DRAFTLENS_ENVIRONMENT", "production")
    monkeypatch.setenv("DRAFTLENS_CONVERGENCE_MAX_CYCLES_REVIEW_CAP", "1")
    get_settings.cache_clear()
    try:
        s = get_settings()
        cfg = ReviewJobConfig(
            main_original_filename="m.docx",
            iterative_review=IterativeReviewConfig(max_cycles_review_mode=8),
        )
        out = _clamp_iterative_for_dev(cfg, s)
        assert out.iterative_review.max_cycles_review_mode == 8
    finally:
        get_settings.cache_clear()


def test_iterative_convergence_does_not_invoke_gemini_reviewer_when_unavailable_for_job() -> None:
    async def inner() -> None:
        blk = DocumentBlock(block_id="b1", char_start=0, char_end=2, text="ab")
        issue = Issue(
            block_id="b1",
            span_text="ab",
            char_start=0,
            char_end=2,
            category=IssueCategory.clarity,
            severity=IssueSeverity.major,
            title="t",
            explanation="e",
        )
        arb = ArbitrationDecision(executive_summary="e", issues=[issue])
        ir = IterativeReviewConfig(enabled=True, max_cycles_review_mode=2)
        cfg = ReviewJobConfig(main_original_filename="m.docx", iterative_review=ir)
        state = {
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [blk.model_dump(mode="json")],
            "normalized_text": "ab",
            "reviewer_phase1": {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": False}},
            "review_context": "",
            "evidence_chunks": [],
            "supporting_count": 0,
        }

        class _Ad:
            configured = True

            async def complete_reviewer_json(self, **kwargs):
                return (
                    {"summary": "s", "risks": [], "questions_for_peers": [], "issues": []},
                    None,
                )

        reg = SimpleNamespace(adapter=lambda _rm: _Ad())
        assign = SimpleNamespace(
            author_intent=SimpleNamespace(provider="anthropic", model_id="c"),
            skeptical_reviewer=SimpleNamespace(provider="openai", model_id="g"),
            consistency_parser=SimpleNamespace(provider="google", model_id="gem"),
            arbiter=SimpleNamespace(provider="openai", model_id="arb"),
        )

        rt = LLMJobRuntime(job_id="job-g", gemini_unavailable_for_job=True)
        tok = attach_llm_job_runtime(rt)
        gemini_roles: list[tuple[str, int]] = []
        real_run = iterative_convergence_mod._run_reviewer_role

        async def wrapper(**kwargs):
            rk = kwargs.get("role_key")
            cyc = int(kwargs.get("cycle") or 0)
            if rk == "gemini":
                gemini_roles.append((rk, cyc))
                return [], None
            return await real_run(**kwargs)

        async def fake_arbiter(**kwargs):
            iws = kwargs["issues_working"]
            return ArbitrationDecision(
                executive_summary="e",
                issues=list(iws),
                proposed_edits=[],
                resolved_conflicts=[],
            )

        try:
            with (
                patch.object(iterative_convergence_mod, "_run_reviewer_role", new=wrapper),
                patch.object(iterative_convergence_mod, "_run_arbiter_once", new=fake_arbiter),
            ):
                await run_iterative_convergence(state, cfg=cfg, registry=reg, assign=assign, emit=None)
        finally:
            reset_llm_job_runtime(tok)

        assert gemini_roles == []

    asyncio.run(inner())
