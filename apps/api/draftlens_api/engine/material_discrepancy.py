"""
Material reviewer discrepancy — explicit, code-first definitions.

These rules classify *cross-model* disagreement on overlapping spans as material
(inspectable, drives convergence cycles) vs non-material (ignored for discrepancy count).

Non-material pairs must not keep convergence running.
"""

from __future__ import annotations

import re

from draftlens_api.domain.enums import IssueCategory, IssueSeverity
from draftlens_api.domain.models import Issue

# Reasons returned from pair analysis (also persisted on conflict clusters).
REASON_SAME_SPAN_MATERIALLY_DIFFERENT_FIX = "same_span_materially_different_fix"
REASON_ISSUE_EXISTS_VS_NO_ISSUE = "issue_exists_vs_no_issue"
REASON_SEVERITY_DISAGREEMENT = "severity_disagreement"
REASON_EVIDENCE_DISAGREEMENT = "evidence_disagreement"
REASON_MEANING_CHANGE_VS_PRESERVING_REWRITE = "meaning_change_vs_preserving_rewrite"
REASON_KEEP_VS_CHANGE_DISAGREEMENT = "keep_vs_change_disagreement"
REASON_LOCK_OR_DN_CHANGE_DISPUTED = "lock_or_dn_change_disputed"

MATERIAL_DISCREPANCY_REASON_CODES: frozenset[str] = frozenset(
    {
        REASON_SAME_SPAN_MATERIALLY_DIFFERENT_FIX,
        REASON_ISSUE_EXISTS_VS_NO_ISSUE,
        REASON_SEVERITY_DISAGREEMENT,
        REASON_EVIDENCE_DISAGREEMENT,
        REASON_MEANING_CHANGE_VS_PRESERVING_REWRITE,
        REASON_KEEP_VS_CHANGE_DISAGREEMENT,
        REASON_LOCK_OR_DN_CHANGE_DISPUTED,
    }
)

# Reasons that remain material even when both severities are outside `material_severities`
# (e.g. two nits still disagree on whether an edit is allowed vs locked span).
STRONG_MATERIAL_REASONS: frozenset[str] = frozenset(
    {
        REASON_ISSUE_EXISTS_VS_NO_ISSUE,
        REASON_MEANING_CHANGE_VS_PRESERVING_REWRITE,
        REASON_KEEP_VS_CHANGE_DISAGREEMENT,
        REASON_LOCK_OR_DN_CHANGE_DISPUTED,
    }
)


def _sev_rank(sev: IssueSeverity) -> int:
    return {"nit": 0, "minor": 1, "major": 2, "critical": 3}.get(sev.value, 1)


def _spans_overlap(a: Issue, b: Issue) -> bool:
    if a.block_id != b.block_id:
        return False
    return not (a.char_end < b.char_start or b.char_end < a.char_start)


def _fix_norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _fix_jaccard(a: str, b: str) -> float:
    ta = {x for x in re.findall(r"[a-z0-9]{4,}", _fix_norm(a))}
    tb = {x for x in re.findall(r"[a-z0-9]{4,}", _fix_norm(b))}
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _meaning_change_heuristic(fix: str) -> bool:
    f = _fix_norm(fix)
    if not f:
        return False
    aggressive = (
        "rewrite",
        "replace",
        "remove",
        "delete",
        "reframe",
        "contradict",
        "invert",
        "change meaning",
        "new claim",
    )
    return any(k in f for k in aggressive)


def _meaning_preserve_heuristic(fix: str) -> bool:
    f = _fix_norm(fix)
    gentle = ("comma", "typo", "spelling", "grammar", "clarify", "tighten", "word choice", "punctuation")
    return any(k in f for k in gentle)


def _materially_different_fixes(a: Issue, b: Issue) -> bool:
    fa, fb = a.suggested_fix.strip(), b.suggested_fix.strip()
    if len(fa) < 8 and len(fb) < 8:
        return False
    if not fa or not fb:
        return False
    return _fix_jaccard(fa, fb) < 0.28


def _severity_disagreement(a: Issue, b: Issue, *, min_rank_gap: int) -> bool:
    return abs(_sev_rank(a.severity) - _sev_rank(b.severity)) >= min_rank_gap


def _evidence_disagreement(a: Issue, b: Issue) -> bool:
    if a.category != IssueCategory.accuracy or b.category != IssueCategory.accuracy:
        return False
    la, lb = len(a.evidence_basis.strip()), len(b.evidence_basis.strip())
    return (la > 48 and lb < 6) or (lb > 48 and la < 6)


def _issue_vs_no_issue(a: Issue, b: Issue) -> bool:
    fa, fb = a.suggested_fix.strip(), b.suggested_fix.strip()
    one_empty = (len(fa) < 3) != (len(fb) < 3)
    substantive = len(fa) > 20 or len(fb) > 20
    return one_empty and substantive and _spans_overlap(a, b)


def _keep_vs_change(a: Issue, b: Issue) -> bool:
    fa, fb = _fix_norm(a.suggested_fix), _fix_norm(b.suggested_fix)
    noop_phrases = ("no change", "leave as-is", "keep as written", "ok as-is", "no edit")
    a_noop = any(p in fa for p in noop_phrases) or len(a.suggested_fix.strip()) < 4
    b_noop = any(p in fb for p in noop_phrases) or len(b.suggested_fix.strip()) < 4
    return (a_noop ^ b_noop) and (len(a.suggested_fix) > 18 or len(b.suggested_fix) > 18)


def _meaning_rewrite_conflict(a: Issue, b: Issue) -> bool:
    if not _spans_overlap(a, b):
        return False
    ma, mb = _meaning_change_heuristic(a.suggested_fix), _meaning_change_heuristic(b.suggested_fix)
    pa, pb = _meaning_preserve_heuristic(a.suggested_fix), _meaning_preserve_heuristic(b.suggested_fix)
    return (ma and pb) or (mb and pa)


_DN_MARKERS = (
    "do not change",
    "must not change",
    "do-not-change",
    "locked term",
    "locked phrase",
    "verbatim",
    "dnr",
)


def _lock_or_dn_change_disputed(a: Issue, b: Issue, *, do_not_change_corpus: str) -> bool:
    """Heuristic: explicit lock/DNC language, or corpus line appears in span with conflicting edit intent."""
    bundle = f"{a.title}\n{a.explanation}\n{a.suggested_fix}\n{b.title}\n{b.explanation}\n{b.suggested_fix}".lower()
    if any(m in bundle for m in _DN_MARKERS):
        return True
    corpus = (do_not_change_corpus or "").strip()
    if not corpus:
        return False
    span_l = (a.span_text or "").lower()
    for line in corpus.splitlines():
        piece = line.strip()
        if len(piece) < 3:
            continue
        pl = piece.lower()
        if pl in span_l or piece in (a.span_text or ""):
            # One side proposes substantive rewrite touching locked substring
            for it in (a, b):
                if len(it.suggested_fix.strip()) > 14 and _meaning_change_heuristic(it.suggested_fix):
                    return True
    return False


def pair_material_discrepancy_reasons(
    a: Issue,
    b: Issue,
    *,
    severity_rank_gap_min: int = 1,
    do_not_change_corpus: str = "",
) -> list[str]:
    """
    Return non-empty list iff this overlapping cross-model pair is a *material* discrepancy
    for convergence purposes.
    """
    if a.block_id != b.block_id or not _spans_overlap(a, b):
        return []
    reasons: list[str] = []
    if _materially_different_fixes(a, b):
        reasons.append(REASON_SAME_SPAN_MATERIALLY_DIFFERENT_FIX)
    if _issue_vs_no_issue(a, b):
        reasons.append(REASON_ISSUE_EXISTS_VS_NO_ISSUE)
    if _severity_disagreement(a, b, min_rank_gap=severity_rank_gap_min):
        reasons.append(REASON_SEVERITY_DISAGREEMENT)
    if _evidence_disagreement(a, b):
        reasons.append(REASON_EVIDENCE_DISAGREEMENT)
    if _meaning_rewrite_conflict(a, b):
        reasons.append(REASON_MEANING_CHANGE_VS_PRESERVING_REWRITE)
    if _keep_vs_change(a, b):
        reasons.append(REASON_KEEP_VS_CHANGE_DISAGREEMENT)
    if _lock_or_dn_change_disputed(a, b, do_not_change_corpus=do_not_change_corpus):
        reasons.append(REASON_LOCK_OR_DN_CHANGE_DISPUTED)

    # Non-material: duplicate nits with near-identical suggested fixes (wording-only drift).
    if (
        a.severity == IssueSeverity.nit
        and b.severity == IssueSeverity.nit
        and _fix_jaccard(a.suggested_fix, b.suggested_fix) >= 0.72
    ):
        reasons = [r for r in reasons if r != REASON_SAME_SPAN_MATERIALLY_DIFFERENT_FIX]

    return reasons


def should_count_pair_toward_material_discrepancy(
    a: Issue,
    b: Issue,
    reasons: list[str],
    *,
    material_severities: set[str] | None,
) -> bool:
    """
    True if this pair should contribute to unresolved_material_discrepancy_count.

    If `material_severities` is set, require at least one issue in that severity set *or*
    a strong material reason (lock / meaning / keep-vs-change / issue-vs-none).
    """
    if not reasons:
        return False
    if material_severities is None:
        return True
    if set(reasons) & STRONG_MATERIAL_REASONS:
        return True
    return a.severity.value in material_severities or b.severity.value in material_severities
