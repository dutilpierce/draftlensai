from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from draftlens_api.config import get_settings
from draftlens_api.db import get_or_create_user
from draftlens_api.deps import get_db
from draftlens_api.models.schemas import AccessMeResponse, AccessStartRequest, AccessStartResponse
from draftlens_api.persistence.orm import User
from draftlens_api.routes.access_helpers import build_access_me_response
from draftlens_api.security.session import session_user_id_or_none, set_session_cookie
from draftlens_api.services.entitlement_service import EntitlementService

router = APIRouter(prefix="/access", tags=["access"])


@router.post("/start", response_model=AccessStartResponse)
def access_start(payload: AccessStartRequest, response: Response, db: Session = Depends(get_db)):
    user = get_or_create_user(db, str(payload.email))
    set_session_cookie(response, user.id)
    settings = get_settings()
    ent = EntitlementService(db, settings)
    summary = ent.summary(user)
    return AccessStartResponse(ok=True, **build_access_me_response(user, summary).model_dump())


@router.get("/me", response_model=AccessMeResponse)
def access_me(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    uid = session_user_id_or_none(request)
    if not uid:
        raise HTTPException(status_code=401, detail="not_signed_in")
    user = db.get(User, uid)
    if user is None:
        raise HTTPException(status_code=401, detail="not_signed_in")
    ent = EntitlementService(db, settings)
    summary = ent.summary(user)
    return build_access_me_response(user, summary)
