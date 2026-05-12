from __future__ import annotations

from draftlens_api.domain.enums import EntitlementTier
from draftlens_api.domain.models import EntitlementSummary
from draftlens_api.models.schemas import AccessMeResponse, Plan
from draftlens_api.persistence.orm import User


def build_access_me_response(user: User, summary: EntitlementSummary) -> AccessMeResponse:
    plan = Plan.pro if summary.tier == EntitlementTier.pro else Plan.free
    return AccessMeResponse(
        user_id=user.id,
        email=user.email,
        plan=plan,
        access_tier=plan.value,
        monthly_free_uses_remaining=summary.monthly_free_uses_remaining,
        free_proof_remaining_this_month=summary.free_proofs_remaining_month,
        usage_count_current_month=summary.usage_count_current_month,
        fair_use_count_current_month=summary.fair_use_count_current_month,
        current_billing_status=summary.current_billing_status,
        subscription_current_period_end=summary.subscription_current_period_end,
        pro_docs_used_this_month=summary.pro_docs_used_month,
        pro_monthly_cap=summary.pro_fair_use_cap,
        supporting_files_allowed=summary.supporting_files_allowed,
        fix_mode_allowed=summary.fix_mode_allowed,
        max_pages=summary.max_pages,
    )
