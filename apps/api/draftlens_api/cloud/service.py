from __future__ import annotations

import logging
from pathlib import Path

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from draftlens_api.cloud.models import (
    CloudExportBody,
    CloudExportResult,
    CloudFileReference,
    CloudImportBody,
    CloudImportResult,
)
from draftlens_api.cloud.staging import write_staged_bytes
from draftlens_api.cloud.transfer import download_for_import, export_filename, upload_export
from draftlens_api.persistence.orm import Artifact, Job, Upload
from draftlens_api.services.paths import DataPaths

logger = logging.getLogger(__name__)


async def stage_cloud_import(paths: DataPaths, *, user_id: str, body: CloudImportBody) -> CloudImportResult:
    req = body.request
    token = body.access_token.strip()
    if req.provider == "google_drive" and not token:
        raise HTTPException(status_code=400, detail="access_token_required")
    if req.provider == "onedrive" and not (req.download_url or "").strip() and not token:
        raise HTTPException(status_code=400, detail="access_token_or_download_url_required")

    try:
        raw, mime, name = await download_for_import(req, token)
    except httpx.HTTPStatusError as exc:
        logger.warning("cloud import http error: %s", exc, exc_info=False)
        raise HTTPException(status_code=502, detail="cloud_download_failed") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ref = CloudFileReference(
        provider=req.provider,
        provider_file_id=req.provider_file_id,
        shared_link=req.shared_link,
        download_url=None,
        filename=name,
        mime_type=mime,
        document_role=req.document_role,
    )
    handle = write_staged_bytes(paths, user_id=user_id, data=raw, reference=ref)
    return CloudImportResult(import_handle=handle, reference=ref)


async def export_job_artifact(
    db: Session,
    paths: DataPaths,
    *,
    user_id: str,
    body: CloudExportBody,
) -> CloudExportResult:
    job = db.get(Job, body.job_id)
    if job is None or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="job_not_found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="job_not_completed")

    art = db.execute(
        select(Artifact).where(Artifact.job_id == body.job_id, Artifact.name == Path(body.request.artifact_name).name)
    ).scalar_one_or_none()
    if art is None or not art.storage_path:
        raise HTTPException(status_code=404, detail="artifact_not_found")

    main_row = db.execute(select(Upload).where(Upload.job_id == body.job_id, Upload.kind == "main")).scalar_one_or_none()
    original_name = main_row.original_name if main_row else body.request.artifact_name

    target = Path(art.storage_path)
    if not target.is_absolute():
        target = paths.root / target
    if not target.is_file():
        raise HTTPException(status_code=404, detail="artifact_not_found")

    data = target.read_bytes()
    remote_name = export_filename(original_filename=original_name, artifact_filename=body.request.artifact_name)

    try:
        rid, link = await upload_export(
            body.request.provider,
            access_token=body.access_token,
            body=data,
            remote_name=remote_name,
            parent_folder_id=body.request.parent_folder_id,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning("cloud export http error: %s", exc, exc_info=False)
        raise HTTPException(status_code=502, detail="cloud_upload_failed") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CloudExportResult(provider=body.request.provider, remote_file_id=rid, web_view_link=link)
