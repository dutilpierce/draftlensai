from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from draftlens_api.persistence.orm import Artifact, Job, SupportingFile, Upload
from draftlens_api.services.paths import DataPaths

logger = logging.getLogger(__name__)


@dataclass
class RetentionService:
    """Deletes uploads, working dirs, caches, tmp, and artifacts after retention; never mid-run."""

    paths: DataPaths

    def cleanup_eligible_jobs(
        self,
        db: Session,
        *,
        now: datetime | None = None,
        include_artifacts: bool = True,
    ) -> int:
        """
        Purge filesystem data for completed/failed jobs past `retention_until`.
        By default removes artifacts as well once the retention window expires.
        """
        now = now or datetime.now(timezone.utc)
        stmt = select(Job).where(
            Job.status.in_(("completed", "failed")),
            Job.retention_until.is_not(None),
            Job.retention_until < now,
            Job.data_purged_at.is_(None),
        )
        jobs = list(db.execute(stmt).scalars().all())
        removed = 0
        for job in jobs:
            try:
                self._cleanup_one_job(db, job, include_artifacts=include_artifacts, now=now)
                removed += 1
            except Exception:  # noqa: BLE001
                logger.exception("retention cleanup failed for job %s", job.id)
        if removed:
            db.commit()
        return removed

    def _cleanup_one_job(self, db: Session, job: Job, *, include_artifacts: bool, now: datetime) -> None:
        jid = job.id
        for p in (
            self.paths.uploads_main / jid,
            self.paths.uploads_supporting / jid,
            self.paths.job_working(jid),
            self.paths.tmp / jid,
        ):
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)

        for row in db.execute(select(SupportingFile).where(SupportingFile.job_id == jid)).scalars().all():
            if row.extracted_cache_path:
                cp = Path(row.extracted_cache_path)
                if cp.exists():
                    try:
                        cp.unlink()
                    except OSError:
                        pass

        if include_artifacts:
            art_dir = self.paths.job_artifacts(jid)
            if art_dir.exists():
                shutil.rmtree(art_dir, ignore_errors=True)

        for art in list(db.execute(select(Artifact).where(Artifact.job_id == jid)).scalars().all()):
            db.delete(art)
        for sf in list(db.execute(select(SupportingFile).where(SupportingFile.job_id == jid)).scalars().all()):
            db.delete(sf)
        for up in list(db.execute(select(Upload).where(Upload.job_id == jid)).scalars().all()):
            db.delete(up)

        meta = dict(job.job_config or {})
        meta["data_purge"] = {"filesystem_purged_at": now.isoformat(), "artifacts_included": include_artifacts}
        job.job_config = meta
        job.working_root = None
        job.retention_until = None
        job.data_purged_at = now
        db.flush()
