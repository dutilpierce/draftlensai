"""Fix Mode multi-stage pipeline: tri-review on candidate, alignment audit, thrash guards."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from draftlens_api.domain.models import (
    ArbitrationDecision,
    DocumentBlock,
    IterativeReviewConfig,
    ProposedEdit,
    ReviewJobConfig,
)
from draftlens_api.engine.cycle_ledger_compare import detect_edit_signature_thrash, _edit_cycle_signature
from draftlens_api.engine.final_fix_alignment import run_final_fix_alignment_audit
from draftlens_api.engine.iterative_convergence import apply_plaintext_edits, run_iterative_convergence


def _blk(text: str = "The contract term alpha is binding.") -> DocumentBlock:
    return DocumentBlock(block_id="b1", char_start=0, char_end=len(text), text=text)


def test_fix_mode_tri_reviews_when_pairwise_clusters_zero() -> None:
    """Fix mode must not short-circuit convergence before tri-review on the corrected candidate."""

    async def inner() -> None:
        calls = {"n": 0}

        async def spy_reviewer(**kwargs):
            calls["n"] += 1
            return [], None

        arb = ArbitrationDecision(executive_summary="e", issues=[], proposed_edits=[])
        ir = IterativeReviewConfig(enabled=True, max_cycles_fix_mode=3)
        cfg = ReviewJobConfig(main_original_filename="m.docx", output_mode="fix", iterative_review=ir)
        text = _blk().text
        state = {
            "arbitration_decision": arb.model_dump(mode="json"),
            "blocks": [_blk(text).model_dump(mode="json")],
            "normalized_text": text,
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

        async def fake_arbiter(**kwargs):
            iws = kwargs["issues_working"]
            return ArbitrationDecision(
                executive_summary="e",
                issues=list(iws),
                proposed_edits=[],
                resolved_conflicts=[],
            )

        with (
            patch("draftlens_api.engine.iterative_convergence._run_reviewer_role", spy_reviewer),
            patch("draftlens_api.engine.iterative_convergence._run_arbiter_once", side_effect=fake_arbiter),
        ):
            out = await run_iterative_convergence(state, cfg=cfg, registry=reg, assign=assign, emit=None)

        assert calls["n"] >= 3, "expected at least one tri-review fan-out"
        assert out["convergence_meta"].get("fix_alignment_audit_passed") is True

    asyncio.run(inner())


def test_alignment_audit_fails_when_edit_not_applied() -> None:
    doc = "hello world"
    base = "hello world"
    ed = ProposedEdit(block_id="b1", before="goodbye", after="moon", rationale="r", source_agents=["arbiter"])
    ok, errs = run_final_fix_alignment_audit(
        final_document_text=doc,
        baseline_document_text=base,
        proposed_edits=[ed],
        issues=[],
        do_not_change=None,
        material_severities={"critical", "major", "minor"},
        require_locked_term_integrity=False,
    )
    assert ok is False
    assert any("missing_after" in e for e in errs)


def test_alignment_audit_locked_term() -> None:
    base = "Keep AcmeCorp indemnity."
    final = "Keep indemnity."
    ok, errs = run_final_fix_alignment_audit(
        final_document_text=final,
        baseline_document_text=base,
        proposed_edits=[],
        issues=[],
        do_not_change="AcmeCorp",
        material_severities=set(),
        require_locked_term_integrity=True,
    )
    assert ok is False
    assert any("locked_term_removed" in e for e in errs)


def test_edit_signature_thrash_detects_oscillation() -> None:
    e1 = ProposedEdit(block_id="b1", before="x", after="y", rationale="")
    e2 = ProposedEdit(block_id="b1", before="y", after="x", rationale="")
    a = _edit_cycle_signature([e1])
    b = _edit_cycle_signature([e2])
    assert detect_edit_signature_thrash([a, b, a]) is True


def test_apply_plaintext_edits_replaces() -> None:
    ed = ProposedEdit(block_id="b1", before="alpha", after="beta", rationale="")
    out = apply_plaintext_edits("term alpha here", [ed])
    assert "beta" in out
    assert "alpha" not in out
