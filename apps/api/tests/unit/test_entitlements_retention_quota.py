from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic_settings import SettingsConfigDict
from sqlalchemy.orm import Session

from draftlens_api.config import Settings
from draftlens_api.db import get_db_session
from draftlens_api.domain.enums import EntitlementTier
from draftlens_api.persistence.orm import Artifact, Job, Upload, User
from draftlens_api.policies.central import CentralPolicyService
from draftlens_api.services.entitlement_service import EntitlementService
from draftlens_api.services.paths import DataPaths
from draftlens_api.services.retention_service import RetentionService
from draftlens_api.services.usage_quota import UsageQuotaService


@pytest.fixture
def db_session(api_env) -> Session:
    """Fresh ORM session (same DB as TestClient)."""
    s = get_db_session()
    try:
        yield s
    finally:
        s.close()


def test_entitlement_free_blocks_fix_and_supporting(db_session: Session) -> None:
    from draftlens_api.config import get_settings

    settings = get_settings()
    u = User(email="free@example.com", plan="free")
    db_session.add(u)
    db_session.commit()

    ent = EntitlementService(db_session, settings)
    user = db_session.get(User, u.id)
    assert ent.tier_for_user(user) == EntitlementTier.free
    summary = ent.summary(user)
    assert summary.fix_mode_allowed is False
    assert summary.supporting_files_allowed is False

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        ent.assert_job_allowed(user=user, output_mode="fix", supporting_count=0, pages=1)
    assert exc.value.detail == "fix_mode_requires_pro"

    with pytest.raises(HTTPException) as exc:
        ent.assert_job_allowed(user=user, output_mode="review", supporting_count=1, pages=1)
    assert exc.value.detail == "supporting_files_require_pro"


def test_entitlement_free_quota_enforcement(db_session: Session) -> None:
    from draftlens_api.config import get_settings

    settings = get_settings()
    u = User(email="quota@example.com", plan="free")
    db_session.add(u)
    db_session.flush()
    now = datetime.now(timezone.utc)
    j = Job(
        id="job-done",
        user_id=u.id,
        status="completed",
        output_mode="review",
        review_focus="standard",
        page_count=2,
        retention_until=now + timedelta(days=1),
        completed_at=now,
    )
    db_session.add(j)
    db_session.commit()

    ent = EntitlementService(db_session, settings)
    user = db_session.get(User, u.id)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        ent.assert_job_allowed(user=user, output_mode="review", supporting_count=0, pages=1)
    assert exc.value.detail == "free_monthly_limit_reached"


def test_entitlement_pro_fair_use_cap(db_session: Session) -> None:
    from draftlens_api.config import get_settings

    settings = get_settings()
    u = User(email="procap@example.com", plan="pro", billing_status="active")
    db_session.add(u)
    db_session.flush()
    now = datetime.now(timezone.utc)
    for i in range(settings.pro_fair_use_docs_per_month):
        db_session.add(
            Job(
                id=f"pj-{i}",
                user_id=u.id,
                status="completed",
                output_mode="review",
                review_focus="standard",
                page_count=1,
                retention_until=now + timedelta(days=1),
                completed_at=now,
            )
        )
    db_session.commit()

    ent = EntitlementService(db_session, settings)
    user = db_session.get(User, u.id)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        ent.assert_job_allowed(user=user, output_mode="review", supporting_count=0, pages=1)
    assert exc.value.detail == "pro_monthly_cap_reached"


def test_page_limit_enforcement(db_session: Session) -> None:
    from draftlens_api.config import get_settings

    settings = get_settings()
    u = User(email="pages@example.com", plan="free")
    db_session.add(u)
    db_session.commit()
    ent = EntitlementService(db_session, settings)
    user = db_session.get(User, u.id)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        ent.assert_job_allowed(user=user, output_mode="review", supporting_count=0, pages=999)
    assert exc.value.detail == "document_page_limit_exceeded"


def test_usage_quota_month_boundary(db_session: Session) -> None:
    """Jobs completed in a prior calendar month (UTC) do not count toward this month."""
    u = User(email="ym@example.com", plan="free")
    db_session.add(u)
    db_session.flush()
    old = datetime(2020, 1, 15, tzinfo=timezone.utc)
    db_session.add(
        Job(
            id="old-job",
            user_id=u.id,
            status="completed",
            output_mode="review",
            review_focus="standard",
            page_count=1,
            retention_until=old + timedelta(days=7),
            completed_at=old,
        )
    )
    db_session.commit()
    q = UsageQuotaService(db_session)
    assert q.completed_jobs_this_month(u.id) == 0


def test_central_policy_retention_and_limits() -> None:
    class _SettingsForTest(Settings):
        """Avoid picking up repo `.env` retention overrides during unit construction."""

        model_config = SettingsConfigDict(env_file=None, extra="ignore")

    s = _SettingsForTest(
        app_session_secret="x" * 32,
        data_retention_hours_default=168,
        data_retention_hours_sensitive=24,
        free_max_review_blocks=10,
        pro_max_review_blocks=0,
        free_max_pages=25,
        pro_max_pages=500,
    )
    pol = CentralPolicyService(s)
    assert pol.retention_hours(sensitive_mode=False) == 168
    assert pol.retention_hours(sensitive_mode=True) == 24
    assert pol.document_review_limits(EntitlementTier.free).max_blocks_for_review == s.free_max_review_blocks
    assert pol.document_review_limits(EntitlementTier.pro).max_blocks_for_review is None
    assert pol.max_pages_for_tier(EntitlementTier.free) == 25


def test_retention_service_purges_filesystem_and_rows(db_session: Session, tmp_path: Path) -> None:
    paths = DataPaths(root=tmp_path)
    paths.ensure_layout()

    u = User(email="ret@example.com", plan="free")
    db_session.add(u)
    db_session.flush()
    past = datetime.now(timezone.utc) - timedelta(days=30)
    jid = "ret-job-1"
    paths.uploads_main.mkdir(parents=True, exist_ok=True)
    (paths.uploads_main / jid).mkdir(parents=True, exist_ok=True)
    (paths.uploads_main / jid / "main.docx").write_bytes(b"x")
    paths.job_artifacts(jid).mkdir(parents=True, exist_ok=True)
    (paths.job_artifacts(jid) / "out.txt").write_text("artifact", encoding="utf-8")

    j = Job(
        id=jid,
        user_id=u.id,
        status="completed",
        output_mode="review",
        review_focus="standard",
        page_count=1,
        retention_until=past,
    )
    db_session.add(j)
    db_session.flush()
    up = Upload(
        id="up1",
        job_id=jid,
        kind="main",
        storage_path=str((paths.uploads_main / jid / "main.docx").relative_to(paths.root)),
        original_name="main.docx",
        mime="application/vnd",
        byte_size=1,
    )
    db_session.add(up)
    art = Artifact(
        id="a1",
        job_id=jid,
        name="out.txt",
        storage_path=str((paths.job_artifacts(jid) / "out.txt").resolve()),
        mime="text/plain",
        byte_size=1,
    )
    db_session.add(art)
    db_session.commit()

    n = RetentionService(paths).cleanup_eligible_jobs(db_session)
    assert n == 1
    assert not (paths.uploads_main / jid).exists()
    assert not paths.job_artifacts(jid).exists()
    assert db_session.get(Artifact, "a1") is None
    assert db_session.get(Upload, "up1") is None
