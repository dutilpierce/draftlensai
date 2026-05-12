"""
Predictable ordering for persisted job status stages (SSE + `job_status_events`).

Parallel model reviewers may interleave (same rank). Early pipeline and late export
stages are strictly ordered by cumulative peak rank — a stage must not appear after
a higher-ranked stage has already been observed.
"""

from __future__ import annotations

# Same numeric rank => allowed to repeat / interleave (e.g. concurrent reviewers).
STAGE_RANK: dict[str, int] = {
    "UPLOAD_RECEIVED": 10,
    "APPLY_FIXES_STARTED": 12,
    "SUPPORTING_FILES_INGESTED": 20,
    "DOC_PARSED": 30,
    "EVIDENCE_PARSE_STARTED": 40,
    "EVIDENCE_PARSED": 45,
    "EVIDENCE_RETRIEVAL_READY": 50,
    "DOC_NORMALIZED": 60,
    "APPLY_FIXES_HYDRATE_STARTED": 65,
    "APPLY_FIXES_HYDRATE_COMPLETE": 66,
    "FIX_JOB_CREATED_FROM_REVIEW": 67,
    "CHUNKING_COMPLETE": 70,
    "TRI_REVIEW_PANEL_STARTED": 80,
    "TRI_REVIEW_PANEL_COMPLETE": 81,
    "MODEL_REVIEW_CLAUDE_STARTED": 80,
    "MODEL_REVIEW_CLAUDE_COMPLETE": 81,
    "MODEL_REVIEW_CLAUDE_FAILED": 81,
    "MODEL_REVIEW_GPT_STARTED": 80,
    "MODEL_REVIEW_GPT_COMPLETE": 81,
    "MODEL_REVIEW_GPT_FAILED": 81,
    "MODEL_REVIEW_GEMINI_STARTED": 80,
    "MODEL_REVIEW_GEMINI_COMPLETE": 81,
    "MODEL_REVIEW_GEMINI_FAILED": 81,
    "CROSS_MODEL_DEBATE_STARTED": 90,
    "CROSS_MODEL_DEBATE_ROUND_COMPLETE": 95,
    "ARBITER_SKIPPED_NO_QUORUM": 98,
    "ARBITER_SKIPPED_NO_CONFLICTS": 98,
    "ARBITER_STARTED": 100,
    "ARBITER_COMPLETE": 105,
    "FIX_BASELINE_REVIEW_STARTED": 105,
    "FIX_BASELINE_REVIEW_COMPLETE": 105,
    "ITERATIVE_CYCLE_STARTED": 106,
    "ITERATIVE_CYCLE_COMPLETE": 106,
    "ITERATIVE_SKIPPED_NO_QUORUM": 106,
    "FIX_RECONCILIATION_CYCLE_STARTED": 106,
    "FIX_RECONCILIATION_CYCLE_COMPLETE": 106,
    "FIX_CANDIDATE_GENERATION_STARTED": 106,
    "FIX_CANDIDATE_GENERATION_COMPLETE": 106,
    "FIX_REAPPLY_STARTED": 106,
    "FIX_REAPPLY_COMPLETE": 106,
    "FIX_CANDIDATE_TRI_REVIEW_STARTED": 106,
    "FIX_CANDIDATE_TRI_REVIEW_COMPLETE": 106,
    "FINAL_ALIGNMENT_AUDIT_STARTED": 107,
    "FINAL_ALIGNMENT_AUDIT_COMPLETE": 107,
    "FINAL_ALIGNMENT_AUDIT_FAILED": 107,
    "FIX_CONVERGENCE_REACHED": 107,
    "FIX_HUMAN_FOLLOW_UP_REQUIRED": 107,
    "CONVERGENCE_REACHED": 107,
    "PARTIAL_CONSENSUS": 107,
    "PARTIAL_REVIEW_COMPLETE": 108,
    "HUMAN_FOLLOW_UP_REQUIRED": 107,
    "PDF_RENDER_STARTED": 109,
    "PDF_RENDER_COMPLETE": 109,
    "RENDERING_FIXED_DOC": 110,
    "RENDERING_REVIEW_DOC": 110,
    "EXPORT_COMPLETE": 120,
    "completed": 200,
    "failed": 200,
    "JOB_FAILED": 200,
    "FAIL_NO_REVIEWER_OUTPUT": 200,
}

DEFAULT_UNKNOWN_RANK = 75  # between chunking and reviewer fan-out


def rank_for_stage(stage: str) -> int:
    return STAGE_RANK.get(stage, DEFAULT_UNKNOWN_RANK)


def assert_monotonic_stage_sequence(stages: list[str]) -> None:
    """
    Raises AssertionError if any stage has rank strictly below the peak rank seen earlier.

    Repeats and equal ranks are allowed (duplicate emits, parallel reviewers).
    """
    peak = -1
    for s in stages:
        r = rank_for_stage(s)
        if r < peak:
            raise AssertionError(f"stage_order_regression: {s!r} rank {r} after peak {peak}")
        peak = max(peak, r)


def validate_monotonic_stage_sequence(stages: list[str]) -> tuple[bool, str | None]:
    try:
        assert_monotonic_stage_sequence(stages)
    except AssertionError as exc:
        return False, str(exc)
    return True, None
