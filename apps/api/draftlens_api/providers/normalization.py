from __future__ import annotations

import uuid
from typing import Any

from draftlens_api.domain.enums import AccuracyPosture, IssueCategory, IssueSeverity, IssueStatus
from draftlens_api.domain.models import AgentFinding, Issue


def _coerce_severity(value: Any) -> IssueSeverity:
    try:
        return IssueSeverity(str(value).lower())
    except ValueError:
        return IssueSeverity.minor


def _coerce_category(value: Any) -> IssueCategory:
    try:
        return IssueCategory(str(value).lower())
    except ValueError:
        return IssueCategory.clarity


def _coerce_accuracy_posture(value: Any) -> AccuracyPosture | None:
    if value is None or value == "":
        return None
    try:
        return AccuracyPosture(str(value).lower())
    except ValueError:
        return None


def issues_from_payload(raw: Any, *, default_block_id: str, source_agent: str) -> list[Issue]:
    if not isinstance(raw, list):
        return []
    out: list[Issue] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        block_id = str(item.get("block_id") or default_block_id)
        span = str(item.get("span_text") or item.get("span") or "")
        try:
            cs = int(item.get("char_start", 0))
            ce = int(item.get("char_end", max(len(span), 1)))
        except (TypeError, ValueError):
            cs, ce = 0, max(len(span), 1)
        st = item.get("status")
        try:
            istatus = IssueStatus(str(st)) if st else IssueStatus.open
        except ValueError:
            istatus = IssueStatus.open
        issue = Issue(
            issue_id=str(item.get("issue_id") or uuid.uuid4()),
            lineage_id=str(item.get("lineage_id")) if item.get("lineage_id") else None,
            block_id=block_id,
            span_text=span,
            char_start=cs,
            char_end=ce,
            category=_coerce_category(item.get("category")),
            severity=_coerce_severity(item.get("severity")),
            title=str(item.get("title") or "Finding"),
            explanation=str(item.get("explanation") or item.get("details") or ""),
            evidence_basis=str(item.get("evidence_basis") or ""),
            confidence=float(item.get("confidence", 0.7)),
            suggested_fix=str(item.get("suggested_fix") or ""),
            preserve_voice_notes=str(item.get("preserve_voice_notes") or ""),
            source_agents=[str(x) for x in item.get("source_agents", [])] or [source_agent],
            status=istatus,
            accuracy_posture=_coerce_accuracy_posture(item.get("accuracy_posture")),
        )
        out.append(issue)
    return out


def agent_finding_from_payload(data: dict[str, Any], *, role: str) -> AgentFinding:
    issues_raw = data.get("issues") or data.get("issue_candidates") or []
    default_block = str(data.get("default_block_id") or "doc-root")
    issues = issues_from_payload(issues_raw, default_block_id=default_block, source_agent=role)
    return AgentFinding(
        agent_role=role,
        summary=str(data.get("summary") or data.get("executive_summary") or "").strip() or "No summary returned.",
        risks=[str(x) for x in (data.get("risks") or []) if str(x).strip()],
        questions_for_peers=[str(x) for x in (data.get("questions_for_peers") or data.get("questions") or []) if str(x).strip()],
        issue_candidates=issues,
        unavailable=bool(data.get("unavailable", False)),
        error_code=data.get("error_code"),
    )
