from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from pathlib import Path

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from draftlens_api.config import get_settings
from draftlens_api.persistence.orm import Base, Entitlement, JobStatusEventRow, User

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None

_sse_subscribers: dict[str, set[asyncio.Queue[dict]]] = defaultdict(set)


def _sqlite_migrate_jobs(engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    try:
        insp = inspect(engine)
        if not insp.has_table("jobs"):
            return
        cols = {c["name"] for c in insp.get_columns("jobs")}
        with engine.begin() as conn:
            if "data_purged_at" not in cols:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN data_purged_at DATETIME"))
    except Exception:
        logger.exception("sqlite jobs migration skipped")


def _sqlite_migrate_users(engine) -> None:
    """Add columns introduced after first deploy (SQLite has no ALTER in create_all)."""
    if engine.dialect.name != "sqlite":
        return
    try:
        insp = inspect(engine)
        if not insp.has_table("users"):
            return
        cols = {c["name"] for c in insp.get_columns("users")}
        with engine.begin() as conn:
            if "billing_status" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN billing_status VARCHAR(64)"))
            if "subscription_current_period_end" not in cols:
                conn.execute(
                    text("ALTER TABLE users ADD COLUMN subscription_current_period_end DATETIME")
                )
    except Exception:
        logger.exception("sqlite user migration skipped")


def _ensure_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            future=True,
        )
        Base.metadata.create_all(bind=_engine)
        _sqlite_migrate_users(_engine)
        _sqlite_migrate_jobs(_engine)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def get_db_session() -> Session:
    _ensure_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def init_db() -> None:
    _ensure_engine()


def register_sse_subscriber(job_id: str, queue: asyncio.Queue[dict]) -> None:
    _sse_subscribers[job_id].add(queue)


def unregister_sse_subscriber(job_id: str, queue: asyncio.Queue[dict]) -> None:
    subs = _sse_subscribers.get(job_id)
    if not subs:
        return
    subs.discard(queue)
    if not subs:
        _sse_subscribers.pop(job_id, None)


async def broadcast_job_event(job_id: str, payload: dict) -> None:
    for q in list(_sse_subscribers.get(job_id, ())):
        try:
            await q.put(payload)
        except Exception:
            logger.exception("SSE broadcast failed for job %s", job_id)


def persist_job_event(session: Session, job_id: str, stage: str, message: str, detail: dict | None):
    ev = JobStatusEventRow(job_id=job_id, stage=stage, message=message, detail=detail)
    session.add(ev)
    session.flush()


def get_or_create_user(session: Session, email: str) -> User:
    stmt = select(User).where(User.email == email.lower())
    user = session.execute(stmt).scalar_one_or_none()
    if user:
        return user
    user = User(email=email.lower(), plan="free")
    session.add(user)
    session.flush()
    session.add(Entitlement(user_id=user.id, tier="free", source="signup"))
    session.flush()
    return user
