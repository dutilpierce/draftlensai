"""Provider download/upload via httpx. Caller supplies short-lived user access tokens (never stored)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx

from draftlens_api.cloud.models import CloudImportRequest, CloudProvider

_DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
_DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
_GRAPH = "https://graph.microsoft.com/v1.0"
_DROPBOX_CONTENT = "https://content.dropboxapi.com/2"


def _safe_filename(name: str) -> str:
    base = re.sub(r"[^\w.\-]+", "_", name, flags=re.UNICODE).strip("._") or "document"
    return base[:200]


def export_filename(*, original_filename: str, artifact_filename: str) -> str:
    """New file name: originalstem.tag.ext — never in-place."""
    orig = _safe_filename(original_filename.rsplit("/", 1)[-1])
    art = artifact_filename.rsplit("/", 1)[-1]
    o_stem = orig.rsplit(".", 1)[0] if "." in orig else orig
    a_lower = art.lower()
    if "reviewed" in a_lower:
        tag = "reviewed"
    elif "corrected" in a_lower:
        tag = "corrected"
    else:
        tag = "draftlens"
    ext = orig.rsplit(".", 1)[-1].lower() if "." in orig else ""
    art_ext = art.rsplit(".", 1)[-1].lower() if "." in art else ext
    use_ext = art_ext or ext or "bin"
    return f"{o_stem}.{tag}.{use_ext}"


def _dropbox_dl_url(link: str) -> str:
    p = urlparse(link.strip())
    q = [(k, v[0]) for k, vals in parse_qs(p.query).items() for v in vals if v]
    keys = {k for k, _ in q}
    if "dl" not in keys:
        q.append(("dl", "1"))
    else:
        q = [(k, "1" if k == "dl" else v) for k, v in q]
    new_query = urlencode(q)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))


async def download_for_import(req: CloudImportRequest, access_token: str) -> tuple[bytes, str, str]:
    """Returns (bytes, resolved_mime_type, resolved_filename)."""
    if req.provider == "google_drive":
        return await _google_drive_download(req, access_token)
    if req.provider == "dropbox":
        return await _dropbox_download(req, access_token)
    if req.provider == "onedrive":
        return await _onedrive_download(req, access_token)
    raise ValueError("unknown_provider")


async def _google_drive_download(req: CloudImportRequest, token: str) -> tuple[bytes, str, str]:
    if not req.provider_file_id.strip():
        raise ValueError("google_drive_requires_file_id")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=120.0) as client:
        meta_r = await client.get(
            f"{_DRIVE_FILES}/{req.provider_file_id}",
            headers=headers,
            params={"fields": "id,name,mimeType"},
        )
        meta_r.raise_for_status()
        meta: dict[str, Any] = meta_r.json()
        mime = str(meta.get("mimeType") or req.mime_type or "application/octet-stream")
        name = _safe_filename(str(meta.get("name") or req.filename))

        if mime == "application/vnd.google-apps.document":
            export_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            r = await client.get(
                f"{_DRIVE_FILES}/{req.provider_file_id}/export",
                headers=headers,
                params={"mimeType": export_mime},
            )
            r.raise_for_status()
            if not name.lower().endswith(".docx"):
                name = f"{name.rsplit('.', 1)[0]}.docx" if "." in name else f"{name}.docx"
            return r.content, export_mime, name

        if mime == "application/vnd.google-apps.spreadsheet":
            export_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            r = await client.get(
                f"{_DRIVE_FILES}/{req.provider_file_id}/export",
                headers=headers,
                params={"mimeType": export_mime},
            )
            r.raise_for_status()
            if not name.lower().endswith(".xlsx"):
                name = f"{name.rsplit('.', 1)[0]}.xlsx" if "." in name else f"{name}.xlsx"
            return r.content, export_mime, name

        r = await client.get(
            f"{_DRIVE_FILES}/{req.provider_file_id}",
            headers=headers,
            params={"alt": "media"},
        )
        r.raise_for_status()
        return r.content, mime, name


async def _dropbox_download(req: CloudImportRequest, token: str) -> tuple[bytes, str, str]:
    link = (req.shared_link or "").strip()
    if link:
        direct = _dropbox_dl_url(link)
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            r = await client.get(direct, headers={"User-Agent": "DraftLens/1.0"})
            if r.status_code == 200 and r.content:
                return r.content, req.mime_type or "application/octet-stream", _safe_filename(req.filename)
        if not token.strip():
            raise ValueError("dropbox_requires_token_or_public_direct_link")
        async with httpx.AsyncClient(timeout=120.0) as client:
            r2 = await client.post(
                "https://api.dropboxapi.com/2/sharing/get_shared_link_file",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"url": link},
            )
            r2.raise_for_status()
            return r2.content, req.mime_type or "application/octet-stream", _safe_filename(req.filename)

    if not req.provider_file_id.strip() or not token.strip():
        raise ValueError("dropbox_requires_shared_link_or_path_token")
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            f"{_DROPBOX_CONTENT}/files/download",
            headers={
                "Authorization": f"Bearer {token}",
                "Dropbox-API-Arg": json.dumps({"path": req.provider_file_id}),
            },
        )
        r.raise_for_status()
        return r.content, req.mime_type or "application/octet-stream", _safe_filename(req.filename)


async def _onedrive_download(req: CloudImportRequest, token: str) -> tuple[bytes, str, str]:
    dl = (req.download_url or "").strip()
    if dl:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            r = await client.get(dl)
            r.raise_for_status()
            mime = req.mime_type or r.headers.get("content-type") or "application/octet-stream"
            return r.content, mime.split(";")[0].strip(), _safe_filename(req.filename)

    if not req.provider_file_id.strip():
        raise ValueError("onedrive_requires_item_id_or_download_url")
    if not token.strip():
        raise ValueError("onedrive_requires_token_without_download_url")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.get(
            f"{_GRAPH}/me/drive/items/{req.provider_file_id}/content",
            headers=headers,
        )
        r.raise_for_status()
        mime = req.mime_type or r.headers.get("content-type") or "application/octet-stream"
        return r.content, mime.split(";")[0].strip(), _safe_filename(req.filename)


async def upload_export(
    provider: CloudProvider,
    *,
    access_token: str,
    body: bytes,
    remote_name: str,
    parent_folder_id: str | None,
) -> tuple[str | None, str | None]:
    if provider == "google_drive":
        return await _google_upload(access_token, body, remote_name, parent_folder_id)
    if provider == "dropbox":
        return await _dropbox_upload(access_token, body, remote_name)
    if provider == "onedrive":
        return await _onedrive_upload(access_token, body, remote_name, parent_folder_id)
    raise ValueError("unknown_provider")


async def _google_upload(token: str, body: bytes, name: str, parent: str | None) -> tuple[str | None, str | None]:
    meta: dict[str, Any] = {"name": name}
    if parent:
        meta["parents"] = [parent]
    boundary = "draftlens_boundary"
    meta_json = json.dumps(meta)
    raw = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta_json}\r\n"
        f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n".encode("utf-8")
        + body
        + f"\r\n--{boundary}--\r\n".encode("utf-8")
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/related; boundary={boundary}",
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(
            _DRIVE_UPLOAD,
            headers=headers,
            params={"uploadType": "multipart"},
            content=raw,
        )
        r.raise_for_status()
        data = r.json()
        fid = str(data.get("id") or "")
        link = f"https://drive.google.com/file/d/{fid}/view" if fid else None
        return fid or None, link


async def _dropbox_upload(token: str, body: bytes, name: str) -> tuple[str | None, str | None]:
    path = f"/DraftLens/{_safe_filename(name)}"
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(
            f"{_DROPBOX_CONTENT}/files/upload",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
                "Dropbox-API-Arg": json.dumps({"path": path, "mode": "add", "autorename": True, "mute": False}),
            },
            content=body,
        )
        r.raise_for_status()
        js = r.json()
        rid = str(js.get("id") or "")
        return rid or None, None


async def _onedrive_upload(token: str, body: bytes, name: str, parent: str | None) -> tuple[str | None, str | None]:
    from urllib.parse import quote

    safe = _safe_filename(name)
    headers = {"Authorization": f"Bearer {token}"}
    enc = quote(safe)
    if parent:
        url = f"{_GRAPH}/me/drive/items/{parent}:/{enc}:/content"
    else:
        url = f"{_GRAPH}/me/drive/root:/DraftLens/{enc}:/content"
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.put(url, headers=headers, content=body)
        r.raise_for_status()
        data = r.json()
        iid = str(data.get("id") or "")
        web = str(data.get("webUrl") or "") or None
        return iid or None, web
