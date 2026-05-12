from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from draftlens_api.config import Settings
from draftlens_api.domain.enums import EntitlementTier
from draftlens_api.domain.models import EntitlementSummary
from draftlens_api.persistence.orm import Entitlement, Subscription, User

_PAID_SUBSCRIPTION_STATUSES = ("active", "trialing", "past_due")


@dataclass
class EntitlementService:
    db: Session
    settings: Settings

    def _active_subscription(self, user_id: str) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status.in_(_PAID_SUBSCRIPTION_STATUSES))
            .order_by(Subscription.updated_at.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def tier_for_user(self, user: User) -> EntitlementTier:
        sub = self._active_subscription(user.id)
        if sub:
            return EntitlementTier.pro
        if user.plan == "pro":
            return EntitlementTier.pro
        ent = (
            self.db.execute(
                select(Entitlement)
                .where(Entitlement.user_id == user.id)
                .order_by(Entitlement.updated_at.desc())
            )
            .scalars()
            .first()
        )
        if ent and ent.tier == EntitlementTier.pro.value:
            return EntitlementTier.pro
        return EntitlementTier.free

    def _completed_jobs_this_month(self, user_id: str) -> int:
        from draftlens_api.services.usage_quota import UsageQuotaService

        return UsageQuotaService(self.db).completed_jobs_this_month(user_id)

    def summary(self, user: User) -> EntitlementSummary:
        tier = self.tier_for_user(user)
        completed = self._completed_jobs_this_month(user.id)

        if tier == EntitlementTier.free:
            remaining = max(0, self.settings.free_monthly_proofs - completed)
            return EntitlementSummary(
                tier=tier,
                free_proofs_remaining_month=remaining,
                monthly_free_uses_remaining=remaining,
                usage_count_current_month=completed,
                fair_use_count_current_month=None,
                current_billing_status=user.billing_status,
                subscription_current_period_end=user.subscription_current_period_end,
                last_reset_at=None,
                supporting_files_allowed=False,
                fix_mode_allowed=False,
                max_pages=self.settings.free_max_pages,
                pro_docs_used_month=None,
                pro_fair_use_cap=None,
            )
        return EntitlementSummary(
            tier=tier,
            free_proofs_remaining_month=None,
            monthly_free_uses_remaining=None,
            usage_count_current_month=completed,
            fair_use_count_current_month=completed,
            current_billing_status=user.billing_status,
            subscription_current_period_end=user.subscription_current_period_end,
            last_reset_at=None,
            supporting_files_allowed=True,
            fix_mode_allowed=True,
            max_pages=self.settings.pro_max_pages,
            pro_docs_used_month=completed,
            pro_fair_use_cap=self.settings.pro_fair_use_docs_per_month,
        )

    def assert_job_allowed(
        self,
        *,
        user: User,
        output_mode: str,
        supporting_count: int,
        pages: int | None,
    ) -> None:
        tier = self.tier_for_user(user)
        summary = self.summary(user)
        if tier == EntitlementTier.free:
            if output_mode == "fix":
                raise HTTPException(status_code=403, detail="fix_mode_requires_pro")
            if supporting_count > 0:
                raise HTTPException(status_code=403, detail="supporting_files_require_pro")
            if (
                summary.free_proofs_remaining_month is not None
                and summary.free_proofs_remaining_month <= 0
            ):
                raise HTTPException(status_code=403, detail="free_monthly_limit_reached")
        else:
            if summary.pro_docs_used_month is not None and summary.pro_fair_use_cap is not None:
                if summary.pro_docs_used_month >= summary.pro_fair_use_cap:
                    raise HTTPException(status_code=403, detail="pro_monthly_cap_reached")
        if pages is not None and pages > summary.max_pages:
            raise HTTPException(status_code=400, detail="document_page_limit_exceeded")
