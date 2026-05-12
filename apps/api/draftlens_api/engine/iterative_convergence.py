"""
Bounded iterative convergence after the initial tri-model review + arbitration.

Deterministic, inspectable: each cycle re-runs structured reviewer passes and a
single arbiter refresh (no unbounded free-form agent chatter).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from draftlens_api.domain.enums import IssueStatus
from draftlens_api.domain.models import (
    ArbitrationDecision,
    DocumentBlock,
    Issue,
    IterativeReviewConfig,
    ProposedEdit,
    ReviewJobConfig,
)
from draftlens_api.engine.cycle_ledger_compare import (
    detect_edit_signature_thrash,
    detect_text_thrash,
    fix_mode_meets_clean_threshold,
    fix_mode_open_issues_pass_completion,
    _edit_cycle_signature,
)
from draftlens_api.engine.final_fix_alignment import run_final_fix_alignment_audit
from draftlens_api.engine.pipeline_conflicts import detect_conflicts as detect_material_conflicts
from draftlens_api.engine.pipeline_conflicts import material_discrepancy_detect_kwargs
from draftlens_api.engine.pipeline_dedupe import dedupe_findings
from draftlens_api.engine.arbitration_gate import count_structured_successes
from draftlens_api.engine.consensus_coverage import (
    configured_reviewer_slots,
    reconcile_consensus_fields,
)
from draftlens_api.engine.pipeline_prompts import arbiter_round3_system, claude_system, gemini_system, gpt_system
from draftlens_api.engine.reviewer_caps import cap_reviewer_issues
from draftlens_api.evidence import EvidenceChunk, EvidenceIndex, EvidenceRetriever
from draftlens_api.prompts.schemas import validate_arbiter_payload, validate_reviewer_payload
from draftlens_api.providers.llm_job_runtime import get_llm_job_runtime, sync_provider_instability_into_meta
from draftlens_api.providers.normalization import agent_finding_from_payload, issues_from_payload
from draftlens_api.providers.structured_output import (
    GEMINI_DISABLED,
    GEMINI_RATE_LIMITED,
    GEMINI_SERVICE_UNAVAILABLE,
    GEMINI_UNAVAILABLE,
    OPENAI_RATE_LIMITED,
    OPENAI_UNAVAILABLE,
    RATE_LIMIT_EXHAUSTED,
)
from draftlens_api.routing.model_registry import ModelRegistry
from draftlens_api.services.document_blocks import chunk_document_blocks

logger = logging.getLogger(__name__)


def _summarize_unresolved_clusters(payload: list[dict[str, Any]], *, limit: int = 14) -> list[dict[str, Any]]:
    """Compact diagnostics for material discrepancy clusters (UI + pipeline_stats)."""
    out: list[dict[str, Any]] = []
    for c in payload[:limit]:
        reasons = [str(x) for x in (c.get("reasons") or [])[:8]]
        mini: list[dict[str, Any]] = []
        for i in (c.get("issues") or [])[:5]:
            if isinstance(i, dict):
                mini.append(
                    {
                        "title": str(i.get("title", ""))[:120],
                        "severity": str(i.get("severity", "")),
                        "category": str(i.get("category", "")),
                    }
                )
        out.append({"cluster_id": c.get("cluster_id"), "reasons": reasons, "issues": mini})
    return out


EmitFn = Callable[[str, str, dict[str, Any] | None], Awaitable[None]]


def _fix_open_issue_gate(
    cfg: ReviewJobConfig,
    issues: list[Issue],
    material: set[str],
) -> tuple[bool, str | None]:
    fc = cfg.fix_mode_completion
    allow_nits = bool(fc.allow_remaining_nits and cfg.iterative_review.ignore_nits_for_fix_completion)
    return fix_mode_open_issues_pass_completion(
        issues,
        material_severities=material,
        allow_remaining_nits=allow_nits,
        require_no_open_critical=fc.require_no_open_critical,
        require_no_open_major=fc.require_no_open_major,
        require_no_open_minor=fc.require_no_open_minor,
    )


def _finalize_stopped_remaining_discrepancies(
    meta: dict[str, Any],
    *,
    convergence_status: str | None,
    unresolved_disc_count: int,
    fix_not_clean: bool,
) -> None:
    """Incomplete unless true zero-discrepancy convergence (CONVERGENCE_REACHED) was recorded."""
    fin = convergence_status or ""
    if fin == "CONVERGENCE_REACHED":
        meta["stopped_with_remaining_discrepancies"] = False
        return
    if fin == "HUMAN_FOLLOW_UP_REQUIRED":
        meta["stopped_with_remaining_discrepancies"] = True
        return
    if fin == "PARTIAL_CONSENSUS":
        meta["stopped_with_remaining_discrepancies"] = bool(
            int(unresolved_disc_count) > 0
            or fix_not_clean
            or meta.get("stopped_due_to_quorum_loss")
            or meta.get("stopped_due_to_max_cycles")
            or meta.get("stopped_due_to_provider_unavailable")
            or meta.get("stopped_due_to_fatal_arbiter_failure")
            or meta.get("convergence_failure_code") == "THRASH_DETECTED"
            or meta.get("convergence_failure_code") == "EDIT_THRASH_DETECTED"
            or meta.get("convergence_failure_code") == "ALIGNMENT_AUDIT_FAILED"
        )
        return
    meta["stopped_with_remaining_discrepancies"] = bool(
        int(unresolved_disc_count) > 0
        or fix_not_clean
        or meta.get("stopped_due_to_quorum_loss")
        or meta.get("stopped_due_to_max_cycles")
        or meta.get("stopped_due_to_provider_unavailable")
        or meta.get("stopped_due_to_fatal_arbiter_failure")
        or meta.get("convergence_failure_code") == "THRASH_DETECTED"
        or meta.get("convergence_failure_code") == "EDIT_THRASH_DETECTED"
        or meta.get("convergence_failure_code") == "ALIGNMENT_AUDIT_FAILED"
    )


def _convergence_configured_role_count(registry: ModelRegistry, assign: Any) -> int:
    """How many reviewer roles can still invoke their provider (configured + not job-disabled)."""
    rt = get_llm_job_runtime()
    n = 0
    for role_key, rm in (
        ("claude", assign.author_intent),
        ("gpt", assign.skeptical_reviewer),
        ("gemini", assign.consistency_parser),
    ):
        if not registry.adapter(rm).configured:
            continue
        if role_key == "gemini" and rt and rt.gemini_unavailable_for_job:
            continue
        if role_key == "gpt" and rt and rt.openai_unavailable_for_job:
            continue
        n += 1
    return n


async def _emit(emit: EmitFn | None, stage: str, message: str, detail: dict[str, Any] | None = None) -> None:
    if emit is None:
        return
    await emit(stage, message, detail)


def _reconcile_iterative_consensus_meta(
    meta: dict[str, Any],
    *,
    cfg: ReviewJobConfig,
    registry: ModelRegistry,
    assign: Any,
    issues_for_fix_threshold: list[Issue],
    successful_reviewer_count: int,
    pairwise_cluster_count: int,
) -> None:
    sync_provider_instability_into_meta(meta)
    ir = cfg.iterative_review
    material = set(ir.material_issue_severities)
    fix_mode = cfg.output_mode == "fix"
    fix_clean = not fix_mode or fix_mode_meets_clean_threshold(
        issues_for_fix_threshold,
        material_severities=material,
        ignore_nits=ir.ignore_nits_for_fix_completion,
    )
    reconcile_consensus_fields(
        meta,
        configured_slots=configured_reviewer_slots(registry, assign),
        successful_count=successful_reviewer_count,
        pairwise_cluster_count=pairwise_cluster_count,
        fix_mode=fix_mode,
        fix_clean=fix_clean,
        strict_three_reviewer_consensus=ir.strict_three_reviewer_consensus,
    )


def _make_evidence_retriever(state: dict[str, Any]) -> EvidenceRetriever:
    chunks = [EvidenceChunk.model_validate(x) for x in state.get("evidence_chunks") or []]
    raw_path = str(state.get("evidence_index_path") or "").strip()
    idx: EvidenceIndex | None = None
    if raw_path and Path(raw_path).is_file():
        idx = EvidenceIndex(Path(raw_path), fts_enabled=bool(state.get("evidence_fts_enabled")))
    supporting = int(state.get("supporting_count") or 0) > 0
    return EvidenceRetriever(
        chunks=chunks,
        index=idx,
        has_supporting_files=supporting,
        partial_file=bool(state.get("evidence_any_partial")),
    )


def _clamp_issue(issue: Issue, blocks: list[DocumentBlock]) -> Issue:
    blk = next((b for b in blocks if b.block_id == issue.block_id), None)
    if blk is None:
        return issue
    cs = max(blk.char_start, min(issue.char_start, blk.char_end))
    ce = max(cs, min(issue.char_end, blk.char_end))
    span = issue.span_text
    if not span.strip():
        span = blk.text[cs - blk.char_start : ce - blk.char_start] if blk.text else issue.span_text
    return issue.model_copy(update={"char_start": cs, "char_end": ce, "span_text": span})


def _build_blocks_payload(
    blocks: list[DocumentBlock],
    *,
    cfg: ReviewJobConfig,
    state: dict[str, Any],
    send_cap: int,
) -> list[dict[str, Any]]:
    retriever = _make_evidence_retriever(state)
    blocks_payload: list[dict[str, Any]] = []
    for blk in sorted(blocks, key=lambda b: (b.char_start, b.block_id)):
        body = blk.text
        truncated = False
        if len(body) > send_cap:
            half = max(200, send_cap // 2 - 40)
            body = body[:half] + "\n…[middle truncated for review context budget]…\n" + body[-half:]
            truncated = True
        rr = retriever.rank_for_block(blk, top_k=5, max_chars_each=900)
        blocks_payload.append(
            {
                "block_id": blk.block_id,
                "char_start": blk.char_start,
                "char_end": blk.char_end,
                "text": body,
                "text_truncated_for_context_budget": truncated,
                "relevant_evidence_excerpts": [
                    {
                        "chunk_id": ex.chunk_id,
                        "source_label": ex.source_label,
                        "excerpt": ex.text,
                        "relevance": round(ex.score, 4),
                        "rank_method": ex.rank_method,
                    }
                    for ex in rr.excerpts
                ],
                "evidence_note_for_block": rr.evidence_note,
            }
        )
    return blocks_payload


def _neighbor_block_ids(blocks: list[DocumentBlock], seed: set[str], window: int) -> set[str]:
    if window <= 0:
        return set(seed)
    by_id = {b.block_id: i for i, b in enumerate(sorted(blocks, key=lambda x: (x.char_start, x.block_id)))}
    ordered = sorted(blocks, key=lambda x: (x.char_start, x.block_id))
    out = set(seed)
    for bid in list(seed):
        idx = by_id.get(bid)
        if idx is None:
            continue
        for d in range(-window, window + 1):
            j = idx + d
            if 0 <= j < len(ordered):
                out.add(ordered[j].block_id)
    return out


def _select_blocks_for_cycle(
    issues: list[Issue],
    all_blocks: list[DocumentBlock],
    ir: IterativeReviewConfig,
    *,
    cycle: int,
) -> list[DocumentBlock]:
    material = set(ir.material_issue_severities)
    hot: set[str] = set()
    for it in issues:
        if it.severity.value not in material:
            continue
        if it.status in {IssueStatus.rejected, IssueStatus.deferred, IssueStatus.resolved}:
            continue
        hot.add(it.block_id)
    if ir.rerun_neighbor_blocks and hot:
        hot = _neighbor_block_ids(all_blocks, hot, ir.neighbor_window)
    if not hot:
        return []
    by_id = {b.block_id: b for b in all_blocks}
    chosen = [by_id[b] for b in sorted(hot) if b in by_id]
    if cycle >= 3 and ir.recheck_changed_blocks_only_after_cycle_1 and chosen:
        chosen = chosen[: max(1, len(chosen) // 2 + 1)]
    return chosen


def apply_plaintext_edits(text: str, edits: list[ProposedEdit]) -> str:
    """Deterministic first-occurrence replacements (longest `before` first)."""
    ordered = sorted([e for e in edits if e.before.strip()], key=lambda e: len(e.before), reverse=True)
    out = text
    for e in ordered:
        b, a = e.before, e.after
        if b in out:
            out = out.replace(b, a, 1)
    return out


async def _run_reviewer_role(
    *,
    state: dict[str, Any],
    cfg: ReviewJobConfig,
    blocks: list[DocumentBlock],
    role_key: str,
    resolved: Any,
    system_builder,
    source_tag: str,
    registry: ModelRegistry,
    emit: EmitFn | None,
    cycle: int,
) -> tuple[list[Issue], str | None]:
    adapter = registry.adapter(resolved)
    has_supporting = int(state.get("supporting_count") or 0) > 0
    send_cap = int(cfg.max_block_send_chars)
    blocks_payload = _build_blocks_payload(blocks, cfg=cfg, state=state, send_cap=send_cap)
    user_obj: dict[str, Any] = {
        "static_review_context": (state.get("review_context") or "") + f"\n\n[Convergence cycle {cycle}]",
        "user_context_text": cfg.context_text or "",
        "do_not_change": cfg.do_not_change or "",
        "document_type": cfg.document_type.value,
        "review_focus": cfg.review_focus,
        "document_blocks": blocks_payload,
        "large_document_limits": {
            "max_blocks_for_review": cfg.max_blocks_for_review,
            "blocks_omitted": 0,
            "max_block_send_chars": send_cap,
        },
    }
    user = json.dumps(user_obj, ensure_ascii=False)
    started = {
        "claude": "MODEL_REVIEW_CLAUDE_STARTED",
        "gpt": "MODEL_REVIEW_GPT_STARTED",
        "gemini": "MODEL_REVIEW_GEMINI_STARTED",
    }[role_key]
    done = {
        "claude": "MODEL_REVIEW_CLAUDE_COMPLETE",
        "gpt": "MODEL_REVIEW_GPT_COMPLETE",
        "gemini": "MODEL_REVIEW_GEMINI_COMPLETE",
    }[role_key]
    failed = {
        "claude": "MODEL_REVIEW_CLAUDE_FAILED",
        "gpt": "MODEL_REVIEW_GPT_FAILED",
        "gemini": "MODEL_REVIEW_GEMINI_FAILED",
    }[role_key]

    if not adapter.configured:
        await _emit(
            emit,
            failed,
            f"{role_key} reviewer unavailable.",
            {
                "cycle_number": cycle,
                "error_code": "not_configured",
                "percent_complete": 82,
                "provider": resolved.provider,
                "model_id": resolved.model_id,
                "reviewer": role_key,
            },
        )
        return [], "not_configured"

    rt = get_llm_job_runtime()
    if role_key == "gemini" and rt and rt.gemini_unavailable_for_job:
        code = GEMINI_DISABLED if rt.gemini_disabled_intentionally else GEMINI_UNAVAILABLE
        detail: dict[str, Any] = {
            "cycle_number": cycle,
            "error_code": code,
            "gemini_skip_reason": rt.gemini_skip_reason,
            "percent_complete": 82,
            "provider": resolved.provider,
            "model_id": resolved.model_id,
            "reviewer": role_key,
        }
        if rt.gemini_disabled_intentionally:
            detail["gemini_job_state"] = "INTENTIONALLY_DISABLED"
        else:
            detail["gemini_job_state"] = "GEMINI_SKIPPED_FOR_REMAINDER_OF_JOB"
            if (rt.gemini_skip_reason or "") == "GEMINI_RATE_LIMITED":
                detail["gemini_rate_limited"] = True
            if (rt.gemini_skip_reason or "") == "GEMINI_SERVICE_UNAVAILABLE":
                detail["gemini_service_unavailable"] = True
        gem_msg = f"{role_key} skipped (unavailable for this job)."
        if (rt.gemini_skip_reason or "") == "GEMINI_RATE_LIMITED":
            gem_msg = "Gemini rate-limited — continuing with available reviewers."
        elif (rt.gemini_skip_reason or "") == "GEMINI_SERVICE_UNAVAILABLE":
            gem_msg = "Gemini temporarily unavailable — continuing with available reviewers."
        await _emit(
            emit,
            failed,
            gem_msg,
            detail,
        )
        return [], code

    if role_key == "gpt" and rt and rt.openai_unavailable_for_job:
        detail_gpt: dict[str, Any] = {
            "cycle_number": cycle,
            "error_code": OPENAI_UNAVAILABLE,
            "openai_skip_reason": rt.openai_skip_reason,
            "percent_complete": 82,
            "provider": resolved.provider,
            "model_id": resolved.model_id,
            "reviewer": role_key,
            "openai_job_state": "PROVIDER_SKIPPED_FOR_REMAINDER_OF_JOB",
        }
        if (rt.openai_skip_reason or "") == "OPENAI_RATE_LIMITED":
            detail_gpt["openai_rate_limited"] = True
        gpt_msg = "GPT unavailable for this job — continuing with available reviewers."
        if (rt.openai_skip_reason or "") == "OPENAI_RATE_LIMITED":
            gpt_msg = "GPT rate-limited — continuing with available reviewers."
        await _emit(emit, failed, gpt_msg, detail_gpt)
        return [], OPENAI_UNAVAILABLE

    await _emit(
        emit,
        started,
        f"{role_key} convergence review started.",
        {
            "cycle_number": cycle,
            "percent_complete": 80,
            "reviewer": role_key,
            "provider": resolved.provider,
            "model_id": resolved.model_id,
        },
    )
    payload, err = await adapter.complete_reviewer_json(
        model_id=resolved.model_id,
        system=system_builder(cfg, has_supporting=has_supporting),
        user=user,
        validate=validate_reviewer_payload,
    )
    if payload is None:
        code = err or "INVALID_JSON"
        await _emit(
            emit,
            failed,
            f"{role_key} reviewer failed.",
            {
                "cycle_number": cycle,
                "error_code": code,
                "percent_complete": 82,
                "provider": resolved.provider,
                "model_id": resolved.model_id,
                "reviewer": role_key,
            },
        )
        return [], code
    try:
        validate_reviewer_payload(payload)
    except ValidationError:
        await _emit(
            emit,
            failed,
            f"{role_key} schema mismatch.",
            {
                "cycle_number": cycle,
                "error_code": "SCHEMA_MISMATCH",
                "percent_complete": 82,
                "provider": resolved.provider,
                "model_id": resolved.model_id,
                "reviewer": role_key,
            },
        )
        return [], "SCHEMA_MISMATCH"
    finding = agent_finding_from_payload(payload, role=source_tag)
    issues = [_clamp_issue(i, blocks) for i in finding.issue_candidates]
    issues = cap_reviewer_issues(issues)
    for it in issues:
        if source_tag not in it.source_agents:
            it.source_agents.append(source_tag)
        it.discovered_in_cycle = cycle
        it.cycle_number = cycle
    await _emit(
        emit,
        done,
        f"{role_key} convergence review complete.",
        {
            "cycle_number": cycle,
            "issues": len(issues),
            "percent_complete": 83,
            "reviewer": role_key,
            "provider": resolved.provider,
            "model_id": resolved.model_id,
        },
    )
    return issues, None


async def _run_arbiter_once(
    *,
    state: dict[str, Any],
    cfg: ReviewJobConfig,
    issues_working: list[Issue],
    conflict_clusters: list[dict[str, Any]],
    registry: ModelRegistry,
    assign: Any,
    emit: EmitFn | None,
    cycle: int,
) -> ArbitrationDecision:
    adapter = registry.adapter(assign.arbiter)
    if not adapter.configured:
        raise RuntimeError("arbiter_not_configured")

    blocks = [DocumentBlock.model_validate(b) for b in state.get("blocks") or []]
    retriever = _make_evidence_retriever(state)
    hints: list[dict[str, Any]] = []
    for c in conflict_clusters:
        its_raw = c.get("issues") or []
        if len(its_raw) < 2:
            continue
        its = [Issue.model_validate(x) for x in its_raw]
        blk_id = its[0].block_id
        blk = next((b for b in blocks if b.block_id == blk_id), blocks[0] if blocks else None)
        if blk is None:
            continue
        rr = retriever.rank_for_block(blk, top_k=4, max_chars_each=650)
        hints.append(
            {
                "cluster_id": c.get("cluster_id"),
                "block_id": blk_id,
                "ranked_evidence_excerpts": [
                    {"source": ex.source_label, "text": ex.text, "score": round(ex.score, 4), "method": ex.rank_method}
                    for ex in rr.excerpts
                ],
                "evidence_note": rr.evidence_note,
            }
        )
        if len(hints) >= 10:
            break

    excerpt = (state.get("normalized_text") or "")[:18_000]
    has_supporting = int(state.get("supporting_count") or 0) > 0
    user = json.dumps(
        {
            "conflict_clusters": conflict_clusters,
            "round2": [],
            "issues_working": [i.model_dump(mode="json") for i in issues_working],
            "document_excerpt": excerpt,
            "output_mode": cfg.output_mode,
            "global_evidence_status": state.get("evidence_status_summary") or "",
            "evidence_arbitration_hints": hints,
            "convergence_cycle": cycle,
        },
        ensure_ascii=False,
    )
    await _emit(
        emit,
        "ARBITER_STARTED",
        "Arbiter refresh for convergence cycle.",
        {"cycle_number": cycle, "percent_complete": 88},
    )
    payload, err = await adapter.complete_json_with_retry(
        model_id=assign.arbiter.model_id,
        system=arbiter_round3_system(cfg, cfg.output_mode, has_supporting=has_supporting),
        user=user,
    )
    if payload is None:
        raise RuntimeError(f"arbiter_failed:{err}")
    validate_arbiter_payload(payload)
    issues_raw = payload.get("issues") or []
    issues = issues_from_payload(issues_raw, default_block_id="doc-root", source_agent="arbiter")
    edits_raw = payload.get("proposed_edits") or []
    edits: list[ProposedEdit] = []
    if isinstance(edits_raw, list):
        for e in edits_raw:
            if not isinstance(e, dict):
                continue
            edits.append(
                ProposedEdit(
                    edit_id=str(e.get("edit_id") or uuid.uuid4()),
                    block_id=str(e.get("block_id", "doc-root")),
                    before=str(e.get("before", "")),
                    after=str(e.get("after", "")),
                    rationale=str(e.get("rationale", "")),
                    source_agents=[str(x) for x in e.get("source_agents", [])] or ["arbiter"],
                )
            )
    decision = ArbitrationDecision(
        executive_summary=str(payload.get("executive_summary", "")).strip() or "Arbitration refresh complete.",
        resolved_conflicts=[],
        issues=issues,
        proposed_edits=edits,
        corrected_document_text=payload.get("corrected_document_text"),
        redline_html_fragment=payload.get("redline_html_fragment"),
    )
    await _emit(
        emit,
        "ARBITER_COMPLETE",
        "Arbiter refresh complete.",
        {"cycle_number": cycle, "issues": len(issues), "percent_complete": 90},
    )
    return decision


async def run_iterative_convergence(
    state: dict[str, Any],
    *,
    cfg: ReviewJobConfig,
    registry: ModelRegistry,
    assign: Any,
    emit: EmitFn | None,
) -> dict[str, Any]:
    """
    Mutates logical outputs: arbitration_decision, issues_working, conflict_clusters,
    normalized_text (fix mode), arbiter_payload, convergence_meta.
    """
    ir = cfg.iterative_review
    if not ir.enabled:
        return {}

    material = set(ir.material_issue_severities)
    disc_kw = material_discrepancy_detect_kwargs(cfg)
    meta: dict[str, Any] = {
        "cycles_completed": 1,
        "cycle_count_completed": 1,
        "convergence_status": "SINGLE_PASS",
        "convergence_failure_code": None,
        "max_cycles_reached": False,
        "unresolved_material_discrepancy_count": None,
        "newly_found_material_discrepancy_count": 0,
        "resolved_material_discrepancy_count": 0,
        "stopped_due_to_max_cycles": False,
        "stopped_due_to_quorum_loss": False,
        "stopped_due_to_provider_unavailable": False,
        "stopped_due_to_fatal_arbiter_failure": False,
        "stopped_with_remaining_discrepancies": False,
        "fix_alignment_audit_passed": None,
        "fix_alignment_audit_errors": None,
        "unresolved_cluster_summaries": [],
    }

    arb_dict = state.get("arbitration_decision")
    if not arb_dict:
        return {}
    arb = ArbitrationDecision.model_validate(arb_dict)
    working_issues = list(arb.issues)
    blocks_all = [DocumentBlock.model_validate(b) for b in state.get("blocks") or []]

    max_cycles = ir.max_cycles_fix_mode if cfg.output_mode == "fix" else ir.max_cycles_review_mode
    text_history: list[str] = [state.get("normalized_text") or ""]

    p1 = state.get("reviewer_phase1") or {}
    initial_ok = count_structured_successes(p1)
    meta["_last_cycle_reviewer_successes"] = initial_ok
    meta["_fix_baseline_normalized_for_audit"] = state.get("normalized_text") or ""
    meta["_fix_edit_sigs"] = []
    if initial_ok < 2:
        p1_rate = any(
            (p1.get(k) or {}).get("error_code")
            in (
                RATE_LIMIT_EXHAUSTED,
                GEMINI_UNAVAILABLE,
                GEMINI_DISABLED,
                GEMINI_RATE_LIMITED,
                GEMINI_SERVICE_UNAVAILABLE,
                OPENAI_UNAVAILABLE,
                OPENAI_RATE_LIMITED,
            )
            for k in ("claude", "gpt", "gemini")
        )
        if p1_rate:
            if any((p1.get(k) or {}).get("error_code") == GEMINI_RATE_LIMITED for k in ("claude", "gpt", "gemini")):
                meta["convergence_failure_code"] = GEMINI_RATE_LIMITED
            elif any((p1.get(k) or {}).get("error_code") == GEMINI_SERVICE_UNAVAILABLE for k in ("claude", "gpt", "gemini")):
                meta["convergence_failure_code"] = GEMINI_SERVICE_UNAVAILABLE
            elif any((p1.get(k) or {}).get("error_code") == OPENAI_RATE_LIMITED for k in ("claude", "gpt", "gemini")):
                meta["convergence_failure_code"] = OPENAI_RATE_LIMITED
            else:
                meta["convergence_failure_code"] = RATE_LIMIT_EXHAUSTED
            meta["convergence_status"] = "PARTIAL_REVIEW_COMPLETE"
            meta["stopped_due_to_provider_unavailable"] = True
        else:
            meta["convergence_failure_code"] = "QUORUM_LOST"
            meta["convergence_status"] = "QUORUM_LOST"
            meta["stopped_due_to_quorum_loss"] = True
        await _emit(
            emit,
            "ITERATIVE_SKIPPED_NO_QUORUM",
            "Insufficient structured reviewer quorum for convergence; skipping iterative cycles.",
            {"reviewer_success_count": initial_ok, "percent_complete": 77},
        )
        arb_dict_out = arb.model_dump(mode="json")
        arb_payload = {
            "executive_summary": arb.executive_summary,
            "issues": [i.model_dump(mode="json") for i in arb.issues],
            "redline_html": arb.redline_html_fragment or "",
            "changes": [e.model_dump(mode="json") for e in arb.proposed_edits],
            "corrected_document_text": arb.corrected_document_text or "",
        }
        clusters_final = detect_material_conflicts(arb.issues, **disc_kw)
        meta["unresolved_material_discrepancy_count"] = len(clusters_final)
        fix_not_clean_er = cfg.output_mode == "fix" and not fix_mode_meets_clean_threshold(
            list(arb.issues),
            material_severities=material,
            ignore_nits=ir.ignore_nits_for_fix_completion,
        )
        _reconcile_iterative_consensus_meta(
            meta,
            cfg=cfg,
            registry=registry,
            assign=assign,
            issues_for_fix_threshold=list(arb.issues),
            successful_reviewer_count=initial_ok,
            pairwise_cluster_count=len(clusters_final),
        )
        _finalize_stopped_remaining_discrepancies(
            meta,
            convergence_status=str(meta.get("convergence_status") or "") or None,
            unresolved_disc_count=len(clusters_final),
            fix_not_clean=fix_not_clean_er,
        )
        conflict_payload_final = [
            {"cluster_id": c.cluster_id, "reasons": list(c.reasons), "issues": [i.model_dump(mode="json") for i in c.issues]}
            for c in clusters_final
        ]
        meta["unresolved_cluster_summaries"] = _summarize_unresolved_clusters(conflict_payload_final)
        return {
            "arbitration_decision": arb_dict_out,
            "issues_working": [i.model_dump(mode="json") for i in arb.issues],
            "conflict_clusters": conflict_payload_final,
            "arbiter_payload": arb_payload,
            "convergence_meta": meta,
            "normalized_text": state.get("normalized_text"),
            "blocks": state.get("blocks"),
        }

    init_disc = detect_material_conflicts(working_issues, **disc_kw)
    meta["_last_material_disc_count"] = len(init_disc)
    meta["unresolved_material_discrepancy_count"] = len(init_disc)

    if cfg.output_mode == "fix":
        await _emit(
            emit,
            "FIX_BASELINE_REVIEW_STARTED",
            "Fix Mode Stage A — baseline tri-review and arbitration captured.",
            {"issues": len(working_issues), "percent_complete": 76},
        )
        await _emit(
            emit,
            "FIX_BASELINE_REVIEW_COMPLETE",
            "Baseline issue ledger and proposed edits are ready for correction cycles.",
            {
                "issues": len(working_issues),
                "proposed_edits": len(arb.proposed_edits),
                "material_clusters": len(init_disc),
                "percent_complete": 76,
            },
        )

    cycle = 2
    while cycle <= max_cycles:
        await _emit(
            emit,
            "ITERATIVE_CYCLE_STARTED",
            f"Convergence cycle {cycle} started.",
            {"cycle_number": cycle, "percent_complete": 78},
        )

        if _convergence_configured_role_count(registry, assign) < 2:
            rt = get_llm_job_runtime()
            if rt and (
                (rt.gemini_unavailable_for_job and not rt.gemini_disabled_intentionally) or rt.openai_unavailable_for_job
            ):
                if rt.openai_unavailable_for_job and (rt.openai_skip_reason or "") == "OPENAI_RATE_LIMITED":
                    meta["convergence_failure_code"] = OPENAI_RATE_LIMITED
                elif rt.gemini_unavailable_for_job and (rt.gemini_skip_reason or "") == "GEMINI_RATE_LIMITED":
                    meta["convergence_failure_code"] = GEMINI_RATE_LIMITED
                elif rt.gemini_unavailable_for_job and (rt.gemini_skip_reason or "") == "GEMINI_SERVICE_UNAVAILABLE":
                    meta["convergence_failure_code"] = GEMINI_SERVICE_UNAVAILABLE
                else:
                    meta["convergence_failure_code"] = RATE_LIMIT_EXHAUSTED
                meta["convergence_status"] = "PARTIAL_REVIEW_COMPLETE"
                meta["stopped_due_to_provider_unavailable"] = True
            else:
                meta["convergence_failure_code"] = "QUORUM_LOST"
                meta["convergence_status"] = "QUORUM_LOST"
                meta["stopped_due_to_quorum_loss"] = True
            await _emit(
                emit,
                "ITERATIVE_CYCLE_COMPLETE",
                "Too few callable reviewers for another convergence cycle.",
                {"cycle_number": cycle, "percent_complete": 84},
            )
            break

        if cfg.output_mode == "fix":
            await _emit(
                emit,
                "FIX_RECONCILIATION_CYCLE_STARTED",
                f"Fix Mode Stage D — reconciliation cycle {cycle} (candidate generation + tri-review).",
                {"cycle_number": cycle, "percent_complete": 78},
            )
            await _emit(
                emit,
                "FIX_CANDIDATE_GENERATION_STARTED",
                "Building corrected plaintext candidate from accepted edits.",
                {"cycle_number": cycle, "percent_complete": 79},
            )
            await _emit(emit, "FIX_REAPPLY_STARTED", "Applying accepted edits for re-review.", {"cycle_number": cycle})
            corrected = apply_plaintext_edits(state.get("normalized_text") or "", arb.proposed_edits)
            if detect_text_thrash(text_history + [corrected]):
                meta["convergence_status"] = "HUMAN_FOLLOW_UP_REQUIRED"
                meta["convergence_failure_code"] = "THRASH_DETECTED"
                meta["unresolved_material_discrepancy_count"] = len(
                    detect_material_conflicts(working_issues, **disc_kw)
                )
                await _emit(
                    emit,
                    "ITERATIVE_CYCLE_COMPLETE",
                    "Text oscillation thrash detected; stopping fix convergence.",
                    {"cycle_number": cycle, "percent_complete": 85},
                )
                await _emit(
                    emit,
                    "FIX_HUMAN_FOLLOW_UP_REQUIRED",
                    "Fix Mode requires human follow-up (document text oscillated across cycles).",
                    {"cycle_number": cycle, "percent_complete": 85},
                )
                break
            text_history.append(corrected)
            state["normalized_text"] = corrected
            state["blocks"] = [
                b.model_dump(mode="json")
                for b in chunk_document_blocks(corrected, max_chars=int(cfg.max_chars_per_block))
            ]
            blocks_all = [DocumentBlock.model_validate(b) for b in state["blocks"]]
            await _emit(emit, "FIX_REAPPLY_COMPLETE", "Corrected text ready for tri-review.", {"cycle_number": cycle})
            await _emit(
                emit,
                "FIX_CANDIDATE_GENERATION_COMPLETE",
                "Corrected candidate generated; starting tri-model review of the candidate.",
                {"cycle_number": cycle, "char_len": len(corrected), "percent_complete": 79},
            )

        clusters_on_working = detect_material_conflicts(working_issues, **disc_kw)
        meta["unresolved_material_discrepancy_count"] = len(clusters_on_working)

        if len(clusters_on_working) == 0:
            if cfg.output_mode == "fix" and not fix_mode_meets_clean_threshold(
                working_issues,
                material_severities=material,
                ignore_nits=ir.ignore_nits_for_fix_completion,
            ):
                pass  # fall through to full-document re-review
            elif cfg.output_mode == "review":
                succ = int(meta.get("_last_cycle_reviewer_successes", initial_ok))
                meta["cycles_completed"] = cycle
                meta["cycle_count_completed"] = cycle
                _reconcile_iterative_consensus_meta(
                    meta,
                    cfg=cfg,
                    registry=registry,
                    assign=assign,
                    issues_for_fix_threshold=working_issues,
                    successful_reviewer_count=succ,
                    pairwise_cluster_count=0,
                )
                if ir.strict_three_reviewer_consensus and meta.get("consensus_mode") == "PARTIAL_CONSENSUS":
                    meta["convergence_status"] = "PARTIAL_CONSENSUS"
                else:
                    meta["convergence_status"] = "CONVERGENCE_REACHED"
                meta["unresolved_material_discrepancy_count"] = 0
                meta["stopped_with_remaining_discrepancies"] = False
                mode = str(meta.get("consensus_mode") or "")
                if mode == "PARTIAL_CONSENSUS":
                    await _emit(
                        emit,
                        "PARTIAL_CONSENSUS",
                        "Partial consensus reached — no material discrepancies among participating reviewers; "
                        "three-reviewer agreement was not obtained.",
                        {"cycle_number": cycle, "percent_complete": 92, "material_discrepancies": 0},
                    )
                elif mode == "FULL_THREE_REVIEWER_CONSENSUS":
                    await _emit(
                        emit,
                        "CONVERGENCE_REACHED",
                        "Consensus reached across 3 reviewers — no material discrepancies remain.",
                        {"cycle_number": cycle, "percent_complete": 92, "material_discrepancies": 0},
                    )
                else:
                    await _emit(
                        emit,
                        "CONVERGENCE_REACHED",
                        "Consensus reached across configured reviewers — no material discrepancies remain.",
                        {"cycle_number": cycle, "percent_complete": 92, "material_discrepancies": 0},
                    )
                await _emit(
                    emit,
                    "ITERATIVE_CYCLE_COMPLETE",
                    "Convergence cycle complete.",
                    {"cycle_number": cycle, "percent_complete": 92},
                )
                break

        if cfg.output_mode == "fix":
            await _emit(
                emit,
                "FIX_CANDIDATE_TRI_REVIEW_STARTED",
                "Tri-model review of corrected candidate (Claude, GPT, Gemini).",
                {"cycle_number": cycle, "percent_complete": 80},
            )

        target_blocks = _select_blocks_for_cycle(working_issues, blocks_all, ir, cycle=cycle)
        if cfg.output_mode == "review" and clusters_on_working and not target_blocks:
            hot = {it.block_id for c in clusters_on_working for it in c.issues}
            if ir.rerun_neighbor_blocks and hot:
                hot = _neighbor_block_ids(blocks_all, hot, ir.neighbor_window)
            by_id = {b.block_id: b for b in blocks_all}
            target_blocks = [by_id[b] for b in sorted(hot) if b in by_id]

        if cfg.output_mode == "review" and target_blocks:
            review_blocks = target_blocks
        else:
            review_blocks = blocks_all

        rt_cycle = get_llm_job_runtime()
        skip_gemini = bool(
            rt_cycle
            and rt_cycle.gemini_unavailable_for_job
            and registry.adapter(assign.consistency_parser).configured
        )
        skip_gpt = bool(
            rt_cycle
            and rt_cycle.openai_unavailable_for_job
            and registry.adapter(assign.skeptical_reviewer).configured
        )
        tasks: list[Awaitable[tuple[list[Issue], str | None]]] = [
            _run_reviewer_role(
                state=state,
                cfg=cfg,
                blocks=review_blocks,
                role_key="claude",
                resolved=assign.author_intent,
                system_builder=claude_system,
                source_tag="claude_reviewer",
                registry=registry,
                emit=emit,
                cycle=cycle,
            ),
        ]
        if not skip_gpt:
            tasks.append(
                _run_reviewer_role(
                    state=state,
                    cfg=cfg,
                    blocks=review_blocks,
                    role_key="gpt",
                    resolved=assign.skeptical_reviewer,
                    system_builder=gpt_system,
                    source_tag="gpt_reviewer",
                    registry=registry,
                    emit=emit,
                    cycle=cycle,
                )
            )
        if not skip_gemini:
            tasks.append(
                _run_reviewer_role(
                    state=state,
                    cfg=cfg,
                    blocks=review_blocks,
                    role_key="gemini",
                    resolved=assign.consistency_parser,
                    system_builder=gemini_system,
                    source_tag="gemini_reviewer",
                    registry=registry,
                    emit=emit,
                    cycle=cycle,
                )
            )
        results = await asyncio.gather(*tasks)
        ri = 0
        r_claude = results[ri]
        ri += 1
        if skip_gpt:
            assert rt_cycle is not None
            gpt_code = OPENAI_RATE_LIMITED if (rt_cycle.openai_skip_reason or "") == "OPENAI_RATE_LIMITED" else OPENAI_UNAVAILABLE
            r_gpt = ([], gpt_code)
        else:
            r_gpt = results[ri]
            ri += 1
        r_gem: tuple[list[Issue], str | None]
        if skip_gemini:
            assert rt_cycle is not None
            if rt_cycle.gemini_disabled_intentionally:
                code = GEMINI_DISABLED
            elif (rt_cycle.gemini_skip_reason or "") == "GEMINI_RATE_LIMITED":
                code = GEMINI_RATE_LIMITED
            elif (rt_cycle.gemini_skip_reason or "") == "GEMINI_SERVICE_UNAVAILABLE":
                code = GEMINI_SERVICE_UNAVAILABLE
            else:
                code = GEMINI_UNAVAILABLE
            r_gem = ([], code)
        else:
            r_gem = results[ri]
        new_lists = [r_claude[0], r_gpt[0], r_gem[0]]
        errs = [r_claude[1], r_gpt[1], r_gem[1]]
        ok = sum(1 for e in errs if e is None)
        if ok < 2:
            if any(
                e
                in (
                    RATE_LIMIT_EXHAUSTED,
                    GEMINI_UNAVAILABLE,
                    GEMINI_DISABLED,
                    GEMINI_RATE_LIMITED,
                    GEMINI_SERVICE_UNAVAILABLE,
                    OPENAI_UNAVAILABLE,
                    OPENAI_RATE_LIMITED,
                )
                for e in errs
            ):
                if GEMINI_RATE_LIMITED in errs:
                    meta["convergence_failure_code"] = GEMINI_RATE_LIMITED
                elif GEMINI_SERVICE_UNAVAILABLE in errs:
                    meta["convergence_failure_code"] = GEMINI_SERVICE_UNAVAILABLE
                elif OPENAI_RATE_LIMITED in errs:
                    meta["convergence_failure_code"] = OPENAI_RATE_LIMITED
                else:
                    meta["convergence_failure_code"] = RATE_LIMIT_EXHAUSTED
                meta["convergence_status"] = "PARTIAL_REVIEW_COMPLETE"
                meta["stopped_due_to_provider_unavailable"] = True
            else:
                meta["convergence_failure_code"] = "QUORUM_LOST"
                meta["convergence_status"] = "QUORUM_LOST"
                meta["stopped_due_to_quorum_loss"] = True
            await _emit(
                emit,
                "ITERATIVE_CYCLE_COMPLETE",
                "Quorum lost during convergence; stopping.",
                {"cycle_number": cycle, "percent_complete": 84},
            )
            break

        meta["_last_cycle_reviewer_successes"] = ok

        if cfg.output_mode == "fix":
            await _emit(
                emit,
                "FIX_CANDIDATE_TRI_REVIEW_COMPLETE",
                "Tri-model review of corrected candidate finished; refreshing arbitration.",
                {"cycle_number": cycle, "percent_complete": 84},
            )

        merged_round: list[Issue] = []
        merged_round.extend(working_issues)
        for lst in new_lists:
            merged_round.extend(lst)
        deduped = dedupe_findings(merged_round)
        clusters = detect_material_conflicts(deduped, **disc_kw)
        meta["unresolved_material_discrepancy_count"] = len(clusters)

        conflict_payload = [
            {"cluster_id": c.cluster_id, "reasons": list(c.reasons), "issues": [i.model_dump(mode="json") for i in c.issues]}
            for c in clusters
        ]

        try:
            new_arb = await _run_arbiter_once(
                state=state,
                cfg=cfg,
                issues_working=deduped,
                conflict_clusters=conflict_payload,
                registry=registry,
                assign=assign,
                emit=emit,
                cycle=cycle,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("iterative arbiter failed: %s", exc)
            meta["convergence_failure_code"] = "ARBITER_FAILED"
            meta["convergence_status"] = "PARTIAL_REVIEW_COMPLETE"
            meta["stopped_due_to_fatal_arbiter_failure"] = True
            meta["unresolved_material_discrepancy_count"] = len(clusters)
            meta["_pending_failure_conflict_payload"] = conflict_payload
            break

        working_issues = list(new_arb.issues)
        arb = new_arb

        post_clusters = detect_material_conflicts(working_issues, **disc_kw)
        post_material = len(post_clusters)
        meta["unresolved_material_discrepancy_count"] = post_material
        prev_disc = meta.get("_last_material_disc_count")
        if isinstance(prev_disc, int):
            if post_material < prev_disc:
                meta["resolved_material_discrepancy_count"] = meta.get("resolved_material_discrepancy_count", 0) + (
                    prev_disc - post_material
                )
            elif post_material > prev_disc:
                meta["newly_found_material_discrepancy_count"] = meta.get(
                    "newly_found_material_discrepancy_count", 0
                ) + (post_material - prev_disc)
        meta["_last_material_disc_count"] = post_material

        if cfg.output_mode == "fix":
            meta["_fix_edit_sigs"].append(_edit_cycle_signature(arb.proposed_edits))
            if detect_edit_signature_thrash(meta["_fix_edit_sigs"]):
                meta["convergence_status"] = "HUMAN_FOLLOW_UP_REQUIRED"
                meta["convergence_failure_code"] = "EDIT_THRASH_DETECTED"
                meta["unresolved_material_discrepancy_count"] = post_material
                await _emit(
                    emit,
                    "ITERATIVE_CYCLE_COMPLETE",
                    "Edit-set oscillation detected across fix cycles; stopping.",
                    {"cycle_number": cycle, "percent_complete": 85},
                )
                await _emit(
                    emit,
                    "FIX_HUMAN_FOLLOW_UP_REQUIRED",
                    "Fix Mode requires human follow-up (proposed edits oscillated without stabilizing).",
                    {"cycle_number": cycle, "percent_complete": 85},
                )
                break

        if post_material == 0:
            if cfg.output_mode == "fix" and not fix_mode_meets_clean_threshold(
                working_issues,
                material_severities=material,
                ignore_nits=ir.ignore_nits_for_fix_completion,
            ):
                meta["cycles_completed"] = cycle
                meta["cycle_count_completed"] = cycle
                await _emit(
                    emit,
                    "ITERATIVE_CYCLE_COMPLETE",
                    "Zero cross-model material discrepancies; re-reviewing for remaining open issues.",
                    {"cycle_number": cycle, "percent_complete": 88},
                )
                await _emit(
                    emit,
                    "FIX_RECONCILIATION_CYCLE_COMPLETE",
                    "Fix cycle paused for remaining open issues (nits or non-cluster material).",
                    {"cycle_number": cycle, "percent_complete": 88},
                )
                cycle += 1
                continue
            if cfg.output_mode == "fix":
                open_ok, open_reason = _fix_open_issue_gate(cfg, working_issues, material)
                if not open_ok:
                    meta["cycles_completed"] = cycle
                    meta["cycle_count_completed"] = cycle
                    await _emit(
                        emit,
                        "ITERATIVE_CYCLE_COMPLETE",
                        f"Fix completion gate: open issues remain ({open_reason}); continuing cycles.",
                        {"cycle_number": cycle, "percent_complete": 88},
                    )
                    await _emit(
                        emit,
                        "FIX_RECONCILIATION_CYCLE_COMPLETE",
                        "Reconciliation cycle finished; another fix pass required.",
                        {"cycle_number": cycle, "percent_complete": 88},
                    )
                    cycle += 1
                    continue

            meta["cycles_completed"] = cycle
            meta["cycle_count_completed"] = cycle
            meta["_last_cycle_reviewer_successes"] = ok

            if cfg.output_mode == "fix":
                await _emit(
                    emit,
                    "FIX_RECONCILIATION_CYCLE_COMPLETE",
                    "Material discrepancy clusters cleared; running final alignment audit.",
                    {"cycle_number": cycle, "percent_complete": 90},
                )
                fc = cfg.fix_mode_completion
                final_candidate = apply_plaintext_edits(state.get("normalized_text") or "", arb.proposed_edits)
                audit_passed = True
                audit_errors: list[str] = []
                if fc.require_alignment_audit_pass:
                    await _emit(
                        emit,
                        "FINAL_ALIGNMENT_AUDIT_STARTED",
                        "Comparing final corrected candidate to accepted edit ledger and constraints.",
                        {"cycle_number": cycle, "percent_complete": 91},
                    )
                    audit_passed, audit_errors = run_final_fix_alignment_audit(
                        final_document_text=final_candidate,
                        baseline_document_text=str(meta.get("_fix_baseline_normalized_for_audit") or ""),
                        proposed_edits=list(arb.proposed_edits),
                        issues=list(working_issues),
                        do_not_change=cfg.do_not_change,
                        material_severities=material,
                        require_locked_term_integrity=fc.require_locked_term_integrity,
                    )
                    meta["fix_alignment_audit_passed"] = audit_passed
                    meta["fix_alignment_audit_errors"] = audit_errors
                    if audit_passed:
                        await _emit(
                            emit,
                            "FINAL_ALIGNMENT_AUDIT_COMPLETE",
                            "Final alignment audit passed — corrected document matches the converged ledger.",
                            {"cycle_number": cycle, "percent_complete": 91},
                        )
                    else:
                        await _emit(
                            emit,
                            "FINAL_ALIGNMENT_AUDIT_FAILED",
                            "Final alignment audit failed — corrected document does not match the converged ledger.",
                            {"cycle_number": cycle, "errors": audit_errors[:12], "percent_complete": 91},
                        )
                if not audit_passed:
                    meta["convergence_status"] = "HUMAN_FOLLOW_UP_REQUIRED"
                    meta["convergence_failure_code"] = "ALIGNMENT_AUDIT_FAILED"
                    state["normalized_text"] = final_candidate
                    state["blocks"] = [
                        b.model_dump(mode="json")
                        for b in chunk_document_blocks(final_candidate, max_chars=int(cfg.max_chars_per_block))
                    ]
                    await _emit(
                        emit,
                        "FIX_HUMAN_FOLLOW_UP_REQUIRED",
                        "Fix Mode requires human follow-up (final alignment audit failed).",
                        {"cycle_number": cycle, "percent_complete": 92},
                    )
                    await _emit(
                        emit,
                        "ITERATIVE_CYCLE_COMPLETE",
                        "Convergence cycle complete.",
                        {"cycle_number": cycle, "percent_complete": 92},
                    )
                    break

                state["normalized_text"] = final_candidate
                state["blocks"] = [
                    b.model_dump(mode="json")
                    for b in chunk_document_blocks(final_candidate, max_chars=int(cfg.max_chars_per_block))
                ]
                await _emit(
                    emit,
                    "FIX_CONVERGENCE_REACHED",
                    "Fix Mode: tri-review converged, thresholds met, and final alignment audit passed.",
                    {"cycle_number": cycle, "percent_complete": 92},
                )

            _reconcile_iterative_consensus_meta(
                meta,
                cfg=cfg,
                registry=registry,
                assign=assign,
                issues_for_fix_threshold=working_issues,
                successful_reviewer_count=ok,
                pairwise_cluster_count=0,
            )
            if ir.strict_three_reviewer_consensus and meta.get("consensus_mode") == "PARTIAL_CONSENSUS":
                meta["convergence_status"] = "PARTIAL_CONSENSUS"
            else:
                meta["convergence_status"] = "CONVERGENCE_REACHED"
            meta["unresolved_material_discrepancy_count"] = 0
            meta["stopped_with_remaining_discrepancies"] = False
            mode = str(meta.get("consensus_mode") or "")
            if mode == "PARTIAL_CONSENSUS":
                await _emit(
                    emit,
                    "PARTIAL_CONSENSUS",
                    "Partial consensus reached — no material discrepancies among participating reviewers; "
                    "three-reviewer agreement was not obtained.",
                    {"cycle_number": cycle, "percent_complete": 92, "material_discrepancies": 0},
                )
            elif mode == "FULL_THREE_REVIEWER_CONSENSUS":
                await _emit(
                    emit,
                    "CONVERGENCE_REACHED",
                    "Consensus reached across 3 reviewers — no material discrepancies remain.",
                    {"cycle_number": cycle, "percent_complete": 92, "material_discrepancies": 0},
                )
            else:
                await _emit(
                    emit,
                    "CONVERGENCE_REACHED",
                    "Consensus reached across configured reviewers — no material discrepancies remain.",
                    {"cycle_number": cycle, "percent_complete": 92, "material_discrepancies": 0},
                )
            await _emit(
                emit,
                "ITERATIVE_CYCLE_COMPLETE",
                "Convergence cycle complete.",
                {"cycle_number": cycle, "percent_complete": 92},
            )
            break

        meta["cycles_completed"] = cycle
        meta["cycle_count_completed"] = cycle
        await _emit(
            emit,
            "ITERATIVE_CYCLE_COMPLETE",
            "Convergence cycle complete.",
            {"cycle_number": cycle, "percent_complete": 87},
        )
        cycle += 1

    if (
        max_cycles >= 2
        and meta["cycles_completed"] >= max_cycles
        and meta.get("convergence_status")
        not in {
            "CONVERGENCE_REACHED",
            "HUMAN_FOLLOW_UP_REQUIRED",
            "QUORUM_LOST",
            "PARTIAL_REVIEW_COMPLETE",
            "PARTIAL_CONSENSUS",
        }
    ):
        meta["convergence_failure_code"] = meta.get("convergence_failure_code") or "MAX_CYCLES_REACHED"
        meta["max_cycles_reached"] = True
        meta["convergence_status"] = "MAX_CYCLES_REACHED"
        meta["stopped_due_to_max_cycles"] = True

    arb_dict_out = arb.model_dump(mode="json")
    arb_payload = {
        "executive_summary": arb.executive_summary,
        "issues": [i.model_dump(mode="json") for i in arb.issues],
        "redline_html": arb.redline_html_fragment or "",
        "changes": [e.model_dump(mode="json") for e in arb.proposed_edits],
        "corrected_document_text": arb.corrected_document_text or "",
    }
    pending_fail = meta.pop("_pending_failure_conflict_payload", None)
    if pending_fail is not None:
        conflict_payload_final = pending_fail
    else:
        clusters_final = detect_material_conflicts(arb.issues, **disc_kw)
        meta["unresolved_material_discrepancy_count"] = len(clusters_final)
        conflict_payload_final = [
            {"cluster_id": c.cluster_id, "reasons": list(c.reasons), "issues": [i.model_dump(mode="json") for i in c.issues]}
            for c in clusters_final
        ]
    meta["unresolved_cluster_summaries"] = _summarize_unresolved_clusters(conflict_payload_final)
    meta.pop("_last_material_disc_count", None)

    succ_final = int(meta.get("_last_cycle_reviewer_successes", initial_ok))
    pairwise_final = int(meta.get("unresolved_material_discrepancy_count") or 0)
    _reconcile_iterative_consensus_meta(
        meta,
        cfg=cfg,
        registry=registry,
        assign=assign,
        issues_for_fix_threshold=list(arb.issues),
        successful_reviewer_count=succ_final,
        pairwise_cluster_count=pairwise_final,
    )

    fix_not_clean = cfg.output_mode == "fix" and not fix_mode_meets_clean_threshold(
        list(arb.issues),
        material_severities=material,
        ignore_nits=ir.ignore_nits_for_fix_completion,
    )
    _finalize_stopped_remaining_discrepancies(
        meta,
        convergence_status=str(meta.get("convergence_status") or "") or None,
        unresolved_disc_count=int(meta.get("unresolved_material_discrepancy_count") or 0),
        fix_not_clean=fix_not_clean,
    )

    return {
        "arbitration_decision": arb_dict_out,
        "issues_working": [i.model_dump(mode="json") for i in arb.issues],
        "conflict_clusters": conflict_payload_final,
        "arbiter_payload": arb_payload,
        "convergence_meta": meta,
        "normalized_text": state.get("normalized_text"),
        "blocks": state.get("blocks"),
    }
