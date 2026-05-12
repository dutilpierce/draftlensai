from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

from draftlens_api.domain.enums import (
    AccuracyPosture,
    DocumentType,
    EntitlementTier,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    SubscriptionStatus,
    UsageEventType,
)


# --- Job & session ---


class IterativeReviewConfig(BaseModel):
    """Bounded convergence / re-review controls (deterministic, inspectable)."""

    enabled: bool = True
    max_cycles_review_mode: int = Field(default=5, ge=1, le=8)
    max_cycles_fix_mode: int = Field(default=6, ge=1, le=10)
    stop_when_no_new_material_issues: bool = True
    material_issue_severities: list[str] = Field(
        default_factory=lambda: ["critical", "major", "minor"],
    )
    ignore_nits_for_fix_completion: bool = True
    rerun_neighbor_blocks: bool = True
    neighbor_window: int = Field(default=1, ge=0, le=3)
    recheck_changed_blocks_only_after_cycle_1: bool = True
    severity_rank_gap_material_min: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Minimum absolute severity-rank gap (nit=0..critical=3) for severity_disagreement pairs.",
    )
    strict_three_reviewer_consensus: bool = Field(
        default=True,
        description="When true, declaring full tri-panel success uses PARTIAL_CONSENSUS unless all three "
        "configured reviewers produced structured success on the counted pass and pairwise material clusters are zero.",
    )


class FixModeCompletionConfig(BaseModel):
    """Thresholds for declaring Fix Mode complete (beyond pairwise discrepancy clusters)."""

    require_zero_material_discrepancies: bool = True
    allow_remaining_nits: bool = True
    require_alignment_audit_pass: bool = True
    require_locked_term_integrity: bool = True
    require_no_open_critical: bool = True
    require_no_open_major: bool = True
    require_no_open_minor: bool = False


class ReviewJobConfig(BaseModel):
    output_mode: Literal["review", "fix"] = "review"
    review_focus: str = "standard"
    document_type: DocumentType = DocumentType.general
    max_debate_rounds: int = Field(default=3, ge=1, le=5)
    context_text: str | None = None
    do_not_change: str | None = None
    sensitive_mode: bool = False
    main_original_filename: str
    main_mime: str = "application/octet-stream"
    # Large-document-safe review (set from CentralPolicyService at job creation)
    max_chars_per_block: int = Field(default=2400, ge=400, le=12_000)
    max_blocks_for_review: int | None = Field(default=None, ge=1, le=50_000)
    max_block_send_chars: int = Field(default=3200, ge=400, le=20_000)
    iterative_review: IterativeReviewConfig = Field(default_factory=IterativeReviewConfig)
    fix_mode_completion: FixModeCompletionConfig = Field(default_factory=FixModeCompletionConfig)
    # --- Post-review apply-fixes (fix job bootstrapped from a completed review job) ---
    post_review_fix_seed_job_id: str | None = Field(
        default=None,
        description="When set with output_mode=fix, pipeline hydrates from that job's fix_seed_snapshot.json.",
    )
    fix_generation_started_from_review: bool = Field(
        default=False,
        description="True when this fix job was created via Apply fixes after a review.",
    )
    source_review_consensus_mode: str | None = Field(
        default=None,
        description="Snapshot of source review convergence_status for honesty labeling.",
    )
    source_review_full_tri_consensus: bool | None = Field(
        default=None,
        description="Whether the source review achieved full three-reviewer consensus.",
    )
    source_review_partial_consensus_only: bool | None = Field(
        default=None,
        description="Whether the source review ended with partial_consensus_only.",
    )
    apply_fixes_honesty_notice: str | None = Field(
        default=None,
        description="User-visible caveat when generating fixes from partial-review source material.",
    )


class UserSession(BaseModel):
    session_id: str
    user_id: str
    email: EmailStr
    expires_at: datetime
    created_at: datetime | None = None


class UserRecord(BaseModel):
    user_id: str
    email: EmailStr
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EntitlementSummary(BaseModel):
    tier: EntitlementTier
    free_proofs_remaining_month: int | None = None
    monthly_free_uses_remaining: int | None = None
    usage_count_current_month: int = 0
    fair_use_count_current_month: int | None = None
    current_billing_status: str | None = None
    subscription_current_period_end: datetime | None = None
    last_reset_at: datetime | None = None
    pro_docs_used_month: int | None = None
    pro_fair_use_cap: int | None = None
    supporting_files_allowed: bool = False
    fix_mode_allowed: bool = False
    max_pages: int = 25


class BillingState(BaseModel):
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    subscription_status: SubscriptionStatus | None = None
    is_pro: bool = False


class SubscriptionRecord(BaseModel):
    subscription_id: str
    user_id: str
    stripe_subscription_id: str
    status: SubscriptionStatus
    plan_code: str = "pro_monthly"
    current_period_end: datetime | None = None
    raw: dict | None = None


class UsageEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str | None = None
    event_type: UsageEventType
    year_month: str  # YYYY-MM
    quantity: int = 1
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class SupportingFileRecord(BaseModel):
    file_id: str
    job_id: str
    original_name: str
    storage_path: str
    mime: str
    byte_size: int
    extracted_cache_path: str | None = None
    page_estimate: int | None = None


class EvidenceSource(BaseModel):
    source_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    excerpt: str
    kind: Literal["supporting", "context", "main_snippet"] = "supporting"


class MainDocumentRecord(BaseModel):
    job_id: str
    original_filename: str
    storage_path: str
    mime: str
    page_estimate: int
    full_text: str
    sha256: str | None = None


class DocumentBlock(BaseModel):
    block_id: str
    char_start: int
    char_end: int
    text: str


class Issue(BaseModel):
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lineage_id: str | None = None
    parent_issue_id: str | None = None
    cycle_number: int = Field(default=1, ge=1)
    discovered_in_cycle: int | None = None
    resolved_in_cycle: int | None = None
    superseded_by_issue_id: str | None = None
    block_id: str
    span_text: str
    char_start: int
    char_end: int
    category: IssueCategory
    severity: IssueSeverity
    title: str
    explanation: str
    evidence_basis: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    suggested_fix: str = ""
    preserve_voice_notes: str = ""
    source_agents: list[str] = Field(default_factory=list)
    status: IssueStatus = IssueStatus.open
    accuracy_posture: AccuracyPosture | None = None

    @model_validator(mode="after")
    def _ensure_lineage_id(self) -> Issue:
        if not self.lineage_id:
            self.lineage_id = self.issue_id
        return self


class ProposedEdit(BaseModel):
    edit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    block_id: str
    before: str
    after: str
    rationale: str
    source_agents: list[str] = Field(default_factory=list)


class AgentFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_role: str
    summary: str
    risks: list[str] = Field(default_factory=list)
    questions_for_peers: list[str] = Field(default_factory=list)
    issue_candidates: list[Issue] = Field(default_factory=list)
    unavailable: bool = False
    error_code: str | None = None


class ConflictSet(BaseModel):
    conflict_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    positions: dict[str, str] = Field(default_factory=dict)  # agent_role -> stance
    unresolved: bool = True


class ArbitrationDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    executive_summary: str
    resolved_conflicts: list[ConflictSet] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    proposed_edits: list[ProposedEdit] = Field(default_factory=list)
    corrected_document_text: str | None = None
    redline_html_fragment: str | None = None


class DisclaimerBundle(BaseModel):
    """Short, professional copy for UI nudges and artifact footers (no alarmist language)."""

    general: str = "AI-assisted review. Please verify important facts and final wording."
    third_party_models: str = "Suggested edits may require human verification."
    accuracy_context_note: str | None = None
    retention: str | None = "Changes are generated automatically and should be reviewed before use."
    no_model_training: str | None = None
    files_scheduled_for_deletion: str | None = None
    sensitive_mode: str | None = None
    ui_run_area_note: str = "AI-assisted review. Please verify important facts and final wording."
    ui_results_area_note: str = (
        "Designed to help review documents, not replace final human judgment. "
        "Suggested edits may require human verification."
    )
    markdown_review_footer: str = ""
    markdown_fix_footer: str = ""


class FinalLedger(BaseModel):
    ledger_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    debate_digest: str
    participating_agents: list[str] = Field(default_factory=list)
    unavailable_agents: list[str] = Field(default_factory=list)
    quorum_met: bool = False
    arbitration: ArbitrationDecision | None = None
    disclaimers: DisclaimerBundle = Field(default_factory=DisclaimerBundle)


class RenderPlan(BaseModel):
    """Declares which artifact files to emit for a job."""

    emit_reviewed_docx: bool = True
    emit_redline_html: bool = True
    emit_issues_json: bool = True
    emit_issues_md: bool = True
    emit_review_summary_md: bool = True
    emit_corrected_docx: bool = False
    emit_change_log_md: bool = False
    emit_changes_json: bool = False


class JobStatusEvent(BaseModel):
    stage: str
    message: str
    detail: dict = Field(default_factory=dict)
    ts: datetime | None = None


class ArtifactManifest(BaseModel):
    job_id: str
    artifacts: list["ArtifactRecord"] = Field(default_factory=list)


class ArtifactRecord(BaseModel):
    name: str
    path: str
    media_type: str | None = None
    byte_size: int | None = None


class PipelineGraphOutput(BaseModel):
    """Structured aggregate emitted by the LangGraph review pipeline."""

    job_id: str
    final_ledger: FinalLedger
    render_plan: RenderPlan
    final_issues: list[Issue]
    accepted_edits: list[ProposedEdit]
    stats_by_severity: dict[str, int]
    stats_by_category: dict[str, int]
    unresolved_human_evidence: list[Issue]
    disclaimer_bundle: DisclaimerBundle
    artifact_manifest: ArtifactManifest
    debate_digest: str
    stage_trace: list[str] = Field(default_factory=list)
