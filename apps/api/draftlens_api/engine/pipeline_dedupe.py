from __future__ import annotations

import re
from typing import Iterable

from draftlens_api.domain.enums import IssueSeverity
from draftlens_api.domain.models import Issue


_SEV_ORDER = {
    IssueSeverity.nit: 0,
    IssueSeverity.minor: 1,
    IssueSeverity.major: 2,
    IssueSeverity.critical: 3,
}


def _sev_rank(sev: IssueSeverity) -> int:
    return _SEV_ORDER.get(sev, 1)


def _merge_severity(a: IssueSeverity, b: IssueSeverity) -> IssueSeverity:
    return a if _sev_rank(a) >= _sev_rank(b) else b


def _token_jaccard(a: str, b: str) -> float:
    ta = {x for x in re.findall(r"[a-z0-9]{3,}", a.lower())}
    tb = {x for x in re.findall(r"[a-z0-9]{3,}", b.lower())}
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return float(inter) / float(union) if union else 0.0


def _same_category_or_semantic(a: Issue, b: Issue) -> bool:
    if a.category == b.category:
        return True
    blob_a = f"{a.title}\n{a.explanation}"
    blob_b = f"{b.title}\n{b.explanation}"
    return _token_jaccard(blob_a, blob_b) >= 0.72


def _spans_overlap(a: Issue, b: Issue) -> bool:
    if a.block_id != b.block_id:
        return False
    return not (a.char_end < b.char_start or b.char_end < a.char_start)


def dedupe_findings(issues: Iterable[Issue]) -> list[Issue]:
    """
    Deterministic dedupe:
    - same block_id
    - overlapping span (char_start/char_end)
    - same category OR semantically equivalent issue text
    - retain highest severity
    - merge source_agents (unique, stable order)
    """
    items = list(issues)
    if not items:
        return []

    groups: list[list[Issue]] = []
    for it in sorted(items, key=lambda x: (x.block_id, x.char_start, x.char_end, x.issue_id)):
        placed = False
        for g in groups:
            rep = g[0]
            if rep.block_id != it.block_id:
                continue
            if not _spans_overlap(rep, it):
                continue
            if not _same_category_or_semantic(rep, it):
                continue
            g.append(it)
            placed = True
            break
        if not placed:
            groups.append([it])

    merged: list[Issue] = []
    for g in groups:
        base = g[0]
        sev = base.severity
        agents: list[str] = []
        for it in g:
            sev = _merge_severity(sev, it.severity)
            for ag in it.source_agents:
                if ag not in agents:
                    agents.append(ag)
        # Prefer the longest explanation as canonical detail carrier
        rep_issue = max(g, key=lambda x: len(x.explanation or ""))
        lineage = rep_issue.lineage_id or rep_issue.issue_id
        merged.append(
            Issue(
                issue_id=rep_issue.issue_id,
                lineage_id=lineage,
                block_id=rep_issue.block_id,
                span_text=rep_issue.span_text,
                char_start=min(x.char_start for x in g),
                char_end=max(x.char_end for x in g),
                category=rep_issue.category,
                severity=sev,
                title=rep_issue.title,
                explanation=rep_issue.explanation,
                evidence_basis=rep_issue.evidence_basis,
                confidence=max(x.confidence for x in g),
                suggested_fix=rep_issue.suggested_fix,
                preserve_voice_notes=rep_issue.preserve_voice_notes,
                source_agents=agents or rep_issue.source_agents,
                status=rep_issue.status,
                accuracy_posture=_merge_accuracy_posture([x.accuracy_posture for x in g]),
            )
        )
    merged.sort(key=lambda x: (x.block_id, x.char_start, _sev_rank(x.severity)), reverse=True)
    return merged


def _merge_accuracy_posture(values: list):
    from draftlens_api.domain.enums import AccuracyPosture

    order = [
        AccuracyPosture.false,
        AccuracyPosture.internally_inconsistent,
        AccuracyPosture.unsupported,
        AccuracyPosture.unverified,
    ]
    best = None
    best_idx = -1
    for v in values:
        if v is None:
            continue
        try:
            idx = order.index(v)
        except ValueError:
            idx = 1
        if idx > best_idx:
            best_idx = idx
            best = v
    return best
