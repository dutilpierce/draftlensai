from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

IssueCategoryLiteral = Literal[
    "accuracy",
    "logic",
    "consistency",
    "grammar",
    "clarity",
    "formatting",
    "citation",
    "tone",
    "risk",
]
IssueSeverityLiteral = Literal["critical", "major", "minor", "nit"]
IssueStatusLiteral = Literal["open", "accepted", "rejected", "deferred", "resolved"]
AccuracyPostureLiteral = Literal["false", "unsupported", "unverified", "internally_inconsistent"]
ArbiterVerdictLiteral = Literal["accept_a", "accept_b", "merge", "reject_both", "needs_human_evidence"]
DebateStanceLiteral = Literal["defend", "revise", "withdraw"]


class IssueFindingPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    issue_id: str | None = None
    lineage_id: str | None = None
    block_id: str
    span_text: str = ""
    char_start: int = 0
    char_end: int = 0
    category: IssueCategoryLiteral
    severity: IssueSeverityLiteral
    title: str
    explanation: str = ""
    evidence_basis: str = ""
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    suggested_fix: str = ""
    preserve_voice_notes: str = ""
    source_agents: list[str] = Field(default_factory=list)
    status: IssueStatusLiteral = "open"
    accuracy_posture: AccuracyPostureLiteral | None = None


class ReviewerLLMResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str
    risks: list[str] = Field(default_factory=list)
    questions_for_peers: list[str] = Field(default_factory=list)
    issues: list[IssueFindingPayload] = Field(default_factory=list)


class DebateVotePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dispute_id: str = ""
    issue_id: str = ""
    stance: DebateStanceLiteral
    rationale_summary: str = ""
    revised_issue: dict[str, Any] | None = None


class DebateRound2Response(BaseModel):
    model_config = ConfigDict(extra="ignore")

    votes: list[DebateVotePayload] = Field(default_factory=list)


class ArbiterVerdictItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dispute_id: str = ""
    verdict: ArbiterVerdictLiteral
    notes: str = ""
    merged_issue: dict[str, Any] | None = None


class ProposedEditPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    edit_id: str | None = None
    block_id: str
    before: str = ""
    after: str = ""
    rationale: str = ""
    source_agents: list[str] = Field(default_factory=list)


class ResolvedConflictPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    conflict_id: str | None = None
    topic: str = ""
    positions: dict[str, str] = Field(default_factory=dict)
    unresolved: bool = True


class ArbiterLLMResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    executive_summary: str
    verdicts: list[ArbiterVerdictItem] = Field(default_factory=list)
    issues: list[IssueFindingPayload] = Field(default_factory=list)
    proposed_edits: list[ProposedEditPayload] = Field(default_factory=list)
    resolved_conflicts: list[ResolvedConflictPayload] = Field(default_factory=list)
    redline_html_fragment: str | None = None
    corrected_document_text: str | None = None


class SupervisorLedgerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    merged_issues: list[IssueFindingPayload]
    conflict_report: list[dict[str, Any]]
    stats_by_severity: dict[str, int]
    stats_by_category: dict[str, int]
    human_evidence_queue: list[IssueFindingPayload] = Field(default_factory=list)
    pipeline_notes: list[str] = Field(default_factory=list)

    @field_validator("stats_by_severity")
    @classmethod
    def _non_negative_counts(cls, v: dict[str, int]) -> dict[str, int]:
        for _k, n in v.items():
            if n < 0:
                raise ValueError("negative_stat")
        return v


def validate_reviewer_payload(data: dict[str, Any]) -> ReviewerLLMResponse:
    return ReviewerLLMResponse.model_validate(data)


def validate_arbiter_payload(data: dict[str, Any]) -> ArbiterLLMResponse:
    return ArbiterLLMResponse.model_validate(data)


def validate_supervisor_payload(data: dict[str, Any]) -> SupervisorLedgerResponse:
    return SupervisorLedgerResponse.model_validate(data)


def validate_debate_round2_payload(data: dict[str, Any]) -> DebateRound2Response:
    return DebateRound2Response.model_validate(data)
