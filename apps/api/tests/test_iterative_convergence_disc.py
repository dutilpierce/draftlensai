"""Zero–material-discrepancy convergence behavior (bounded, inspectable)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from draftlens_api.domain.enums import IssueCategory, IssueSeverity
from draftlens_api.domain.models import (
    ArbitrationDecision,
    DocumentBlock,
    Issue,
    IterativeReviewConfig,
    ProposedEdit,
    ReviewJobConfig,
)
from draftlens_api.engine.iterative_convergence import run_iterative_convergence
from draftlens_api.engine.pipeline_conflicts import detect_conflicts, material_discrepancy_detect_kwargs


def _blk() -> DocumentBlock:
    return DocumentBlock(block_id="b1", char_start=0, char_end=40, text="The contract term alpha is binding.")


def _issue(**kw) -> Issue:
    base = dict(
        block_id="b1",
        span_text="alpha",
        char_start=18,
        char_end=23,
        category=IssueCategory.clarity,
        severity=IssueSeverity.minor,
        title="t",
        explanation="e",
        source_agents=["claude_reviewer"],
    )
    base.update(kw)
    return Issue(**base)


def test_duplicate_nits_same_fix_not_material_cluster() -> None:
    cfg = ReviewJobConfig(main_original_filename="m.docx")
    kw = material_discrepancy_detect_kwargs(cfg)
    a = _issue(
        issue_id="a1",
        severity=IssueSeverity.nit,
        suggested_fix="Insert Oxford comma before and in the list.",
        source_agents=["claude_reviewer"],
    )
    b = _issue(
        issue_id="b1",
        severity=IssueSeverity.nit,
        suggested_fix="Insert Oxford comma before and in the list.",
        source_agents=["gpt_reviewer"],
    )
    clusters = detect_conflicts([a, b], **kw)
    assert clusters == []


def test_review_stops_immediately_when_no_material_clusters() -> None:
    async def inner() -> None:
        spy = AsyncMock(side_effect=AssertionError("_run_reviewer_role should not run"))
        issue = _issue()
        arb = ArbitrationDecision(executive_summary="e", issues=[issue])
        ir = IterativeReviewConfig(enabled=True, max_cycles_review_mode=3)
        cfg = ReviewJobConfig(main_original_filename="m.docx", iterative_review=ir)
        state = {
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [_blk().model_dump(mode="json")],
            "normalized_text": _blk().text,
            "reviewer_phase1": {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": True}},
            "review_context": "",
            "evidence_chunks": [],
            "supporting_count": 0,
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
        assert out["convergence_meta"]["convergence_status"] == "CONVERGENCE_REACHED"
        assert out["convergence_meta"]["consensus_mode"] == "FULL_THREE_REVIEWER_CONSENSUS"
        assert out["convergence_meta"]["full_consensus_achieved"] is True
        assert out["convergence_meta"]["partial_consensus_only"] is False
        assert out["convergence_meta"]["unresolved_material_discrepancy_count"] == 0
        assert out["convergence_meta"]["stopped_with_remaining_discrepancies"] is False

    asyncio.run(inner())


def test_review_stops_immediately_partial_consensus_when_only_two_phase1_successes_strict() -> None:
    async def inner() -> None:
        spy = AsyncMock(side_effect=AssertionError("_run_reviewer_role should not run"))
        issue = _issue()
        arb = ArbitrationDecision(executive_summary="e", issues=[issue])
        ir = IterativeReviewConfig(enabled=True, max_cycles_review_mode=3, strict_three_reviewer_consensus=True)
        cfg = ReviewJobConfig(main_original_filename="m.docx", iterative_review=ir)
        state = {
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [_blk().model_dump(mode="json")],
            "normalized_text": _blk().text,
            "reviewer_phase1": {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": False}},
            "review_context": "",
            "evidence_chunks": [],
            "supporting_count": 0,
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
        assert out["convergence_meta"]["convergence_status"] == "PARTIAL_CONSENSUS"
        assert out["convergence_meta"]["consensus_mode"] == "PARTIAL_CONSENSUS"
        assert out["convergence_meta"]["full_consensus_achieved"] is False
        assert out["convergence_meta"]["partial_consensus_only"] is True
        assert out["convergence_meta"]["unresolved_material_discrepancy_count"] == 0

    asyncio.run(inner())


def test_review_stops_immediately_non_strict_allows_convergence_label_with_partial_flags() -> None:
    async def inner() -> None:
        spy = AsyncMock(side_effect=AssertionError("_run_reviewer_role should not run"))
        issue = _issue()
        arb = ArbitrationDecision(executive_summary="e", issues=[issue])
        ir = IterativeReviewConfig(enabled=True, max_cycles_review_mode=3, strict_three_reviewer_consensus=False)
        cfg = ReviewJobConfig(main_original_filename="m.docx", iterative_review=ir)
        state = {
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [_blk().model_dump(mode="json")],
            "normalized_text": _blk().text,
            "reviewer_phase1": {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": False}},
            "review_context": "",
            "evidence_chunks": [],
            "supporting_count": 0,
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
        assert out["convergence_meta"]["convergence_status"] == "CONVERGENCE_REACHED"
        assert out["convergence_meta"]["consensus_mode"] == "PARTIAL_CONSENSUS"
        assert out["convergence_meta"]["partial_consensus_only"] is True
        assert out["convergence_meta"]["full_consensus_achieved"] is False

    asyncio.run(inner())


def test_second_cycle_runs_when_material_discrepancy_present() -> None:
    async def inner() -> None:
        a = _issue(
            issue_id="i1",
            category=IssueCategory.accuracy,
            severity=IssueSeverity.major,
            source_agents=["claude_reviewer"],
            suggested_fix="Replace alpha with the defined term from section 2.",
            explanation="Accuracy rationale token unique qwer111 for dedupe separation.",
        )
        b = _issue(
            issue_id="i2",
            category=IssueCategory.clarity,
            severity=IssueSeverity.minor,
            source_agents=["gpt_reviewer"],
            suggested_fix="Use beta instead for consistency across exhibits.",
            explanation="Style rationale token unique asdf222 for dedupe separation.",
        )
        arb = ArbitrationDecision(executive_summary="e", issues=[a, b])
        ir = IterativeReviewConfig(enabled=True, max_cycles_review_mode=3)
        cfg = ReviewJobConfig(main_original_filename="m.docx", iterative_review=ir)
        state = {
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [_blk().model_dump(mode="json")],
            "normalized_text": _blk().text,
            "reviewer_phase1": {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": True}},
            "review_context": "",
            "evidence_chunks": [],
            "supporting_count": 0,
        }
        calls = {"n": 0}

        async def fake_role(**kwargs):
            calls["n"] += 1
            return [], None

        ac = {"i": 0}

        async def fake_arbiter(**kwargs):
            ac["i"] += 1
            iws = kwargs["issues_working"]
            if ac["i"] == 1:
                return ArbitrationDecision(
                    executive_summary="e", issues=list(iws), proposed_edits=[], resolved_conflicts=[]
                )
            lone = iws[0].model_copy(
                update={
                    "source_agents": ["claude_reviewer", "gpt_reviewer"],
                    "severity": IssueSeverity.major,
                }
            )
            return ArbitrationDecision(executive_summary="e", issues=[lone], proposed_edits=[], resolved_conflicts=[])

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

        with (
            patch("draftlens_api.engine.iterative_convergence._run_reviewer_role", side_effect=fake_role),
            patch("draftlens_api.engine.iterative_convergence._run_arbiter_once", side_effect=fake_arbiter),
        ):
            out = await run_iterative_convergence(state, cfg=cfg, registry=reg, assign=assign, emit=None)

        assert calls["n"] == 6
        assert out["convergence_meta"]["convergence_status"] == "CONVERGENCE_REACHED"
        assert out["convergence_meta"]["unresolved_material_discrepancy_count"] == 0

    asyncio.run(inner())


def test_max_cycles_marks_incomplete_with_remaining() -> None:
    async def inner() -> None:
        a = _issue(
            issue_id="i1",
            category=IssueCategory.accuracy,
            severity=IssueSeverity.major,
            source_agents=["claude_reviewer"],
            suggested_fix="Replace alpha with the defined term from section 2.",
            explanation="Accuracy rationale token unique qwer111 for dedupe separation.",
        )
        b = _issue(
            issue_id="i2",
            category=IssueCategory.clarity,
            severity=IssueSeverity.minor,
            source_agents=["gpt_reviewer"],
            suggested_fix="Use beta instead for consistency across exhibits.",
            explanation="Style rationale token unique asdf222 for dedupe separation.",
        )
        arb = ArbitrationDecision(executive_summary="e", issues=[a, b])
        ir = IterativeReviewConfig(enabled=True, max_cycles_review_mode=2)
        cfg = ReviewJobConfig(main_original_filename="m.docx", iterative_review=ir)
        state = {
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [_blk().model_dump(mode="json")],
            "normalized_text": _blk().text,
            "reviewer_phase1": {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": True}},
            "review_context": "",
            "evidence_chunks": [],
            "supporting_count": 0,
        }

        async def fake_arbiter(**kwargs):
            return ArbitrationDecision(
                executive_summary="e",
                issues=[a.model_copy(deep=True), b.model_copy(deep=True)],
                proposed_edits=[],
                resolved_conflicts=[],
            )

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

        with (
            patch("draftlens_api.engine.iterative_convergence._run_reviewer_role", return_value=([], None)),
            patch("draftlens_api.engine.iterative_convergence._run_arbiter_once", side_effect=fake_arbiter),
        ):
            out = await run_iterative_convergence(state, cfg=cfg, registry=reg, assign=assign, emit=None)

        assert out["convergence_meta"]["convergence_status"] == "MAX_CYCLES_REACHED"
        assert out["convergence_meta"]["stopped_due_to_max_cycles"] is True
        assert out["convergence_meta"]["stopped_with_remaining_discrepancies"] is True
        assert int(out["convergence_meta"]["unresolved_material_discrepancy_count"] or 0) > 0

    asyncio.run(inner())


def test_thrash_detection_marks_incomplete() -> None:
    async def inner() -> None:

        a = _issue(issue_id="i1", source_agents=["claude_reviewer"])
        arb = ArbitrationDecision(
            executive_summary="e",
            issues=[a],
            proposed_edits=[
                ProposedEdit(
                    edit_id="e1",
                    block_id="b1",
                    before="alpha",
                    after="beta",
                    rationale="r",
                    source_agents=["arbiter"],
                )
            ],
            resolved_conflicts=[],
        )
        ir = IterativeReviewConfig(enabled=True, max_cycles_fix_mode=4)
        cfg = ReviewJobConfig(main_original_filename="m.docx", output_mode="fix", iterative_review=ir)
        state = {
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [_blk().model_dump(mode="json")],
            "normalized_text": "The contract term alpha is binding.",
            "reviewer_phase1": {"claude": {"ok": True}, "gpt": {"ok": True}, "gemini": {"ok": True}},
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

        with (
            patch("draftlens_api.engine.iterative_convergence._run_reviewer_role", return_value=([], None)),
            patch("draftlens_api.engine.iterative_convergence._run_arbiter_once") as arb_spy,
            patch("draftlens_api.engine.iterative_convergence.detect_text_thrash", return_value=True),
        ):
            arb_spy.side_effect = lambda **kw: ArbitrationDecision(
                executive_summary="e",
                issues=[a.model_copy(deep=True)],
                proposed_edits=arb.proposed_edits,
                resolved_conflicts=[],
            )
            out = await run_iterative_convergence(state, cfg=cfg, registry=reg, assign=assign, emit=None)

        assert out["convergence_meta"]["convergence_failure_code"] == "THRASH_DETECTED"
        assert out["convergence_meta"]["stopped_with_remaining_discrepancies"] is True

    asyncio.run(inner())
