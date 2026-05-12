from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from pydantic import ValidationError

from draftlens_api.artifacts import render as artifact_render
from draftlens_api.artifacts.disclaimers import build_disclaimer_bundle
from draftlens_api.domain.enums import IssueStatus
from draftlens_api.domain.models import (
    ArbitrationDecision,
    ArtifactManifest,
    ArtifactRecord,
    DocumentBlock,
    EvidenceSource,
    FinalLedger,
    Issue,
    ProposedEdit,
    RenderPlan,
    ReviewJobConfig,
)
from draftlens_api.engine.arbitration_gate import (
    build_arbiter_user_dict,
    count_structured_successes,
    post_detect_routing,
)
from draftlens_api.config import get_settings
from draftlens_api.engine.consensus_coverage import configured_reviewer_slots, reconcile_single_pass_consensus
from draftlens_api.engine.cycle_ledger_compare import fix_mode_meets_clean_threshold, unresolved_material_and_nit
from draftlens_api.engine.iterative_convergence import run_iterative_convergence
from draftlens_api.engine.pipeline_conflicts import detect_conflicts as detect_material_conflicts
from draftlens_api.engine.pipeline_conflicts import material_discrepancy_detect_kwargs
from draftlens_api.providers.llm_job_runtime import attach_llm_job_runtime, build_llm_job_runtime, get_llm_job_runtime, reset_llm_job_runtime
from draftlens_api.engine.reviewer_caps import cap_reviewer_issues
from draftlens_api.engine.pipeline_dedupe import dedupe_findings
from draftlens_api.engine.pipeline_evidence import rank_evidence_for_block
from draftlens_api.engine.pipeline_prompts import (
    arbiter_round3_system,
    claude_system,
    conflict_weighting_note,
    gemini_system,
    gpt_system,
    round2_system,
)
from draftlens_api.evidence import EvidenceChunk, EvidenceIndex, EvidenceRetriever, SupportingFileParser
from draftlens_api.evidence.types import EvidenceIngestionAudit, SupportingFileExtractionAudit
from draftlens_api.prompts.schemas import (
    validate_arbiter_payload,
    validate_debate_round2_payload,
    validate_reviewer_payload,
)
from draftlens_api.providers.dev_hints import MISSING_SINGLE_PROVIDER_ENV_HINT, MULTI_MODEL_QUORUM_HINT
from draftlens_api.providers.normalization import agent_finding_from_payload, issues_from_payload
from draftlens_api.providers.structured_output import GEMINI_DISABLED, GEMINI_UNAVAILABLE, OPENAI_UNAVAILABLE
from draftlens_api.routing.model_registry import ModelRegistry
from draftlens_api.policies import artifact_visibility as artifact_visibility_policy
from draftlens_api.services import pdf_artifact_service as pdf_artifact_service
from draftlens_api.services.document_blocks import chunk_document_blocks
from draftlens_api.services.documents import extract_main_document
from draftlens_api.services.paths import DataPaths

logger = logging.getLogger(__name__)

EmitFn = Callable[[str, str, dict[str, Any] | None], Awaitable[None]]


class ReviewPipelineState(TypedDict, total=False):
    job_id: str
    job_config: dict[str, Any]
    main_path: str
    supporting_count: int
    main_bytes_len: int
    main_text: str
    pages: int
    parse_mime: str
    main_source_format: str
    main_parse_warnings: list[str]
    evidence_bundle: str
    evidence_sources: list[dict[str, Any]]
    evidence_chunks: list[dict[str, Any]]
    supporting_paths: list[dict[str, str]]
    evidence_index_path: str
    evidence_fts_enabled: bool
    evidence_any_partial: bool
    evidence_status_summary: str
    evidence_audit_path: str
    normalized_text: str
    review_context: str
    blocks: list[dict[str, Any]]
    issues_claude_r1: list[dict[str, Any]]
    issues_gpt_r1: list[dict[str, Any]]
    issues_gemini_r1: list[dict[str, Any]]
    issues_merged: list[dict[str, Any]]
    issues_deduped: list[dict[str, Any]]
    issues_working: list[dict[str, Any]]
    conflict_clusters: list[dict[str, Any]]
    debate_digest: str
    round2_transcript: list[dict[str, Any]]
    arbitration_decision: dict[str, Any]
    final_ledger: dict[str, Any]
    render_plan: dict[str, Any]
    pipeline_output: dict[str, Any]
    stats_by_severity: dict[str, int]
    stats_by_category: dict[str, int]
    unresolved_human_evidence: list[dict[str, Any]]
    disclaimer_bundle: dict[str, Any]
    artifact_manifest: dict[str, Any]
    artifact_file_rows: list[dict[str, Any]]
    arbiter_payload: dict[str, Any]
    stage_trace: list[str]
    skip_arbitration: bool
    reviewer_phase1: dict[str, Any]
    convergence_meta: dict[str, Any]


def _trace(state: ReviewPipelineState, name: str) -> list[str]:
    t = list(state.get("stage_trace") or [])
    t.append(name)
    return t


def _cfg(state: ReviewPipelineState) -> ReviewJobConfig:
    return ReviewJobConfig.model_validate(state["job_config"])


def _blocks(state: ReviewPipelineState) -> list[DocumentBlock]:
    return [DocumentBlock.model_validate(b) for b in state.get("blocks") or []]


def _issues_from_state(state: ReviewPipelineState, key: str = "issues_working") -> list[Issue]:
    return [Issue.model_validate(x) for x in state.get(key) or []]


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


async def _emit(emit: EmitFn | None, stage: str, message: str, detail: dict[str, Any] | None = None) -> None:
    if emit is None:
        return
    await emit(stage, message, detail)


def _sources(state: ReviewPipelineState) -> list[EvidenceSource]:
    return [EvidenceSource.model_validate(x) for x in state.get("evidence_sources") or []]


def _make_evidence_retriever(state: ReviewPipelineState) -> EvidenceRetriever:
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


def _normalize_text(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    out: list[str] = []
    blank = 0
    for ln in lines:
        if ln.strip() == "":
            blank += 1
            if blank <= 2:
                out.append("")
        else:
            blank = 0
            out.append(ln)
    return "\n".join(out).strip() + ("\n" if text.endswith("\n") else "")


def _stats(issues: list[Issue]) -> tuple[dict[str, int], dict[str, int]]:
    by_sev: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for it in issues:
        by_sev[it.severity.value] = by_sev.get(it.severity.value, 0) + 1
        by_cat[it.category.value] = by_cat.get(it.category.value, 0) + 1
    return by_sev, by_cat


def _human_evidence_queue(issues: list[Issue]) -> list[Issue]:
    out: list[Issue] = []
    for it in issues:
        if "needs_human_evidence" in (it.explanation or "").lower():
            out.append(it)
            continue
        if it.accuracy_posture and it.accuracy_posture.value == "unverified" and it.severity.value in {
            "critical",
            "major",
        }:
            out.append(it)
    return out


def build_review_pipeline_graph(
    registry: ModelRegistry,
    *,
    paths: DataPaths,
    emit: EmitFn | None = None,
) -> StateGraph:
    assign = registry.assignment()

    async def ingest_main_document(state: ReviewPipelineState) -> dict[str, Any]:
        p = Path(state["main_path"])
        data = p.read_bytes()
        return {"main_bytes_len": len(data), "stage_trace": _trace(state, "ingest_main_document")}

    async def ingest_supporting_files(state: ReviewPipelineState) -> dict[str, Any]:
        await _emit(
            emit,
            "SUPPORTING_FILES_INGESTED",
            "Supporting files on record.",
            {"count": int(state.get("supporting_count") or 0)},
        )
        return {"stage_trace": _trace(state, "ingest_supporting_files")}

    async def hydrate_post_review_fix_seed(state: ReviewPipelineState) -> dict[str, Any]:
        cfg = _cfg(state)
        parent = (cfg.post_review_fix_seed_job_id or "").strip()
        if not parent:
            raise RuntimeError("hydrate_missing_parent_job")
        seed_path = paths.job_artifacts(parent) / "fix_seed_snapshot.json"
        if not seed_path.is_file():
            raise RuntimeError("fix_seed_snapshot_missing")
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
        await _emit(
            emit,
            "APPLY_FIXES_HYDRATE_STARTED",
            "Loading finalized review ledger for corrected-document generation.",
            {"source_review_job_id": parent, "progress_percent": 8},
        )
        arb = raw.get("arbitration_decision")
        if not isinstance(arb, dict):
            raise RuntimeError("fix_seed_invalid_arbitration")
        issues_w = raw.get("issues_working")
        if not isinstance(issues_w, list) or not issues_w:
            ad = ArbitrationDecision.model_validate(arb)
            issues_w = [i.model_dump(mode="json") for i in ad.issues]
        out: dict[str, Any] = {
            "arbitration_decision": arb,
            "issues_working": issues_w,
            "blocks": list(raw.get("blocks") or []),
            "normalized_text": str(raw.get("normalized_text") or ""),
            "main_text": str(raw.get("main_text") or ""),
            "pages": int(raw.get("pages") or 1),
            "parse_mime": str(raw.get("parse_mime") or ""),
            "reviewer_phase1": dict(raw.get("reviewer_phase1") or {}),
            "convergence_meta": dict(raw.get("convergence_meta") or {}),
            "conflict_clusters": list(raw.get("conflict_clusters") or []),
            "stage_trace": _trace(state, "hydrate_post_review_fix_seed"),
        }
        await _emit(
            emit,
            "APPLY_FIXES_HYDRATE_COMPLETE",
            "Review outcomes loaded; entering fix validation and convergence.",
            {"progress_percent": 14},
        )
        await _emit(
            emit,
            "FIX_JOB_CREATED_FROM_REVIEW",
            "Derived fix job linked to completed review.",
            {"parent_job_id": parent, "progress_percent": 16},
        )
        return out

    async def parse_main_document(state: ReviewPipelineState) -> dict[str, Any]:
        p = Path(state["main_path"])
        cfg = _cfg(state)
        parsed = extract_main_document(p, cfg.main_original_filename)
        pages = max(1, int(parsed.pages))
        await _emit(
            emit,
            "DOC_PARSED",
            "Main document parsed.",
            {
                "pages": pages,
                "mime": str(parsed.mime or ""),
                "main_source_format": parsed.source_format,
                "parse_notes": list(parsed.parse_notes),
            },
        )
        return {
            "main_text": parsed.text,
            "pages": pages,
            "parse_mime": str(parsed.mime or ""),
            "main_source_format": parsed.source_format,
            "main_parse_warnings": list(parsed.parse_notes),
            "stage_trace": _trace(state, "parse_main_document"),
        }

    async def parse_supporting_evidence(state: ReviewPipelineState) -> dict[str, Any]:
        job_id = state["job_id"]
        work = paths.job_working(job_id)
        work.mkdir(parents=True, exist_ok=True)

        sp = list(state.get("supporting_paths") or [])
        await _emit(
            emit,
            "EVIDENCE_PARSE_STARTED",
            "Parsing supporting evidence files.",
            {"file_count": len(sp)},
        )

        parser = SupportingFileParser()
        all_chunks: list[EvidenceChunk] = []
        all_sources: list[EvidenceSource] = []
        audits: list[SupportingFileExtractionAudit] = []
        bundle_parts: list[str] = []
        any_partial = False

        for item in sp:
            p = Path(str(item.get("path", "")))
            name = str(item.get("original_name") or p.name)
            pr = parser.parse(p, name)
            all_chunks.extend(pr.chunks)
            all_sources.extend(pr.sources)
            audits.append(pr.audit)
            bundle_parts.append(pr.bundle_section)
            if pr.audit.status != "ok":
                any_partial = True

        idx_path = work / "evidence.sqlite"
        idx: EvidenceIndex | None = None
        index_path_str = ""
        if all_chunks:
            idx = EvidenceIndex.build(idx_path, all_chunks)
            index_path_str = str(idx_path)

        audit_model = EvidenceIngestionAudit(
            job_id=job_id,
            files=audits,
            total_chunks=len(all_chunks),
            fts_index_built=bool(idx and idx.fts_enabled),
            fts_index_path=index_path_str or None,
        )
        audit_path = work / "evidence_extraction_audit.json"
        audit_path.write_text(audit_model.model_dump_json(indent=2), encoding="utf-8")

        if not sp:
            evidence_status_summary = (
                "No supporting evidence files supplied. Accuracy findings must degrade gracefully: "
                "use unsupported or unverified rather than speculative factual corrections."
            )
        else:
            fts_note = "on" if (idx and idx.fts_enabled) else "off"
            evidence_status_summary = (
                f"{len(sp)} supporting file(s) ingested; {len(all_chunks)} evidence chunk(s); retrieval index FTS={fts_note}."
            )
            if any_partial:
                evidence_status_summary += " Partial extraction on one or more files — treat excerpts as incomplete."

        bundle = "\n\n".join(bundle_parts).strip()

        await _emit(
            emit,
            "EVIDENCE_PARSED",
            "Supporting evidence normalized and chunked.",
            {"source_count": len(all_sources), "chunk_count": len(all_chunks)},
        )
        await _emit(
            emit,
            "EVIDENCE_RETRIEVAL_READY",
            "Evidence index ready for block-level retrieval.",
            {
                "chunk_count": len(all_chunks),
                "fts": bool(idx and idx.fts_enabled),
            },
        )

        return {
            "evidence_bundle": bundle,
            "evidence_sources": [s.model_dump(mode="json") for s in all_sources],
            "evidence_chunks": [c.model_dump(mode="json") for c in all_chunks],
            "evidence_index_path": index_path_str,
            "evidence_fts_enabled": bool(idx and idx.fts_enabled),
            "evidence_any_partial": any_partial,
            "evidence_status_summary": evidence_status_summary,
            "evidence_audit_path": str(audit_path),
            "stage_trace": _trace(state, "parse_supporting_evidence"),
        }

    async def normalize_document(state: ReviewPipelineState) -> dict[str, Any]:
        text = _normalize_text(state.get("main_text") or "")
        await _emit(emit, "DOC_NORMALIZED", "Text normalized for review.", {"chars": len(text)})
        return {"normalized_text": text, "stage_trace": _trace(state, "normalize_document")}

    async def build_review_context(state: ReviewPipelineState) -> dict[str, Any]:
        cfg = _cfg(state)
        fmt = str(state.get("main_source_format") or "docx")
        if fmt == "pdf":
            manuscript_policy = (
                "Primary manuscript was ingested from PDF text (page markers are included where extraction succeeded). "
                "Fix mode emits a new Word (.docx) built from that text — not a layout-faithful edited PDF."
            )
        else:
            manuscript_policy = (
                "Primary manuscript is Word (.docx): treat it as the main editable target in fix mode when applicable. "
                "Supporting files remain evidence-only in v1."
            )
        parse_notes = state.get("main_parse_warnings") or []
        note_block = ""
        if parse_notes:
            note_block = "Main document parse notes:\n" + "\n".join(f"- {n}" for n in parse_notes) + "\n\n"
        parts = [
            f"Document type: {cfg.document_type.value}",
            f"Review focus: {cfg.review_focus}",
            conflict_weighting_note(cfg.review_focus),
            f"Sensitive mode: {cfg.sensitive_mode}",
            f"Output mode: {cfg.output_mode}",
            "User context (purpose, audience, tone — not standalone evidence):\n"
            + (cfg.context_text or "(none)"),
            "Do-not-change (preserve names, clauses, numbers, wording as given):\n" + (cfg.do_not_change or "(none)"),
            note_block
            + "Supporting evidence policy: supporting files are factual/reference only; never edit them.\n"
            + manuscript_policy,
            "Evidence ingestion and retrieval status:\n" + (state.get("evidence_status_summary") or "(unknown)"),
        ]
        return {"review_context": "\n\n".join(parts).strip(), "stage_trace": _trace(state, "build_review_context")}

    async def chunk_document(state: ReviewPipelineState) -> dict[str, Any]:
        text = state.get("normalized_text") or ""
        cfg = _cfg(state)
        blocks = chunk_document_blocks(text, max_chars=int(cfg.max_chars_per_block))
        await _emit(emit, "CHUNKING_COMPLETE", "Document segmented for reviewers.", {"block_count": len(blocks)})
        return {"blocks": [b.model_dump(mode="json") for b in blocks], "stage_trace": _trace(state, "chunk_document")}

    async def _run_reviewer(
        state: ReviewPipelineState,
        *,
        role_key: str,
        resolved,
        system_builder,
        source_tag: str,
    ) -> dict[str, Any]:
        cfg = _cfg(state)
        blocks = _blocks(state)
        adapter = registry.adapter(resolved)
        has_supporting = int(state.get("supporting_count") or 0) > 0
        retriever = _make_evidence_retriever(state)

        seq = sorted(blocks, key=lambda b: (b.char_start, b.block_id))
        cap = cfg.max_blocks_for_review
        if cap is not None:
            seq = seq[: int(cap)]

        blocks_payload: list[dict[str, Any]] = []
        send_cap = int(cfg.max_block_send_chars)
        for blk in seq:
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

        user_obj: dict[str, Any] = {
            "static_review_context": state.get("review_context") or "",
            "user_context_text": cfg.context_text or "",
            "do_not_change": cfg.do_not_change or "",
            "document_type": cfg.document_type.value,
            "review_focus": cfg.review_focus,
            "document_blocks": blocks_payload,
            "large_document_limits": {
                "max_blocks_for_review": cfg.max_blocks_for_review,
                "blocks_omitted": max(0, len(blocks) - len(seq)),
                "max_block_send_chars": send_cap,
            },
        }
        user = json.dumps(user_obj, ensure_ascii=False)
        state_key = {
            "claude": "issues_claude_r1",
            "gpt": "issues_gpt_r1",
            "gemini": "issues_gemini_r1",
        }[role_key]
        started_stage = {
            "claude": "MODEL_REVIEW_CLAUDE_STARTED",
            "gpt": "MODEL_REVIEW_GPT_STARTED",
            "gemini": "MODEL_REVIEW_GEMINI_STARTED",
        }[role_key]
        complete_stage = {
            "claude": "MODEL_REVIEW_CLAUDE_COMPLETE",
            "gpt": "MODEL_REVIEW_GPT_COMPLETE",
            "gemini": "MODEL_REVIEW_GEMINI_COMPLETE",
        }[role_key]
        failed_stage = {
            "claude": "MODEL_REVIEW_CLAUDE_FAILED",
            "gpt": "MODEL_REVIEW_GPT_FAILED",
            "gemini": "MODEL_REVIEW_GEMINI_FAILED",
        }[role_key]

        phase1 = dict(state.get("reviewer_phase1") or {})

        if not adapter.configured:
            phase1[role_key] = {"ok": False, "error_code": "not_configured"}
            await _emit(
                emit,
                failed_stage,
                f"{role_key} reviewer unavailable.",
                {
                    "provider": resolved.provider,
                    "model_id": resolved.model_id,
                    "error_code": "not_configured",
                    "percent_complete": 72,
                    "reviewer": role_key,
                    "local_dev_hint": MISSING_SINGLE_PROVIDER_ENV_HINT,
                },
            )
            return {
                state_key: [],
                "reviewer_phase1": phase1,
                "stage_trace": _trace(state, f"run_{role_key}_review"),
            }

        rt = get_llm_job_runtime()
        if role_key == "gemini" and rt and rt.gemini_unavailable_for_job:
            code = GEMINI_DISABLED if rt.gemini_disabled_intentionally else GEMINI_UNAVAILABLE
            phase1[role_key] = {
                "ok": False,
                "error_code": code,
                "gemini_skip_reason": rt.gemini_skip_reason,
            }
            detail: dict[str, Any] = {
                "provider": resolved.provider,
                "model_id": resolved.model_id,
                "error_code": code,
                "percent_complete": 72,
                "reviewer": role_key,
                "gemini_skip_reason": rt.gemini_skip_reason,
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
                failed_stage,
                gem_msg,
                detail,
            )
            return {
                state_key: [],
                "reviewer_phase1": phase1,
                "stage_trace": _trace(state, f"run_{role_key}_review"),
            }

        if role_key == "gpt" and rt and rt.openai_unavailable_for_job:
            phase1[role_key] = {
                "ok": False,
                "error_code": OPENAI_UNAVAILABLE,
                "openai_skip_reason": rt.openai_skip_reason,
            }
            detail_gpt: dict[str, Any] = {
                "provider": resolved.provider,
                "model_id": resolved.model_id,
                "error_code": OPENAI_UNAVAILABLE,
                "percent_complete": 72,
                "reviewer": role_key,
                "openai_skip_reason": rt.openai_skip_reason,
                "openai_job_state": "PROVIDER_SKIPPED_FOR_REMAINDER_OF_JOB",
            }
            if (rt.openai_skip_reason or "") == "OPENAI_RATE_LIMITED":
                detail_gpt["openai_rate_limited"] = True
            gpt_msg = "GPT unavailable for this job — continuing with available reviewers."
            if (rt.openai_skip_reason or "") == "OPENAI_RATE_LIMITED":
                gpt_msg = "GPT rate-limited — continuing with available reviewers."
            await _emit(
                emit,
                failed_stage,
                gpt_msg,
                detail_gpt,
            )
            return {
                state_key: [],
                "reviewer_phase1": phase1,
                "stage_trace": _trace(state, f"run_{role_key}_review"),
            }

        await _emit(
            emit,
            started_stage,
            f"{role_key} review started.",
            {
                "provider": resolved.provider,
                "model_id": resolved.model_id,
                "percent_complete": 70,
                "reviewer": role_key,
            },
        )

        payload, err = await adapter.complete_reviewer_json(
            model_id=resolved.model_id,
            system=system_builder(cfg, has_supporting=has_supporting),
            user=user,
            validate=validate_reviewer_payload,
        )
        if payload is None:
            phase1[role_key] = {"ok": False, "error_code": err or "INVALID_JSON"}
            await _emit(
                emit,
                failed_stage,
                f"{role_key} reviewer failed structured output.",
                {
                    "provider": resolved.provider,
                    "model_id": resolved.model_id,
                    "error_code": err,
                    "percent_complete": 72,
                    "reviewer": role_key,
                },
            )
            return {
                state_key: [],
                "reviewer_phase1": phase1,
                "stage_trace": _trace(state, f"run_{role_key}_review"),
            }

        try:
            validate_reviewer_payload(payload)
        except ValidationError as exc:
            phase1[role_key] = {"ok": False, "error_code": "SCHEMA_MISMATCH"}
            await _emit(
                emit,
                failed_stage,
                f"{role_key} review output failed schema validation.",
                {
                    "provider": resolved.provider,
                    "model_id": resolved.model_id,
                    "error_code": "SCHEMA_MISMATCH",
                    "validation_errors": exc.errors()[:8],
                    "percent_complete": 72,
                    "reviewer": role_key,
                },
            )
            return {
                state_key: [],
                "reviewer_phase1": phase1,
                "stage_trace": _trace(state, f"run_{role_key}_review"),
            }

        finding = agent_finding_from_payload(payload, role=source_tag)
        clamped = [_clamp_issue(i, blocks) for i in finding.issue_candidates]
        issues = cap_reviewer_issues(clamped)
        for it in issues:
            if source_tag not in it.source_agents:
                it.source_agents.append(source_tag)
            it.discovered_in_cycle = 1
            it.cycle_number = 1
        phase1[role_key] = {"ok": True, "error_code": None}
        await _emit(
            emit,
            complete_stage,
            f"{role_key} review complete.",
            {
                "provider": resolved.provider,
                "model_id": resolved.model_id,
                "issues": len(issues),
                "percent_complete": 75,
                "reviewer": role_key,
            },
        )
        return {
            state_key: [i.model_dump(mode="json") for i in issues],
            "reviewer_phase1": phase1,
            "stage_trace": _trace(state, f"run_{role_key}_review"),
        }

    async def run_parallel_review_panel(state: ReviewPipelineState) -> dict[str, Any]:
        await _emit(
            emit,
            "TRI_REVIEW_PANEL_STARTED",
            "Running Claude, GPT, and Gemini reviews in parallel.",
            {"progress_percent": 62},
        )
        results = await asyncio.gather(
            _run_reviewer(
                state,
                role_key="claude",
                resolved=assign.author_intent,
                system_builder=claude_system,
                source_tag="claude_reviewer",
            ),
            _run_reviewer(
                state,
                role_key="gpt",
                resolved=assign.skeptical_reviewer,
                system_builder=gpt_system,
                source_tag="gpt_reviewer",
            ),
            _run_reviewer(
                state,
                role_key="gemini",
                resolved=assign.consistency_parser,
                system_builder=gemini_system,
                source_tag="gemini_reviewer",
            ),
        )
        merged: dict[str, Any] = {"reviewer_phase1": dict(state.get("reviewer_phase1") or {})}
        for part in results:
            merged["reviewer_phase1"].update(part.get("reviewer_phase1") or {})
            for k in ("issues_claude_r1", "issues_gpt_r1", "issues_gemini_r1"):
                if k in part:
                    merged[k] = part[k]
        merged["stage_trace"] = _trace(state, "run_parallel_review_panel")
        await _emit(
            emit,
            "TRI_REVIEW_PANEL_COMPLETE",
            "Parallel tri-review finished.",
            {"progress_percent": 70},
        )
        return merged

    async def merge_findings(state: ReviewPipelineState) -> dict[str, Any]:
        merged: list[dict[str, Any]] = []
        merged.extend(state.get("issues_claude_r1") or [])
        merged.extend(state.get("issues_gpt_r1") or [])
        merged.extend(state.get("issues_gemini_r1") or [])
        return {"issues_merged": merged, "stage_trace": _trace(state, "merge_findings")}

    async def dedupe_findings_node(state: ReviewPipelineState) -> dict[str, Any]:
        raw = [Issue.model_validate(x) for x in state.get("issues_merged") or []]
        deduped = dedupe_findings(raw)
        dumped = [i.model_dump(mode="json") for i in deduped]
        return {
            "issues_deduped": dumped,
            "issues_working": list(dumped),
            "stage_trace": _trace(state, "dedupe_findings"),
        }

    async def detect_conflicts_stage(state: ReviewPipelineState) -> dict[str, Any]:
        issues = _issues_from_state(state, "issues_working")
        cfg = _cfg(state)
        clusters = detect_material_conflicts(issues, **material_discrepancy_detect_kwargs(cfg))
        payload = [
            {"cluster_id": c.cluster_id, "reasons": list(c.reasons), "issues": [i.model_dump(mode="json") for i in c.issues]}
            for c in clusters
        ]
        await _emit(
            emit,
            "CROSS_MODEL_DEBATE_STARTED",
            "Cross-model conflict scan complete.",
            {"conflict_groups": len(payload)},
        )
        return {"conflict_clusters": payload, "stage_trace": _trace(state, "detect_conflicts")}

    async def fail_no_reviewer_output(state: ReviewPipelineState) -> dict[str, Any]:
        await _emit(
            emit,
            "FAIL_NO_REVIEWER_OUTPUT",
            "No reviewer model returned valid structured findings; cannot continue.",
            {"reviewer_phase1": state.get("reviewer_phase1") or {}},
        )
        raise RuntimeError(
            "no_reviewer_structured_output: all three reviewer models failed JSON/schema validation; "
            "no findings to review."
        )

    async def synthesize_ledger_without_arbitration(state: ReviewPipelineState) -> dict[str, Any]:
        issues = _issues_from_state(state, "issues_working")
        phase1 = state.get("reviewer_phase1") or {}
        ok = count_structured_successes(phase1)

        if ok < 2:
            await _emit(
                emit,
                "ARBITER_SKIPPED_NO_QUORUM",
                "Arbitration skipped: fewer than two reviewer models produced valid structured output.",
                {"reviewer_success_count": ok, "percent_complete": 96},
            )
        else:
            await _emit(
                emit,
                "ARBITER_SKIPPED_NO_CONFLICTS",
                "Arbitration skipped: no material cross-model conflict clusters to synthesize.",
                {"reviewer_success_count": ok, "percent_complete": 96},
            )

        if ok < 2:
            summary = (
                f"Partial review ledger: only {ok} reviewer model(s) produced valid structured findings. "
                "Cross-model arbitration was skipped because a two-model quorum was not met. "
                "Findings below are merged and deduplicated from the successful reviewer(s) only."
            )
        else:
            summary = (
                "Merged reviewer ledger: deduplicated findings retained without arbiter synthesis "
                "because no material cross-model conflict clusters were detected."
            )

        decision = ArbitrationDecision(
            executive_summary=summary,
            resolved_conflicts=[],
            issues=issues,
            proposed_edits=[],
        )
        arb_payload = {
            "executive_summary": decision.executive_summary,
            "issues": [i.model_dump(mode="json") for i in issues],
            "redline_html": "",
            "changes": [],
            "corrected_document_text": "",
        }
        return {
            "arbitration_decision": decision.model_dump(mode="json"),
            "issues_working": [i.model_dump(mode="json") for i in issues],
            "arbiter_payload": arb_payload,
            "skip_arbitration": True,
            "stage_trace": _trace(state, "synthesize_ledger_without_arbitration"),
        }

    def _route_post_detect(state: ReviewPipelineState) -> str:
        return post_detect_routing(state.get("reviewer_phase1"), state.get("conflict_clusters"))

    async def cross_model_debate(state: ReviewPipelineState) -> dict[str, Any]:
        cfg = _cfg(state)
        max_rounds = max(1, min(int(cfg.max_debate_rounds), 3))
        clusters_raw = state.get("conflict_clusters") or []
        if not clusters_raw:
            await _emit(
                emit,
                "CROSS_MODEL_DEBATE_ROUND_COMPLETE",
                "No debate required.",
                {"round": "skipped", "conflict_groups_remaining": 0},
            )
            return {"stage_trace": _trace(state, "cross_model_debate")}

        blocks = _blocks(state)
        sources = _sources(state)
        issues = {i.issue_id: i for i in _issues_from_state(state, "issues_working")}
        digest_parts: list[str] = []
        transcript: list[dict[str, Any]] = []
        kw = material_discrepancy_detect_kwargs(cfg)

        disputes: list[dict[str, Any]] = []
        for c in clusters_raw:
            its = [Issue.model_validate(x) for x in c.get("issues") or []]
            if len(its) < 2:
                continue
            blk_id = its[0].block_id
            blk = next((b for b in blocks if b.block_id == blk_id), blocks[0] if blocks else None)
            excerpts: list[str] = []
            if blk is not None:
                excerpts = rank_evidence_for_block(blk, sources, max_excerpts=3, max_chars_each=700)
            peer_objs = []
            for it in its:
                peer_objs.append(
                    {
                        "issue_id": it.issue_id,
                        "lineage_id": it.lineage_id,
                        "source_agents": it.source_agents,
                        "title": it.title,
                        "category": it.category.value,
                        "severity": it.severity.value,
                        "explanation": it.explanation,
                        "suggested_fix": it.suggested_fix,
                        "rationale_summary": (it.explanation or "")[:420],
                    }
                )
            disputes.append(
                {
                    "dispute_id": str(c.get("cluster_id")),
                    "reasons": c.get("reasons") or [],
                    "block_id": blk_id,
                    "original_block": blk.text if blk else "",
                    "review_context": (state.get("review_context") or "")[:6000],
                    "do_not_change": (cfg.do_not_change or "(none)"),
                    "supporting_evidence_excerpts": excerpts,
                    "peer_issues": peer_objs,
                }
            )

        async def run_round_for_agent(agent: str, resolved, system: str) -> dict[str, Any] | None:
            adapter = registry.adapter(resolved)
            if not adapter.configured:
                return None
            filtered_disputes: list[dict[str, Any]] = []
            for d in disputes:
                peers = list(d.get("peer_issues") or [])
                mine = [p for p in peers if agent in (p.get("source_agents") or [])]
                others = [p for p in peers if agent not in (p.get("source_agents") or [])]
                filtered_disputes.append(
                    {
                        **{k: v for k, v in d.items() if k != "peer_issues"},
                        "your_issues": mine,
                        "peer_issues": others,
                    }
                )
            user = json.dumps({"disputes": filtered_disputes, "your_agent": agent}, ensure_ascii=False)
            payload, err = await adapter.complete_reviewer_json(
                model_id=resolved.model_id,
                system=system,
                user=user,
                validate=validate_debate_round2_payload,
            )
            if payload is None:
                return {"agent": agent, "error": err}
            try:
                validate_debate_round2_payload(payload)
            except ValidationError as exc:
                return {"agent": agent, "error": f"debate_schema_invalid:{exc}", "payload": payload}
            return {"agent": agent, "payload": payload}

        for r in range(max_rounds):
            if not disputes:
                break
            digest_parts.append(f"## Debate round {r+1}")
            rt_debate = get_llm_job_runtime()
            r2_tasks = [
                run_round_for_agent("claude_reviewer", assign.author_intent, round2_system("Claude")),
            ]
            if not (
                rt_debate
                and rt_debate.openai_unavailable_for_job
                and registry.adapter(assign.skeptical_reviewer).configured
            ):
                r2_tasks.append(
                    run_round_for_agent("gpt_reviewer", assign.skeptical_reviewer, round2_system("GPT")),
                )
            if not (
                rt_debate
                and rt_debate.gemini_unavailable_for_job
                and registry.adapter(assign.consistency_parser).configured
            ):
                r2_tasks.append(
                    run_round_for_agent("gemini_reviewer", assign.consistency_parser, round2_system("Gemini"))
                )
            results = await asyncio.gather(*r2_tasks)
            transcript.append({"round": r + 1, "results": results})
            # Apply votes heuristically
            for item in results:
                if not item or item.get("error") or "payload" not in item:
                    continue
                votes = item["payload"].get("votes")
                if not isinstance(votes, list):
                    continue
                for v in votes:
                    if not isinstance(v, dict):
                        continue
                    stance = str(v.get("stance", "")).lower()
                    iid = str(v.get("issue_id") or "")
                    if stance == "withdraw" and iid in issues:
                        issues[iid] = issues[iid].model_copy(update={"status": IssueStatus.deferred})
                    if stance == "revise" and isinstance(v.get("revised_issue"), dict):
                        rev = issues_from_payload([v["revised_issue"]], default_block_id="doc-root", source_agent=item["agent"])
                        if rev:
                            new_i = rev[0]
                            old = issues.get(iid)
                            lineage = (old.lineage_id if old else None) or new_i.lineage_id or new_i.issue_id
                            new_i = new_i.model_copy(update={"lineage_id": lineage})
                            issues[new_i.issue_id] = new_i
            # Stop early if no material conflicts remain on working list
            working_list = list(issues.values())
            clusters_live = detect_material_conflicts(working_list, **kw)
            await _emit(
                emit,
                "CROSS_MODEL_DEBATE_ROUND_COMPLETE",
                f"Round {r + 1} complete.",
                {"round": r + 1, "conflict_groups_remaining": len(clusters_live)},
            )
            if not clusters_live:
                digest_parts.append("No material conflicts remain; stopping debate early.")
                break

        final_list = [i.model_dump(mode="json") for i in issues.values()]
        final_models = [Issue.model_validate(x) for x in final_list]
        live = detect_material_conflicts(final_models, **kw)
        await _emit(
            emit,
            "CROSS_MODEL_DEBATE_ROUND_COMPLETE",
            "Cross-model debate finished.",
            {"round": "final", "conflict_groups_remaining": len(live)},
        )
        conflict_payload = [
            {"cluster_id": c.cluster_id, "reasons": list(c.reasons), "issues": [i.model_dump(mode="json") for i in c.issues]}
            for c in live
        ]
        return {
            "issues_working": final_list,
            "debate_digest": (state.get("debate_digest") or "").strip() + "\n\n" + "\n".join(digest_parts).strip(),
            "round2_transcript": transcript,
            "conflict_clusters": conflict_payload,
            "stage_trace": _trace(state, "cross_model_debate"),
        }

    async def arbitrate_conflicts(state: ReviewPipelineState) -> dict[str, Any]:
        cfg = _cfg(state)
        await _emit(
            emit,
            "ARBITER_STARTED",
            "Arbiter synthesizing final ledger.",
            {"provider": assign.arbiter.provider, "model_id": assign.arbiter.model_id},
        )
        adapter = registry.adapter(assign.arbiter)
        if not adapter.configured:
            raise RuntimeError(f"arbiter_not_configured — {MISSING_SINGLE_PROVIDER_ENV_HINT}")

        blocks = _blocks(state)
        retriever = _make_evidence_retriever(state)
        hints: list[dict[str, Any]] = []
        for c in state.get("conflict_clusters") or []:
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
                        {
                            "source": ex.source_label,
                            "text": ex.text,
                            "score": round(ex.score, 4),
                            "method": ex.rank_method,
                        }
                        for ex in rr.excerpts
                    ],
                    "evidence_note": rr.evidence_note,
                }
            )
            if len(hints) >= 10:
                break

        excerpt = (state.get("normalized_text") or "")[:18_000]
        has_supporting = int(state.get("supporting_count") or 0) > 0
        user_obj = build_arbiter_user_dict(
            conflict_clusters=list(state.get("conflict_clusters") or []),
            round2_transcript=list(state.get("round2_transcript") or []),
            issues_working=list(state.get("issues_working") or []),
            document_excerpt=excerpt,
            output_mode=cfg.output_mode,
            global_evidence_status=str(state.get("evidence_status_summary") or ""),
            evidence_arbitration_hints=hints,
        )
        user = json.dumps(user_obj, ensure_ascii=False)
        payload, err = await adapter.complete_arbiter_json(
            model_id=assign.arbiter.model_id,
            system=arbiter_round3_system(cfg, cfg.output_mode, has_supporting=has_supporting),
            user=user,
            validate=validate_arbiter_payload,
        )
        if payload is None:
            raise RuntimeError(f"arbiter_failed:{err}")

        try:
            validate_arbiter_payload(payload)
        except ValidationError as exc:
            raise RuntimeError(f"arbiter_schema_invalid:{exc.errors()[:8]}") from exc

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
            executive_summary=str(payload.get("executive_summary", "")).strip() or "Arbitration complete.",
            resolved_conflicts=[],
            issues=issues,
            proposed_edits=edits,
            corrected_document_text=payload.get("corrected_document_text"),
            redline_html_fragment=payload.get("redline_html_fragment"),
        )
        await _emit(
            emit,
            "ARBITER_COMPLETE",
            "Final issues and edits resolved.",
            {"issues": len(issues), "edits": len(edits)},
        )
        return {
            "arbitration_decision": decision.model_dump(mode="json"),
            "issues_working": [i.model_dump(mode="json") for i in issues],
            "stage_trace": _trace(state, "arbitrate_conflicts"),
        }

    async def iterative_convergence_node(state: ReviewPipelineState) -> dict[str, Any]:
        cfg = _cfg(state)
        updates = await run_iterative_convergence(
            dict(state),
            cfg=cfg,
            registry=registry,
            assign=assign,
            emit=emit,
        )
        if not updates:
            meta: dict[str, Any] = {
                "cycles_completed": 1,
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
            }
            arb_dict = state.get("arbitration_decision")
            if arb_dict:
                issues_ws = list(ArbitrationDecision.model_validate(arb_dict).issues)
            else:
                issues_ws = [Issue.model_validate(x) for x in (state.get("issues_working") or []) if isinstance(x, dict)]
            disc_kw = material_discrepancy_detect_kwargs(cfg)
            clusters = detect_material_conflicts(issues_ws, **disc_kw)
            meta["unresolved_material_discrepancy_count"] = len(clusters)
            ir = cfg.iterative_review
            fix_clean = cfg.output_mode != "fix" or fix_mode_meets_clean_threshold(
                issues_ws,
                material_severities=set(ir.material_issue_severities),
                ignore_nits=ir.ignore_nits_for_fix_completion,
            )
            reconcile_single_pass_consensus(
                meta,
                configured_slots=configured_reviewer_slots(registry, assign),
                phase1=state.get("reviewer_phase1"),
                pairwise_cluster_count=len(clusters),
                fix_mode=cfg.output_mode == "fix",
                fix_clean=fix_clean,
                strict_three_reviewer_consensus=ir.strict_three_reviewer_consensus,
            )
            cs = str(meta.get("convergence_status") or "")
            if cs == "CONVERGENCE_REACHED":
                meta["stopped_with_remaining_discrepancies"] = False
            elif cs == "PARTIAL_CONSENSUS":
                meta["stopped_with_remaining_discrepancies"] = bool(len(clusters) > 0 or not fix_clean)
            else:
                meta["stopped_with_remaining_discrepancies"] = bool(
                    len(clusters) > 0
                    or not fix_clean
                    or meta.get("stopped_due_to_quorum_loss")
                    or meta.get("stopped_due_to_max_cycles")
                    or meta.get("stopped_due_to_provider_unavailable")
                    or meta.get("stopped_due_to_fatal_arbiter_failure")
                )
            return {"convergence_meta": meta, "stage_trace": _trace(state, "iterative_convergence")}
        return {**updates, "stage_trace": _trace(state, "iterative_convergence")}

    async def build_final_ledger(state: ReviewPipelineState) -> dict[str, Any]:
        cfg = _cfg(state)
        issues = _issues_from_state(state, "issues_working")
        by_sev, by_cat = _stats(issues)
        human_q = _human_evidence_queue(issues)

        arb_dict = state.get("arbitration_decision")
        if arb_dict:
            arb = ArbitrationDecision.model_validate(arb_dict)
        else:
            arb = ArbitrationDecision(
                executive_summary="No material conflicts detected; merged reviewer ledger retained.",
                issues=issues,
                proposed_edits=[],
                resolved_conflicts=[],
            )

        disclaimers = build_disclaimer_bundle(
            sensitive_mode=cfg.sensitive_mode,
            has_supporting_files=int(state.get("supporting_count") or 0) > 0,
        )

        digest = (state.get("debate_digest") or "").strip() or "No debate digest recorded."

        rt = get_llm_job_runtime()
        phase1 = state.get("reviewer_phase1") or {}
        participating: list[str] = []
        for key, tag in (("claude", "claude_reviewer"), ("gpt", "gpt_reviewer"), ("gemini", "gemini_reviewer")):
            if (phase1.get(key) or {}).get("ok") is True:
                participating.append(tag)
        if state.get("arbitration_decision") or state.get("arbiter_payload"):
            participating.append("arbiter")

        unavailable: list[str] = []
        if rt and rt.gemini_unavailable_for_job:
            unavailable.append("gemini_reviewer")
        if rt and rt.openai_unavailable_for_job:
            unavailable.append("gpt_reviewer")
        if not participating:
            participating = ["claude_reviewer", "gpt_reviewer", "gemini_reviewer", "arbiter"]

        summary = (arb.executive_summary or "").strip()
        notes: list[str] = []
        if rt and rt.gemini_unavailable_for_job and (phase1.get("gemini") or {}).get("ok") is not True:
            if rt.gemini_disabled_intentionally:
                notes.append(
                    "Google Gemini was disabled by configuration for this job (not a provider failure)."
                )
            elif (rt.gemini_skip_reason or "") == "GEMINI_RATE_LIMITED":
                notes.append(
                    "Google Gemini hit its per-job rate-limit budget (HTTP 429) and was skipped for the remainder "
                    "of this job. Consensus and the ledger below are based on the remaining active reviewers."
                )
            elif (rt.gemini_skip_reason or "") == "GEMINI_SERVICE_UNAVAILABLE":
                notes.append(
                    "Google Gemini returned repeated service errors (HTTP 503) and was skipped for the remainder "
                    "of this job. Consensus and the ledger below are based on the remaining active reviewers."
                )
            else:
                notes.append(
                    "Google Gemini became unavailable for this job after repeated rate limits (429). "
                    "Consensus and the ledger below are based on the remaining active reviewers."
                )
        if rt and rt.openai_unavailable_for_job and (phase1.get("gpt") or {}).get("ok") is not True:
            if (rt.openai_skip_reason or "") == "OPENAI_RATE_LIMITED":
                notes.append(
                    "OpenAI (GPT reviewer) hit its per-job rate-limit budget (HTTP 429) and was skipped for the "
                    "remainder of this job. Consensus and the ledger below are based on the remaining active reviewers."
                )
            else:
                notes.append(
                    "OpenAI (GPT reviewer) became unavailable for this job. "
                    "Consensus and the ledger below are based on the remaining active reviewers."
                )
        if notes:
            extra = " ".join(notes)
            if (phase1.get("claude") or {}).get("ok") and (phase1.get("gpt") or {}).get("ok") and (
                phase1.get("gemini") or {}
            ).get("ok"):
                pass
            elif sum(1 for k in ("claude", "gpt", "gemini") if (phase1.get(k) or {}).get("ok") is True) >= 2:
                extra += " Completed with available reviewers; quorum was satisfied."
            if summary:
                summary = summary.rstrip() + "\n\n" + extra
            else:
                summary = extra

        arb_for_ledger = arb.model_copy(update={"executive_summary": summary}) if summary != arb.executive_summary else arb

        ok_ct_phase1 = count_structured_successes(phase1)
        quorum_met = ok_ct_phase1 >= 2

        ledger = FinalLedger(
            job_id=state["job_id"],
            debate_digest=digest,
            participating_agents=participating,
            unavailable_agents=unavailable,
            quorum_met=quorum_met,
            arbitration=arb_for_ledger,
            disclaimers=disclaimers,
        )

        manifest = ArtifactManifest(
            job_id=state["job_id"],
            artifacts=[],
        )

        pipeline_out = {
            "job_id": state["job_id"],
            "final_ledger": ledger.model_dump(mode="json"),
            "render_plan": (state.get("render_plan") or {}),
            "final_issues": [i.model_dump(mode="json") for i in arb_for_ledger.issues],
            "stats_by_severity": by_sev,
            "stats_by_category": by_cat,
            "unresolved_human_evidence": [i.model_dump(mode="json") for i in human_q],
            "disclaimer_bundle": disclaimers.model_dump(mode="json"),
            "artifact_manifest": manifest.model_dump(mode="json"),
            "debate_digest": digest,
            "stage_trace": state.get("stage_trace") or [],
            "accepted_edits": [e.model_dump(mode="json") for e in arb_for_ledger.proposed_edits],
            "convergence_meta": state.get("convergence_meta") or {},
            "reviewer_phase1": state.get("reviewer_phase1") or {},
        }

        arb_payload = {
            "executive_summary": arb_for_ledger.executive_summary,
            "issues": [i.model_dump(mode="json") for i in arb_for_ledger.issues],
            "redline_html": arb_for_ledger.redline_html_fragment or "",
            "changes": [e.model_dump(mode="json") for e in arb_for_ledger.proposed_edits],
            "corrected_document_text": arb_for_ledger.corrected_document_text or "",
        }

        return {
            "final_ledger": ledger.model_dump(mode="json"),
            "stats_by_severity": by_sev,
            "stats_by_category": by_cat,
            "unresolved_human_evidence": [i.model_dump(mode="json") for i in human_q],
            "disclaimer_bundle": disclaimers.model_dump(mode="json"),
            "artifact_manifest": manifest.model_dump(mode="json"),
            "arbiter_payload": arb_payload,
            "pipeline_output": pipeline_out,
            "debate_digest": digest,
            "stage_trace": _trace(state, "build_final_ledger"),
        }

    async def build_render_plan(state: ReviewPipelineState) -> dict[str, Any]:
        cfg = _cfg(state)
        plan = RenderPlan(
            emit_corrected_docx=cfg.output_mode == "fix",
            emit_change_log_md=cfg.output_mode == "fix",
            emit_changes_json=cfg.output_mode == "fix",
        )
        return {"render_plan": plan.model_dump(mode="json"), "stage_trace": _trace(state, "build_render_plan")}

    async def render_outputs(state: ReviewPipelineState) -> dict[str, Any]:
        cfg = _cfg(state)
        if cfg.output_mode == "fix":
            await _emit(emit, "RENDERING_FIXED_DOC", "Rendering corrected package.", {})
        else:
            await _emit(emit, "RENDERING_REVIEW_DOC", "Rendering review package.", {})
        job_id = state["job_id"]
        artifacts_dir = paths.job_artifacts(job_id)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        main_path = Path(state["main_path"])
        original_docx = main_path if main_path.suffix.lower() == ".docx" else None
        arb_payload = state.get("arbiter_payload") or {}
        debate_digest = (state.get("debate_digest") or "").strip() or (state.get("final_ledger") or {}).get(
            "debate_digest", ""
        )
        document_text = state.get("normalized_text") or ""

        disc_raw = state.get("disclaimer_bundle")
        disclaimer_bundle = disc_raw if isinstance(disc_raw, dict) else None
        has_supporting_files = int(state.get("supporting_count") or 0) > 0

        if cfg.output_mode == "fix":
            file_rows = artifact_render.write_fix_bundle(
                artifacts_dir=artifacts_dir,
                original_docx_path=original_docx,
                document_text=document_text,
                arbiter_payload=arb_payload,
                has_supporting_files=has_supporting_files,
                disclaimer_bundle=disclaimer_bundle,
                sensitive_mode=cfg.sensitive_mode,
                do_not_change=cfg.do_not_change,
            )
        else:
            file_rows = artifact_render.write_review_bundle(
                artifacts_dir=artifacts_dir,
                original_docx_path=original_docx,
                document_text=document_text,
                arbiter_payload=arb_payload,
                debate_digest=str(debate_digest),
                has_supporting_files=has_supporting_files,
                disclaimer_bundle=disclaimer_bundle,
                sensitive_mode=cfg.sensitive_mode,
                main_source_format=str(state.get("main_source_format") or "docx"),
                main_original_filename=str(cfg.main_original_filename or "document"),
            )

        sev_map = state.get("stats_by_severity") or {}
        cat_map = state.get("stats_by_category") or {}
        uhe = state.get("unresolved_human_evidence") or []

        phase1 = state.get("reviewer_phase1") or {}
        ok_ct = sum(1 for k in ("claude", "gpt", "gemini") if (phase1.get(k) or {}).get("ok") is True)
        conv = state.get("convergence_meta") or {}

        if cfg.output_mode == "review":
            seed_payload = {
                "version": 1,
                "source_job_id": job_id,
                "arbitration_decision": state.get("arbitration_decision"),
                "blocks": state.get("blocks") or [],
                "normalized_text": document_text,
                "main_text": state.get("main_text") or "",
                "pages": int(state.get("pages") or 1),
                "parse_mime": str(state.get("parse_mime") or ""),
                "reviewer_phase1": phase1,
                "convergence_meta": conv,
                "conflict_clusters": state.get("conflict_clusters") or [],
                "issues_working": state.get("issues_working") or [],
            }
            seed_path = artifacts_dir / "fix_seed_snapshot.json"
            seed_path.write_text(json.dumps(seed_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            file_rows.append(
                {"name": "fix_seed_snapshot.json", "path": str(seed_path), "media_type": "application/json"}
            )

        conv_stat = str(conv.get("convergence_status") or "")
        conv_fail = conv.get("convergence_failure_code")
        partial = (
            ok_ct < 3
            or bool(conv_fail)
            or bool(conv.get("partial_consensus_only"))
            or conv_stat
            in {
                "QUORUM_LOST",
                "PARTIAL_REVIEW_COMPLETE",
                "PARTIAL_CONSENSUS",
                "MAX_CYCLES_REACHED",
                "HUMAN_FOLLOW_UP_REQUIRED",
            }
        )
        if partial:
            if conv_stat == "PARTIAL_CONSENSUS":
                msg = "Partial consensus reached; three-reviewer agreement was not obtained."
            elif conv_stat == "CONVERGENCE_REACHED" and bool(conv.get("partial_consensus_only")):
                msg = (
                    "Partial consensus on participating reviewers — convergence completed, "
                    "but full three-reviewer agreement was not achieved."
                )
            else:
                msg = "Partial review — generated from available reviewers; consensus incomplete."
            await _emit(
                emit,
                "PARTIAL_REVIEW_COMPLETE",
                msg,
                {
                    "reviewer_success_count": ok_ct,
                    "reviewer_failure_count": 3 - ok_ct,
                    "convergence_status": conv_stat,
                    "convergence_failure_code": conv_fail,
                    "percent_complete": 112,
                },
            )

        await _emit(
            emit,
            "PDF_RENDER_STARTED",
            "Rendering PDF artifacts (best effort).",
            {"percent_complete": 113},
        )
        issue_objs = [Issue.model_validate(x) for x in (arb_payload.get("issues") or []) if isinstance(x, dict)]
        material_sev = set(cfg.iterative_review.material_issue_severities)
        mat_un, nit_un = unresolved_material_and_nit(issue_objs, material_severities=material_sev)
        conv_line = str(conv.get("convergence_status") or "SINGLE_PASS")
        mode = str(conv.get("consensus_mode") or "")
        consensus_pdf_lines: list[str] = []
        if mode:
            consensus_pdf_lines.append(f"Consensus mode: {mode}")
        if conv.get("intended_reviewer_count") is not None:
            consensus_pdf_lines.append(
                f"Structured reviewer successes (convergence snapshot): "
                f"{conv.get('successful_reviewer_count')} / {conv.get('intended_reviewer_count')}"
            )
        if conv.get("full_consensus_achieved") is not None:
            consensus_pdf_lines.append(
                f"Full configured-panel consensus: {'yes' if conv.get('full_consensus_achieved') else 'no'}"
            )
        if conv.get("partial_consensus_only"):
            consensus_pdf_lines.append(
                "Partial reviewer coverage only — not full three-model agreement for a three-slot panel."
            )
        if isinstance(conv.get("unresolved_material_discrepancy_count"), int):
            consensus_pdf_lines.append(
                f"Unresolved material discrepancy clusters: {conv.get('unresolved_material_discrepancy_count')}"
            )
        if conv_fail and conv_stat != "CONVERGENCE_REACHED":
            consensus_pdf_lines.append(f"Stop / context code: {conv_fail}")
        rev_line = ", ".join(
            ("ok" if (phase1.get(k) or {}).get("ok") else "failed") for k in ("claude", "gpt", "gemini")
        )
        footer = "AI-assisted review — verify important facts before relying on these results."

        pdf_conversion_notes: list[str] = []

        if cfg.output_mode == "fix":
            ch_path = artifacts_dir / "changes.json"
            ch_rows: list[dict[str, Any]] = []
            if ch_path.is_file():
                try:
                    ch_rows = json.loads(ch_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    ch_rows = []
            cp = artifacts_dir / "change_log.pdf"
            if pdf_artifact_service.write_change_log_pdf(ch_rows, cp):
                file_rows.append({"name": "change_log.pdf", "path": str(cp), "media_type": "application/pdf"})
            cdoc = artifacts_dir / "corrected.docx"
            copdf = artifacts_dir / "corrected.pdf"
            if cdoc.is_file():
                if pdf_artifact_service.convert_docx_to_pdf(cdoc, copdf):
                    file_rows.append({"name": "corrected.pdf", "path": str(copdf), "media_type": "application/pdf"})
                else:
                    msg = "corrected.pdf not generated (DOCX→PDF conversion unavailable)"
                    logger.warning("%s job_id=%s", msg, job_id)
                    pdf_conversion_notes.append(msg)
                    from draftlens_api.artifacts.render import strip_pdf_page_markers_for_display

                    plain = strip_pdf_page_markers_for_display(str(document_text or ""))
                    if pdf_artifact_service.write_reviewed_text_fallback_pdf(
                        plain,
                        copdf,
                        document_name=str(cfg.main_original_filename or "document"),
                        doc_title="DraftLens corrected manuscript (text export)",
                    ):
                        file_rows.append({"name": "corrected.pdf", "path": str(copdf), "media_type": "application/pdf"})
                        pdf_conversion_notes.append(
                            "corrected.pdf delivered as cleaned text PDF (install Word+docx2pdf or LibreOffice for print-faithful export)."
                        )
        else:
            raw_issues = arb_payload.get("issues") or []
            issue_dicts = [x for x in raw_issues if isinstance(x, dict)]

            rlp = artifacts_dir / "redline.pdf"
            if pdf_artifact_service.write_redline_pdf(
                issue_dicts,
                rlp,
                title="DraftLens redline",
                document_name=cfg.main_original_filename,
            ):
                file_rows.append({"name": "redline.pdf", "path": str(rlp), "media_type": "application/pdf"})
            else:
                pdf_conversion_notes.append("redline.pdf not generated (fpdf2 unavailable)")

            ip = artifacts_dir / "issues.pdf"
            if issue_dicts and pdf_artifact_service.write_simple_issues_pdf(
                issue_dicts,
                ip,
                title="Issues",
            ):
                file_rows.append({"name": "issues.pdf", "path": str(ip), "media_type": "application/pdf"})

            rdoc = artifacts_dir / "reviewed.docx"
            rpdf = artifacts_dir / "reviewed.pdf"
            reviewed_pdf_via = "none"
            if rdoc.is_file():
                if pdf_artifact_service.convert_docx_to_pdf(rdoc, rpdf):
                    file_rows.append({"name": "reviewed.pdf", "path": str(rpdf), "media_type": "application/pdf"})
                    reviewed_pdf_via = "docx_convert"
                else:
                    msg = "reviewed.pdf not generated via DOCX→PDF (Word/LibreOffice converter unavailable)"
                    logger.warning("%s job_id=%s", msg, job_id)
                    pdf_conversion_notes.append(msg)
                    from draftlens_api.artifacts.render import strip_pdf_page_markers_for_display

                    plain = strip_pdf_page_markers_for_display(str(document_text or ""))
                    if pdf_artifact_service.write_reviewed_text_fallback_pdf(
                        plain,
                        rpdf,
                        document_name=str(cfg.main_original_filename or "document"),
                    ):
                        file_rows.append({"name": "reviewed.pdf", "path": str(rpdf), "media_type": "application/pdf"})
                        reviewed_pdf_via = "text_fallback"
                        pdf_conversion_notes.append(
                            "reviewed.pdf delivered as a cleaned text-layout PDF (install Word+docx2pdf or LibreOffice for print-faithful export from the DOCX)."
                        )

            summary_extra = [
                f"Redline PDF: {'generated' if (artifacts_dir / 'redline.pdf').is_file() else 'not available'}",
                f"Reviewed PDF: {reviewed_pdf_via}",
            ]
            if pdf_conversion_notes:
                summary_extra.append("PDF / export notes:")
                summary_extra.extend([f"- {n}" for n in pdf_conversion_notes[:6]])

            sp = artifacts_dir / "review_summary.pdf"
            if pdf_artifact_service.write_review_summary_pdf(
                path=sp,
                document_name=cfg.main_original_filename,
                output_mode=cfg.output_mode,
                reviewer_line=rev_line,
                cycles=int(conv.get("cycles_completed") or 1),
                stats_sev=dict(sev_map) if isinstance(sev_map, dict) else {},
                stats_cat=dict(cat_map) if isinstance(cat_map, dict) else {},
                convergence_line=conv_line,
                consensus_coverage_lines=consensus_pdf_lines or None,
                footer=footer,
                extra_lines=summary_extra,
            ):
                file_rows.append({"name": "review_summary.pdf", "path": str(sp), "media_type": "application/pdf"})

        await _emit(emit, "PDF_RENDER_COMPLETE", "PDF rendering finished.", {"percent_complete": 114})

        file_rows = artifact_visibility_policy.annotate_rows(
            [dict(x) for x in file_rows],
            output_mode=cfg.output_mode,
        )
        artifact_names = {str(r.get("name", "")) for r in file_rows}

        stats_path = artifacts_dir / "pipeline_stats.json"
        total_issues = sum(int(v) for v in sev_map.values()) if isinstance(sev_map, dict) else 0
        consensus_reached = len(uhe) == 0
        stats_path.write_text(
            json.dumps(
                {
                    "total_issues": total_issues,
                    "stats_by_severity": sev_map,
                    "stats_by_category": cat_map,
                    "unresolved_human_evidence": uhe,
                    "consensus_reached": consensus_reached,
                    "consensus_mode": conv.get("consensus_mode"),
                    "intended_reviewer_count": conv.get("intended_reviewer_count"),
                    "convergence_successful_reviewer_count": conv.get("successful_reviewer_count"),
                    "required_full_consensus_count": conv.get("required_full_consensus_count"),
                    "full_three_reviewer_consensus_achieved": bool(conv.get("full_consensus_achieved")),
                    "partial_consensus_only": bool(conv.get("partial_consensus_only")),
                    "pairwise_material_discrepancy_count": conv.get("pairwise_material_discrepancy_count"),
                    "participation_coverage_deficit": conv.get("participation_coverage_deficit"),
                    "strict_three_reviewer_consensus": cfg.iterative_review.strict_three_reviewer_consensus,
                    "fix_alignment_audit_passed": conv.get("fix_alignment_audit_passed"),
                    "fix_alignment_audit_errors": conv.get("fix_alignment_audit_errors"),
                    "reviewer_success_count": ok_ct,
                    "reviewer_failure_count": 3 - ok_ct,
                    "reviewer_full_consensus": ok_ct == 3,
                    "partial_quorum_used": ok_ct < 3,
                    "cycle_count_completed": int(conv.get("cycles_completed") or 1),
                    "convergence_status": conv_line,
                    "convergence_failure_code": conv.get("convergence_failure_code"),
                    "max_cycles_reached": bool(conv.get("max_cycles_reached")),
                    "unresolved_material_issue_count": mat_un,
                    "unresolved_nit_count": nit_un,
                    "unresolved_material_discrepancy_count": conv.get("unresolved_material_discrepancy_count"),
                    "newly_found_material_discrepancy_count": conv.get("newly_found_material_discrepancy_count"),
                    "resolved_material_discrepancy_count": conv.get("resolved_material_discrepancy_count"),
                    "stopped_with_remaining_discrepancies": bool(conv.get("stopped_with_remaining_discrepancies")),
                    "stopped_due_to_max_cycles": bool(conv.get("stopped_due_to_max_cycles")),
                    "stopped_due_to_quorum_loss": bool(conv.get("stopped_due_to_quorum_loss")),
                    "stopped_due_to_provider_unavailable": bool(conv.get("stopped_due_to_provider_unavailable")),
                    "stopped_due_to_fatal_arbiter_failure": bool(conv.get("stopped_due_to_fatal_arbiter_failure")),
                    "pdf_conversion_notes": pdf_conversion_notes,
                    "unresolved_cluster_summaries": conv.get("unresolved_cluster_summaries") or [],
                    "artifact_pdf_flags": {
                        "reviewed.pdf": "reviewed.pdf" in artifact_names,
                        "redline.pdf": "redline.pdf" in artifact_names,
                        "issues.pdf": "issues.pdf" in artifact_names,
                        "review_summary.pdf": "review_summary.pdf" in artifact_names,
                        "corrected.pdf": "corrected.pdf" in artifact_names,
                        "change_log.pdf": "change_log.pdf" in artifact_names,
                    },
                    "artifact_tiers": {r["name"]: r.get("tier", "primary") for r in file_rows},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        manifest_path = artifacts_dir / "pipeline_manifest.json"
        manifest = ArtifactManifest(
            job_id=job_id,
            artifacts=[
                ArtifactRecord(name=str(fr["name"]), path=str(fr["path"]), media_type=fr.get("media_type"), byte_size=None)
                for fr in file_rows
            ]
            + [
                ArtifactRecord(name="pipeline_stats.json", path=str(stats_path), media_type="application/json"),
                ArtifactRecord(name="pipeline_manifest.json", path=str(manifest_path), media_type="application/json"),
            ],
        )
        manifest_path.write_text(json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8")
        file_rows = list(file_rows) + [
            {"name": "pipeline_stats.json", "path": str(stats_path), "media_type": "application/json"},
            {"name": "pipeline_manifest.json", "path": str(manifest_path), "media_type": "application/json"},
        ]

        return {
            "artifact_file_rows": file_rows,
            "artifact_manifest": manifest.model_dump(mode="json"),
            "stage_trace": _trace(state, "render_outputs"),
        }

    async def persist_artifacts(state: ReviewPipelineState) -> dict[str, Any]:
        return {"stage_trace": _trace(state, "persist_artifacts")}

    async def finalize_job(state: ReviewPipelineState) -> dict[str, Any]:
        return {"stage_trace": _trace(state, "finalize_job")}

    g = StateGraph(ReviewPipelineState)
    for name, fn in [
        ("hydrate_post_review_fix_seed", hydrate_post_review_fix_seed),
        ("ingest_main_document", ingest_main_document),
        ("ingest_supporting_files", ingest_supporting_files),
        ("parse_main_document", parse_main_document),
        ("parse_supporting_evidence", parse_supporting_evidence),
        ("normalize_document", normalize_document),
        ("build_review_context", build_review_context),
        ("chunk_document", chunk_document),
        ("run_parallel_review_panel", run_parallel_review_panel),
        ("merge_findings", merge_findings),
        ("dedupe_findings", dedupe_findings_node),
        ("detect_conflicts", detect_conflicts_stage),
        ("fail_no_reviewer_output", fail_no_reviewer_output),
        ("synthesize_ledger_without_arbitration", synthesize_ledger_without_arbitration),
        ("cross_model_debate", cross_model_debate),
        ("arbitrate_conflicts", arbitrate_conflicts),
        ("iterative_convergence", iterative_convergence_node),
        ("build_final_ledger", build_final_ledger),
        ("build_render_plan", build_render_plan),
        ("render_outputs", render_outputs),
        ("persist_artifacts", persist_artifacts),
        ("finalize_job", finalize_job),
    ]:
        g.add_node(name, fn)

    def _route_pipeline_entry(state: ReviewPipelineState) -> str:
        cfg = _cfg(state)
        if cfg.output_mode == "fix" and cfg.post_review_fix_seed_job_id:
            seed = paths.job_artifacts(cfg.post_review_fix_seed_job_id) / "fix_seed_snapshot.json"
            if seed.is_file():
                return "hydrate_post_review_fix_seed"
        return "ingest_main_document"

    g.add_conditional_edges(
        START,
        _route_pipeline_entry,
        {
            "hydrate_post_review_fix_seed": "hydrate_post_review_fix_seed",
            "ingest_main_document": "ingest_main_document",
        },
    )
    g.add_edge("hydrate_post_review_fix_seed", "iterative_convergence")
    chain = [
        "ingest_main_document",
        "ingest_supporting_files",
        "parse_main_document",
        "parse_supporting_evidence",
        "normalize_document",
        "build_review_context",
        "chunk_document",
        "run_parallel_review_panel",
        "merge_findings",
        "dedupe_findings",
        "detect_conflicts",
    ]
    for i in range(len(chain) - 1):
        g.add_edge(chain[i], chain[i + 1])

    g.add_conditional_edges(
        "detect_conflicts",
        _route_post_detect,
        {
            "fail_no_reviewer_output": "fail_no_reviewer_output",
            "cross_model_debate": "cross_model_debate",
            "synthesize_ledger_without_arbitration": "synthesize_ledger_without_arbitration",
        },
    )
    g.add_edge("fail_no_reviewer_output", END)
    g.add_edge("cross_model_debate", "arbitrate_conflicts")
    g.add_edge("synthesize_ledger_without_arbitration", "iterative_convergence")
    g.add_edge("arbitrate_conflicts", "iterative_convergence")
    g.add_edge("iterative_convergence", "build_final_ledger")
    g.add_edge("build_final_ledger", "build_render_plan")
    g.add_edge("build_render_plan", "render_outputs")
    g.add_edge("render_outputs", "persist_artifacts")
    g.add_edge("persist_artifacts", "finalize_job")
    g.add_edge("finalize_job", END)
    return g


async def execute_review_pipeline(
    *,
    job_id: str,
    main_path: Path,
    supporting_pairs: list[tuple[Path, str]],
    job_config: ReviewJobConfig,
    paths: DataPaths,
    registry: ModelRegistry,
    emit: EmitFn | None = None,
) -> dict[str, Any]:
    """Run the full 20-stage LangGraph pipeline and return artifacts + payloads for DB persistence."""
    assign = registry.assignment()
    active = 0
    for rm in (assign.author_intent, assign.skeptical_reviewer, assign.consistency_parser):
        if registry.adapter(rm).configured:
            active += 1
    if active < 2:
        raise RuntimeError(f"quorum_not_met: need>=2 configured reviewers; got {active}. {MULTI_MODEL_QUORUM_HINT}")

    graph = build_review_pipeline_graph(registry, paths=paths, emit=emit).compile()
    supporting_paths = [{"path": str(Path(p).resolve()), "original_name": n} for p, n in supporting_pairs]
    init: ReviewPipelineState = {
        "job_id": job_id,
        "job_config": job_config.model_dump(mode="json"),
        "main_path": str(main_path),
        "supporting_count": len(supporting_paths),
        "supporting_paths": supporting_paths,
        "evidence_bundle": "",
        "evidence_sources": [],
        "evidence_chunks": [],
        "evidence_index_path": "",
        "evidence_fts_enabled": False,
        "evidence_any_partial": False,
        "evidence_status_summary": "",
        "evidence_audit_path": "",
        "debate_digest": "",
        "stage_trace": [],
        "reviewer_phase1": {},
    }
    rt = build_llm_job_runtime(job_id, get_settings())
    token = attach_llm_job_runtime(rt)
    try:
        final_state = await graph.ainvoke(init)
    finally:
        reset_llm_job_runtime(token)
    return final_state


__all__ = ["build_review_pipeline_graph", "execute_review_pipeline", "ReviewPipelineState"]
