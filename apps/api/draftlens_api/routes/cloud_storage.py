from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from draftlens_api.cloud.models import (
    CloudExportBody,
    CloudExportResult,
    CloudImportBody,
    CloudImportResult,
    DropboxPkceTokenRequest,
    MicrosoftPkceTokenRequest,
)
from draftlens_api.cloud.oauth_exchange import (
    exchange_dropbox_authorization_code,
    exchange_microsoft_authorization_code,
)
from draftlens_api.cloud.service import export_job_artifact, stage_cloud_import
from draftlens_api.config import get_settings
from draftlens_api.deps import get_db
from draftlens_api.persistence.orm import User
from draftlens_api.security.session import session_user_id_or_none
from draftlens_api.services.paths import DataPaths

router = APIRouter(prefix="/cloud", tags=["cloud"])
logger = logging.getLogger(__name__)


def _user(request: Request, db: Session) -> User:
    uid = session_user_id_or_none(request)
    if not uid:
        raise HTTPException(status_code=401, detail="not_signed_in")
    user = db.get(User, uid)
    if user is None:
        raise HTTPException(status_code=401, detail="not_signed_in")
    return user


@router.get("/config")
def cloud_public_config():
    """Public OAuth client identifiers for browser pickers (not secrets)."""
    s = get_settings()
    return {
        "google_client_id": s.draftlens_cloud_google_client_id or None,
        "google_picker_api_key": s.draftlens_cloud_google_picker_api_key or None,
        "dropbox_app_key": s.draftlens_cloud_dropbox_app_key or None,
        "microsoft_client_id": s.draftlens_cloud_microsoft_client_id or None,
        "api_public_url": s.draftlens_api_public_url,
    }


@router.post("/import", response_model=CloudImportResult)
async def cloud_import(
    request: Request,
    body: CloudImportBody,
    db: Session = Depends(get_db),
):
    user = _user(request, db)
    settings = get_settings()
    paths = DataPaths.from_settings(settings)
    paths.ensure_layout()
    return await stage_cloud_import(paths, user_id=user.id, body=body)


@router.post("/export", response_model=CloudExportResult)
async def cloud_export(
    request: Request,
    body: CloudExportBody,
    db: Session = Depends(get_db),
):
    user = _user(request, db)
    settings = get_settings()
    paths = DataPaths.from_settings(settings)
    return await export_job_artifact(db, paths, user_id=user.id, body=body)


@router.post("/oauth/dropbox/token")
async def dropbox_pkce_token(request: Request, payload: DropboxPkceTokenRequest, db: Session = Depends(get_db)):
    _user(request, db)
    settings = get_settings()
    try:
        return await exchange_dropbox_authorization_code(
            settings,
            code=payload.code,
            redirect_uri=payload.redirect_uri,
            code_verifier=payload.code_verifier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("dropbox token exchange failed")
        raise HTTPException(status_code=502, detail="oauth_exchange_failed") from exc


@router.post("/oauth/microsoft/token")
async def microsoft_pkce_token(request: Request, payload: MicrosoftPkceTokenRequest, db: Session = Depends(get_db)):
    _user(request, db)
    settings = get_settings()
    try:
        return await exchange_microsoft_authorization_code(
            settings,
            code=payload.code,
            redirect_uri=payload.redirect_uri,
            code_verifier=payload.code_verifier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("microsoft token exchange failed")
        raise HTTPException(status_code=502, detail="oauth_exchange_failed") from exc
