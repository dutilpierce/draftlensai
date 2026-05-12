"""
Pre-arbitration routing: quorum of successful structured reviewers + material conflicts.

Pure helpers keep routing testable without compiling LangGraph.
"""

from __future__ import annotations

from typing import Any, Literal

REVIEWER_ROLE_KEYS = ("claude", "gpt", "gemini")


def count_structured_successes(reviewer_phase1: dict[str, Any] | None) -> int:
    """How many of the three reviewer roles returned ok structured output."""
    p = reviewer_phase1 or {}
    return sum(1 for k in REVIEWER_ROLE_KEYS if (p.get(k) or {}).get("ok") is True)


def has_arbitratable_conflict_clusters(conflict_clusters: list[Any] | None) -> bool:
    """True only if at least one cluster has 2+ issues (cross-model material dispute)."""
    for c in conflict_clusters or []:
        if not isinstance(c, dict):
            continue
        if len(c.get("issues") or []) >= 2:
            return True
    return False


def post_detect_routing(
    reviewer_phase1: dict[str, Any] | None,
    conflict_clusters: list[Any] | None,
) -> Literal["fail_no_reviewer_output", "cross_model_debate", "synthesize_ledger_without_arbitration"]:
    """
    After conflict detection:
    - fail if no reviewer produced valid structured output
    - debate+arbiter only if >=2 successes AND there are multi-issue conflict clusters
    - otherwise synthesize ledger from deduped issues without calling the arbiter model
    """
    ok = count_structured_successes(reviewer_phase1)
    if ok == 0:
        return "fail_no_reviewer_output"
    if ok >= 2 and has_arbitratable_conflict_clusters(conflict_clusters):
        return "cross_model_debate"
    return "synthesize_ledger_without_arbitration"


def build_arbiter_user_dict(
    *,
    conflict_clusters: list[Any],
    round2_transcript: list[Any],
    issues_working: list[Any],
    document_excerpt: str,
    output_mode: str,
    global_evidence_status: str,
    evidence_arbitration_hints: list[Any],
    max_issues: int = 100,
    max_clusters: int = 20,
    max_round2: int = 12,
    max_excerpt_chars: int = 18_000,
) -> dict[str, Any]:
    """Bounded, JSON-serializable arbiter user payload (reduces 400s from oversized bodies)."""
    clusters = list(conflict_clusters or [])[:max_clusters]
    issues = list(issues_working or [])
    if len(issues) > max_issues:
        issues = issues[:max_issues]
    r2 = list(round2_transcript or [])
    if len(r2) > max_round2:
        r2 = r2[-max_round2:]
    excerpt = (document_excerpt or "")[:max_excerpt_chars]
    return {
        "conflict_clusters": clusters,
        "round2": r2,
        "issues_working": issues,
        "document_excerpt": excerpt,
        "output_mode": output_mode,
        "global_evidence_status": global_evidence_status or "",
        "evidence_arbitration_hints": list(evidence_arbitration_hints or [])[:15],
    }
