from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from draftlens_api.persistence.orm import Job, UsageEventRow


@dataclass
class UsageQuotaService:
    """
    Monthly usage visibility aligned with calendar months (UTC).
    Enforcement for job starts stays in EntitlementService; this is the shared counter surface.
    """

    db: Session

    def completed_jobs_this_month(self, user_id: str) -> int:
        ym = datetime.now(timezone.utc).strftime("%Y-%m")
        stmt = select(func.count()).select_from(Job).where(
            Job.user_id == user_id,
            Job.status == "completed",
            func.strftime("%Y-%m", Job.completed_at) == ym,
        )
        return int(self.db.execute(stmt).scalar_one())

    def record_usage_event(
        self,
        *,
        user_id: str,
        event_type: str,
        year_month: str | None = None,
        job_id: str | None = None,
        meta: dict | None = None,
    ) -> None:
        ym = year_month or datetime.now(timezone.utc).strftime("%Y-%m")
        self.db.add(
            UsageEventRow(
                user_id=user_id,
                job_id=job_id,
                event_type=event_type,
                year_month=ym,
                quantity=1,
                meta=meta or {},
            )
        )
