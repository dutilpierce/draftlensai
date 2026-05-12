from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class Plan(str, Enum):
    free = "free"
    pro = "pro"


class OutputMode(str, Enum):
    review = "review"
    fix = "fix"


class ReviewFocus(str, Enum):
    standard = "standard"
    accuracy_heavy = "accuracy-heavy"
    formatting_heavy = "formatting-heavy"
    adversarial = "adversarial"
    voice_preserving = "voice-preserving"


class AccessStartRequest(BaseModel):
    email: EmailStr


class AccessMeResponse(BaseModel):
    user_id: str
    email: EmailStr
    plan: Plan
    access_tier: str
    monthly_free_uses_remaining: int | None = None
    free_proof_remaining_this_month: int | None = None
    usage_count_current_month: int = 0
    fair_use_count_current_month: int | None = None
    current_billing_status: str | None = None
    subscription_current_period_end: datetime | None = None
    pro_docs_used_this_month: int | None = None
    pro_monthly_cap: int | None = None
    supporting_files_allowed: bool = False
    fix_mode_allowed: bool = False
    max_pages: int = 25


class AccessStartResponse(AccessMeResponse):
    ok: bool = True


class ArtifactInfo(BaseModel):
    name: str
    path: str
    media_type: str | None = None
    tier: Literal["primary", "advanced"] = "primary"


class JobPipelineResult(BaseModel):
    total_issues: int = 0
    stats_by_severity: dict[str, int] = Field(default_factory=dict)
    stats_by_category: dict[str, int] = Field(default_factory=dict)
    unresolved_human_evidence: list[dict] = Field(default_factory=list)
    consensus_reached: bool = False
    reviewer_success_count: int = 0
    reviewer_failure_count: int = 0
    reviewer_full_consensus: bool = False
    partial_quorum_used: bool = False
    cycle_count_completed: int = 1
    convergence_status: str | None = None
    convergence_failure_code: str | None = None
    consensus_mode: str | None = None
    intended_reviewer_count: int | None = None
    convergence_successful_reviewer_count: int | None = None
    required_full_consensus_count: int | None = None
    full_three_reviewer_consensus_achieved: bool = False
    partial_consensus_only: bool = False
    pairwise_material_discrepancy_count: int | None = None
    participation_coverage_deficit: int | None = None
    strict_three_reviewer_consensus: bool = True
    fix_alignment_audit_passed: bool | None = None
    fix_alignment_audit_errors: list[str] | None = None
    max_cycles_reached: bool = False
    unresolved_material_issue_count: int = 0
    unresolved_nit_count: int = 0
    unresolved_material_discrepancy_count: int | None = None
    newly_found_material_discrepancy_count: int = 0
    resolved_material_discrepancy_count: int = 0
    stopped_with_remaining_discrepancies: bool = False
    stopped_due_to_max_cycles: bool = False
    stopped_due_to_quorum_loss: bool = False
    stopped_due_to_provider_unavailable: bool = False
    stopped_due_to_fatal_arbiter_failure: bool = False
    pdf_conversion_notes: list[str] = Field(default_factory=list)
    unresolved_cluster_summaries: list[dict] = Field(default_factory=list)
    artifact_pdf_flags: dict[str, bool] = Field(default_factory=dict)
    artifact_tiers: dict[str, str] = Field(default_factory=dict)


class JobSummary(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"]
    output_mode: OutputMode
    review_focus: ReviewFocus
    sensitive_mode: bool
    page_count: int
    error_message: str | None = None
    artifacts: list[ArtifactInfo] = Field(default_factory=list)
    created_at: datetime | None = None
    completed_at: datetime | None = None
    pipeline_result: JobPipelineResult | None = None
    retention_until: datetime | None = None
    data_purged_at: datetime | None = None
    retention_notice: str | None = None
    # Post-review apply-fixes lineage (from persisted `job_config`)
    post_review_fix_seed_job_id: str | None = None
    fix_generation_started_from_review: bool = False
    apply_fixes_honesty_notice: str | None = None
    source_review_consensus_mode: str | None = None
    source_review_full_tri_consensus: bool | None = None
    source_review_partial_consensus_only: bool | None = None


class JobEventPayload(BaseModel):
    stage: str
    message: str
    created_at: datetime | None = None


class BillingCheckoutRequest(BaseModel):
    success_url: str | None = None
    cancel_url: str | None = None


class BillingCheckoutResponse(BaseModel):
    url: str


class BillingPortalRequest(BaseModel):
    return_url: str | None = None


class BillingPortalResponse(BaseModel):
    url: str
