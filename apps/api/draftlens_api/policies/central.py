from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from draftlens_api.config import Settings
from draftlens_api.domain.enums import EntitlementTier


@dataclass(frozen=True)
class DocumentReviewLimits:
    """Tier-derived caps for large-document-safe review (chunking + model fan-out)."""

    max_chars_per_block: int
    max_blocks_for_review: int | None  # None = no cap
    max_block_send_chars: int


@dataclass(frozen=True)
class TrustCopy:
    """Quiet, non-alarmist copy for UI and artifact footers."""

    files_scheduled_for_deletion: str = "Files are processed for review and scheduled for deletion."
    sensitive_shorter_retention: str = "Sensitive mode uses shorter retention."
    no_model_training: str = "Your files are used only to run this review; they are not used to train models."


@dataclass
class CentralPolicyService:
    """
    Central place for retention scheduling, document limits, page caps, and trust copy.
    Quota enforcement remains in EntitlementService; this class supplies numeric limits and schedules.
    """

    settings: Settings

    def retention_hours(self, *, sensitive_mode: bool) -> int:
        return (
            int(self.settings.data_retention_hours_sensitive)
            if sensitive_mode
            else int(self.settings.data_retention_hours_default)
        )

    def retention_until(self, *, sensitive_mode: bool, now: datetime | None = None) -> datetime:
        now = now or datetime.now(timezone.utc)
        return now + timedelta(hours=self.retention_hours(sensitive_mode=sensitive_mode))

    def document_review_limits(self, tier: EntitlementTier) -> DocumentReviewLimits:
        if tier == EntitlementTier.free:
            cap = int(self.settings.free_max_review_blocks)
            return DocumentReviewLimits(
                max_chars_per_block=2200,
                max_blocks_for_review=cap if cap > 0 else 48,
                max_block_send_chars=3000,
            )
        pro_cap = int(self.settings.pro_max_review_blocks)
        return DocumentReviewLimits(
            max_chars_per_block=2800,
            max_blocks_for_review=None if pro_cap <= 0 else pro_cap,
            max_block_send_chars=4800,
        )

    def max_pages_for_tier(self, tier: EntitlementTier) -> int:
        return (
            int(self.settings.pro_max_pages)
            if tier == EntitlementTier.pro
            else int(self.settings.free_max_pages)
        )

    def trust_copy(self) -> TrustCopy:
        return TrustCopy()

    def job_retention_notice(self, *, sensitive_mode: bool) -> str:
        base = self.trust_copy().files_scheduled_for_deletion
        if sensitive_mode:
            return f"{base} {self.trust_copy().sensitive_shorter_retention}"
        return base
