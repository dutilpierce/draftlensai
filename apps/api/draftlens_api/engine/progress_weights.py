"""Stage → progress percent (0–100) for SSE; weighted by pipeline phase, not wall-clock."""

from __future__ import annotations

# Ingest + parse + normalize + chunk + tri-review + merge/dedupe/conflict + debate/arb + iterative + ledger + render + export
_STAGE_WEIGHTS_REVIEW: dict[str, float] = {
    "UPLOAD_RECEIVED": 2,
    "ingest_main_document": 4,
    "ingest_supporting_files": 5,
    "parse_main_document": 8,
    "parse_supporting_evidence": 10,
    "normalize_document": 12,
    "build_review_context": 14,
    "chunk_document": 18,
    "run_parallel_review_panel": 45,
    "MODEL_REVIEW_CLAUDE_STARTED": 20,
    "MODEL_REVIEW_CLAUDE_COMPLETE": 28,
    "MODEL_REVIEW_GPT_STARTED": 22,
    "MODEL_REVIEW_GPT_COMPLETE": 34,
    "MODEL_REVIEW_GEMINI_STARTED": 24,
    "MODEL_REVIEW_GEMINI_COMPLETE": 40,
    "merge_findings": 48,
    "dedupe_findings": 50,
    "detect_conflicts": 52,
    "CROSS_MODEL_DEBATE_STARTED": 54,
    "cross_model_debate": 58,
    "ARBITER_COMPLETE": 65,
    "arbitrate_conflicts": 65,
    "synthesize_ledger_without_arbitration": 65,
    "iterative_convergence": 78,
    "ITERATIVE_CYCLE_STARTED": 72,
    "ITERATIVE_CYCLE_COMPLETE": 80,
    "build_final_ledger": 85,
    "build_render_plan": 88,
    "render_outputs": 94,
    "PDF_RENDER_STARTED": 96,
    "persist_artifacts": 98,
    "finalize_job": 99,
    "EXPORT_COMPLETE": 99,
    "completed": 100,
    "PARTIAL_REVIEW_COMPLETE": 99,
}

_STAGE_WEIGHTS_FIX_EXTRA: dict[str, float] = {
    "APPLY_FIXES_STARTED": 4,
    "APPLY_FIXES_HYDRATE_STARTED": 6,
    "APPLY_FIXES_HYDRATE_COMPLETE": 12,
    "FIX_JOB_CREATED_FROM_REVIEW": 8,
    "FIX_BASELINE_REVIEW_STARTED": 18,
    "FIX_BASELINE_REVIEW_COMPLETE": 22,
    "FIX_RECONCILIATION_CYCLE_STARTED": 55,
    "FIX_CANDIDATE_GENERATION_STARTED": 58,
    "FIX_REAPPLY_STARTED": 60,
    "POST_REVIEW_TRI_REVIEW_STARTED": 62,
    "POST_REVIEW_TRI_REVIEW_COMPLETE": 70,
    "FINAL_ALIGNMENT_AUDIT_STARTED": 90,
    "FINAL_ALIGNMENT_AUDIT_COMPLETE": 95,
    "FINAL_ALIGNMENT_AUDIT_FAILED": 92,
    "FIX_CONVERGENCE_REACHED": 96,
    "JOB_FAILED": 0,
}


def progress_percent_for_stage(stage: str, *, output_mode: str, post_review_hydrate: bool = False) -> int | None:
    w = dict(_STAGE_WEIGHTS_REVIEW)
    w.update(_STAGE_WEIGHTS_FIX_EXTRA)
    if stage in w:
        return int(min(100, max(0, round(w[stage]))))
    if "ALIGNMENT" in stage or "alignment" in stage.lower():
        return 91
    if post_review_hydrate and stage in ("hydrate_post_review_fix_seed",):
        return 10
    if output_mode == "fix" and stage == "iterative_convergence":
        return 55
    return None
