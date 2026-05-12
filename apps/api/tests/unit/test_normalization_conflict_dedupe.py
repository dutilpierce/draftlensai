from __future__ import annotations

import pytest
from pydantic import ValidationError

from draftlens_api.domain.enums import IssueCategory, IssueSeverity
from draftlens_api.domain.models import Issue
from draftlens_api.engine.debate_coordinator import DebateCoordinator
from draftlens_api.engine.pipeline_conflicts import detect_conflicts
from draftlens_api.engine.pipeline_dedupe import dedupe_findings
from draftlens_api.providers.normalization import agent_finding_from_payload, issues_from_payload
from draftlens_api.prompts.schemas import validate_reviewer_payload


def test_issues_from_payload_coercions_and_aliases() -> None:
    raw = [
        {
            "span": "hello",
            "category": "INVALID_SHOULD_COERCE",
            "severity": "bogus",
            "title": "T",
            "details": "from details",
        }
    ]
    issues = issues_from_payload(raw, default_block_id="b1", source_agent="gpt")
    assert len(issues) == 1
    assert issues[0].block_id == "b1"
    assert issues[0].span_text == "hello"
    assert issues[0].category == IssueCategory.clarity
    assert issues[0].severity == IssueSeverity.minor
    assert "from details" in issues[0].explanation


def test_agent_finding_from_payload_executive_summary_alias() -> None:
    data = {
        "executive_summary": "Exec",
        "issues": [],
        "risks": ["r1"],
    }
    f = agent_finding_from_payload(data, role="gpt_reviewer")
    assert f.summary == "Exec"


def test_validate_reviewer_payload_strict_rejects_bad_issue_category() -> None:
    bad = {"summary": "ok", "risks": [], "questions_for_peers": [], "issues": [{"category": "nope"}]}
    with pytest.raises(ValidationError):
        validate_reviewer_payload(bad)


def test_dedupe_findings_merges_overlap_and_severity() -> None:
    a = Issue(
        issue_id="a",
        block_id="b1",
        span_text="same",
        char_start=10,
        char_end=20,
        category=IssueCategory.grammar,
        severity=IssueSeverity.minor,
        title="t1",
        explanation="short",
        source_agents=["claude"],
    )
    b = Issue(
        issue_id="b",
        block_id="b1",
        span_text="same",
        char_start=12,
        char_end=22,
        category=IssueCategory.grammar,
        severity=IssueSeverity.major,
        title="t1",
        explanation="longer explanation wins length heuristic",
        source_agents=["gpt"],
    )
    out = dedupe_findings([a, b])
    assert len(out) == 1
    assert out[0].severity == IssueSeverity.major
    assert set(out[0].source_agents) == {"claude", "gpt"}


def test_detect_conflicts_materially_different_fixes() -> None:
    a = Issue(
        issue_id="1",
        block_id="b",
        span_text="x",
        char_start=0,
        char_end=5,
        category=IssueCategory.clarity,
        severity=IssueSeverity.minor,
        title="t",
        explanation="e",
        suggested_fix="replace the entire paragraph with a new thesis statement",
    )
    b = Issue(
        issue_id="2",
        block_id="b",
        span_text="x",
        char_start=1,
        char_end=4,
        category=IssueCategory.clarity,
        severity=IssueSeverity.minor,
        title="t2",
        explanation="e2",
        suggested_fix="add a comma after the introductory clause for readability",
    )
    clusters = detect_conflicts([a, b])
    assert clusters
    assert any("same_span_materially_different_fix" in c.reasons for c in clusters)


def test_debate_coordinator_digest_and_conflict() -> None:
    from draftlens_api.domain.models import AgentFinding

    f1 = AgentFinding(
        agent_role="A",
        summary="S1",
        risks=["r"],
        questions_for_peers=["q"],
        issue_candidates=[
            Issue(
                issue_id="1",
                block_id="b",
                span_text="overlap text here",
                char_start=0,
                char_end=10,
                category=IssueCategory.logic,
                severity=IssueSeverity.major,
                title="t",
                explanation="e",
            )
        ],
    )
    f2 = AgentFinding(
        agent_role="B",
        summary="S2",
        issue_candidates=[
            Issue(
                issue_id="2",
                block_id="b",
                span_text="overlap text here",
                char_start=0,
                char_end=10,
                category=IssueCategory.logic,
                severity=IssueSeverity.minor,
                title="t",
                explanation="e",
            )
        ],
    )
    dc = DebateCoordinator()
    digest = dc.build_digest([f1, f2])
    assert "S1" in digest and "S2" in digest
    conflicts = dc.build_conflicts([f1, f2])
    assert conflicts
    assert conflicts[0].unresolved
