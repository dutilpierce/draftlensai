"""
Deterministic final alignment audit for Fix Mode.

Compares the fully corrected plaintext candidate against the finalized arbiter
ledger (proposed edits + open issues) and do-not-change constraints.
"""

from __future__ import annotations

import re

from draftlens_api.domain.enums import IssueSeverity, IssueStatus
from draftlens_api.domain.models import Issue, ProposedEdit


def _locked_phrases(do_not_change: str | None) -> list[str]:
    if not (do_not_change or "").strip():
        return []
    parts = re.split(r"[\n,;]+", do_not_change)
    return [p.strip() for p in parts if len(p.strip()) >= 2]


def run_final_fix_alignment_audit(
    *,
    final_document_text: str,
    baseline_document_text: str,
    proposed_edits: list[ProposedEdit],
    issues: list[Issue],
    do_not_change: str | None,
    material_severities: set[str],
    require_locked_term_integrity: bool,
) -> tuple[bool, list[str]]:
    """
    Returns (passed, human-readable failure reasons).

    Heuristics are intentionally conservative: false positives are avoided where
    possible, but any clear inconsistency fails the audit.
    """
    errors: list[str] = []
    doc = final_document_text or ""
    base = baseline_document_text or ""

    for ed in proposed_edits:
        b = (ed.before or "").strip()
        a = (ed.after or "").strip()
        if not b and not a:
            continue
        if b:
            if b in doc:
                errors.append(f"proposed_edit_unapplied:{ed.edit_id}:before_still_present")
            elif a.strip() and a not in doc:
                errors.append(f"proposed_edit_missing_after:{ed.edit_id}")
        elif a and a not in doc:
            errors.append(f"proposed_insertion_missing:{ed.edit_id}")

    for it in issues:
        if it.status != IssueStatus.open:
            continue
        if it.severity == IssueSeverity.nit:
            continue
        if it.severity.value in material_severities:
            errors.append(f"open_material_issue:{it.issue_id}:{it.severity.value}")

    if require_locked_term_integrity:
        for phrase in _locked_phrases(do_not_change):
            if phrase in base and phrase not in doc:
                errors.append(f"locked_term_removed:{phrase[:80]}")

    return (len(errors) == 0, errors)
