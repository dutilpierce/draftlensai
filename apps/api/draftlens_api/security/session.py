from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from draftlens_api.config import get_settings


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.app_session_secret, salt="draftlens-session")


def create_session_token(user_id: str) -> str:
    return _serializer().dumps({"uid": user_id})


def read_session_token(token: str, max_age_seconds: int) -> str:
    try:
        data: dict[str, Any] = _serializer().loads(token, max_age=max_age_seconds)
    except SignatureExpired as exc:
        raise HTTPException(status_code=401, detail="session_expired") from exc
    except BadSignature as exc:
        raise HTTPException(status_code=401, detail="invalid_session") from exc
    uid = data.get("uid")
    if not isinstance(uid, str):
        raise HTTPException(status_code=401, detail="invalid_session")
    return uid


def set_session_cookie(response: Response, user_id: str) -> None:
    settings = get_settings()
    token = create_session_token(user_id)
    max_age = int(timedelta(days=settings.session_days).total_seconds())
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.cookie_name, path="/")


def session_user_id_or_none(request: Request) -> str | None:
    settings = get_settings()
    token = request.cookies.get(settings.cookie_name)
    if not token:
        return None
    try:
        return read_session_token(
            token, max_age_seconds=int(timedelta(days=settings.session_days).total_seconds())
        )
    except HTTPException:
        return None
