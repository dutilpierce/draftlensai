"""Drive API metadata for UI previews (same OAuth scopes as cloud import)."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
_METADATA_FIELDS = "id,name,mimeType,iconLink,thumbnailLink,webViewLink,size,modifiedTime"


def _str_or_none(val: object | None) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s or None


async def fetch_google_drive_file_metadata(*, access_token: str, file_id: str) -> dict[str, str | None]:
    """Return normalized Drive file fields for preview cards."""
    headers = {"Authorization": f"Bearer {access_token.strip()}"}
    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.get(
            f"{_DRIVE_FILES}/{file_id}",
            params={"fields": _METADATA_FIELDS, "supportsAllDrives": "true"},
            headers=headers,
        )
    if r.status_code == 401:
        raise ValueError("drive_metadata_unauthorized")
    if r.status_code == 403:
        raise ValueError("drive_metadata_forbidden")
    if r.status_code == 404:
        raise ValueError("drive_metadata_not_found")
    if r.status_code != 200:
        logger.warning("drive metadata unexpected status: %s", r.status_code)
        raise ValueError(f"drive_metadata_http_{r.status_code}")
    data = r.json()
    return {
        "id": str(data.get("id") or file_id),
        "name": str(data.get("name") or ""),
        "mime_type": str(data.get("mimeType") or ""),
        "icon_link": _str_or_none(data.get("iconLink")),
        "thumbnail_link": _str_or_none(data.get("thumbnailLink")),
        "web_view_link": _str_or_none(data.get("webViewLink")),
        "size": _str_or_none(data.get("size")),
        "modified_time": _str_or_none(data.get("modifiedTime")),
    }
