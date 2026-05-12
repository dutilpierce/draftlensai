"""Compare ledgers across convergence cycles (material new-issue detection)."""

from __future__ import annotations

import re
from collections import defaultdict

from typing import TYPE_CHECKING

from draftlens_api.domain.enums import IssueSeverity, IssueStatus
from draftlens_api.domain.models import Issue

if TYPE_CHECKING:
    from draftlens_api.domain.models import ProposedEdit

_SEV_ORDER = {"critical": 4, "major": 3, "minor": 2, "nit": 1}


def _norm_span(s: str) -> str:
    t = re.sub(r"\s+", " ", (s or "").strip().lower())
    return t[:160]


def _fingerprint(it: Issue) -> str:
    return f"{it.block_id}|{_norm_span(it.span_text)}|{it.category.value}"


def _is_material(sev: str, material: set[str]) -> bool:
    return sev in material


def count_new_material_issues(
    prior: list[Issue],
    current: list[Issue],
    *,
    material_severities: set[str],
) -> int:
    """
    Heuristic count of materially new findings (not wording-only duplicates).
    """
    prior_by_fp: dict[str, Issue] = {}
    prior_max_sev: dict[str, int] = defaultdict(int)
    for it in prior:
        if not _is_material(it.severity.value, material_severities):
            continue
        fp = _fingerprint(it)
        prior_by_fp[fp] = it
        prior_max_sev[fp] = max(prior_max_sev[fp], _SEV_ORDER.get(it.severity.value, 0))

    new_count = 0
    seen_new_fps: set[str] = set()
    for it in current:
        if it.status in {IssueStatus.rejected, IssueStatus.deferred}:
            continue
        if not _is_material(it.severity.value, material_severities):
            continue
        fp = _fingerprint(it)
        cur_ord = _SEV_ORDER.get(it.severity.value, 0)
        if fp not in prior_by_fp:
            if fp not in seen_new_fps:
                seen_new_fps.add(fp)
                new_count += 1
            continue
        if cur_ord > prior_max_sev.get(fp, 0):
            new_count += 1
    return new_count


def unresolved_material_and_nit(
    issues: list[Issue],
    *,
    material_severities: set[str],
) -> tuple[int, int]:
    """Open issues: (material_count, nit_count)."""
    mat = 0
    nits = 0
    for it in issues:
        if it.status != IssueStatus.open:
            continue
        if it.severity == IssueSeverity.nit:
            nits += 1
        elif it.severity.value in material_severities:
            mat += 1
    return mat, nits


def fix_mode_meets_clean_threshold(
    issues: list[Issue],
    *,
    material_severities: set[str],
    ignore_nits: bool,
) -> bool:
    mat, nits = unresolved_material_and_nit(issues, material_severities=material_severities)
    if mat == 0 and nits == 0:
        return True
    if mat == 0 and ignore_nits:
        return True
    return False


def detect_text_thrash(history: list[str]) -> bool:
    """True if corrected full text alternates A -> B -> A (simple oscillation guard)."""
    h = [x for x in history if x]
    if len(h) < 3:
        return False
    return h[-1] == h[-3]


def _edit_cycle_signature(edits: list["ProposedEdit"]) -> tuple[str, ...]:
    """Stable fingerprint for a cycle's proposed edit set (for oscillation detection)."""
    parts: list[str] = []
    for e in edits:
        b = getattr(e, "before", "") or ""
        a = getattr(e, "after", "") or ""
        eid = getattr(e, "edit_id", "") or ""
        parts.append(f"{eid}|{b[:120]!r}|{a[:120]!r}")
    parts.sort()
    return tuple(parts)


def detect_edit_signature_thrash(signatures: list[tuple[str, ...]]) -> bool:
    """True if the arbiter's proposed-edit fingerprint repeats A -> B -> A across cycles."""
    if len(signatures) < 3:
        return False
    return signatures[-1] == signatures[-3]


def fix_mode_open_issues_pass_completion(
    issues: list[Issue],
    *,
    material_severities: set[str],
    allow_remaining_nits: bool,
    require_no_open_critical: bool,
    require_no_open_major: bool,
    require_no_open_minor: bool,
) -> tuple[bool, str | None]:
    """
    Returns (passes, reason_if_failed).

    When require_no_open_minor/major/critical, any *open* issue at that severity
    fails even if it is not part of a cross-model discrepancy cluster.
    """
    for it in issues:
        if it.status != IssueStatus.open:
            continue
        if it.severity == IssueSeverity.nit and not allow_remaining_nits:
            return False, "open_nit_when_nits_disallowed"
        if it.severity == IssueSeverity.nit:
            continue
        if it.severity == IssueSeverity.critical and require_no_open_critical:
            return False, "open_critical_issue"
        if it.severity == IssueSeverity.major and require_no_open_major:
            return False, "open_major_issue"
        if it.severity == IssueSeverity.minor and require_no_open_minor:
            return False, "open_minor_issue"
        if it.severity.value in material_severities:
            # Material severities already covered by major/minor/critical flags;
            # if none of the strict flags matched but severity is in material set, use major/minor defaults.
            pass
    return True, None
