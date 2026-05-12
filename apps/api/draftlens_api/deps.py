from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from draftlens_api.db import get_db_session


def get_db() -> Generator[Session, None, None]:
    db = get_db_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
