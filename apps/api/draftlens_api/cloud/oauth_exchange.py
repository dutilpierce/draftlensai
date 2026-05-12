"""PKCE authorization-code exchange (server-side). No tokens persisted."""

from __future__ import annotations

import httpx

from draftlens_api.config import Settings

_DROPBOX_TOKEN = "https://api.dropboxapi.com/oauth2/token"
_MS_TOKEN = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
_MS_SCOPE = "Files.ReadWrite offline_access"


async def exchange_dropbox_authorization_code(
    settings: Settings,
    *,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict[str, str]:
    cid = settings.draftlens_cloud_dropbox_app_key.strip()
    if not cid:
        raise ValueError("dropbox_not_configured")
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": cid,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
    }
    sec = settings.draftlens_cloud_dropbox_app_secret.strip()
    if sec:
        data["client_secret"] = sec
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(_DROPBOX_TOKEN, data=data)
        r.raise_for_status()
        js = r.json()
    token = str(js.get("access_token") or "")
    if not token:
        raise ValueError("dropbox_token_missing")
    return {"access_token": token, "token_type": str(js.get("token_type") or "bearer")}


async def exchange_microsoft_authorization_code(
    settings: Settings,
    *,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict[str, str]:
    cid = settings.draftlens_cloud_microsoft_client_id.strip()
    if not cid:
        raise ValueError("microsoft_not_configured")
    data = {
        "client_id": cid,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
        "scope": _MS_SCOPE,
    }
    sec = settings.draftlens_cloud_microsoft_client_secret.strip()
    if sec:
        data["client_secret"] = sec
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(_MS_TOKEN, data=data)
        r.raise_for_status()
        js = r.json()
    token = str(js.get("access_token") or "")
    if not token:
        raise ValueError("microsoft_token_missing")
    return {"access_token": token, "token_type": str(js.get("token_type") or "bearer")}
