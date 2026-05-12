from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from draftlens_api.cloud.models import CloudFileReference, CloudImportBody, CloudImportRequest
from draftlens_api.cloud.service import stage_cloud_import
from draftlens_api.cloud.staging import read_staged, write_staged_bytes
from draftlens_api.services.paths import DataPaths
from tests.conftest import fake_pipeline_artifacts, minimal_docx_bytes


def _cookies_from_start(client: TestClient, email: str) -> None:
    r = client.post("/api/access/start", json={"email": email})
    assert r.status_code == 200
    from draftlens_api.config import get_settings

    name = get_settings().cookie_name
    assert name in r.cookies
    client.cookies.set(name, r.cookies[name])


def test_cloud_config_is_public(api_env: tuple[TestClient, object]) -> None:
    client, _ = api_env
    r = client.get("/api/cloud/config")
    assert r.status_code == 200
    body = r.json()
    assert "google_client_id" in body
    assert "google_picker_api_key" in body
    assert "dropbox_app_key" in body
    assert "microsoft_client_id" in body


def test_cloud_import_requires_session(api_env: tuple[TestClient, object]) -> None:
    client, _ = api_env
    r = client.post(
        "/api/cloud/import",
        json={
            "request": {
                "provider": "google_drive",
                "provider_file_id": "abc",
                "filename": "x.docx",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "document_role": "main",
            },
            "access_token": "fake",
        },
    )
    assert r.status_code == 401


def test_cloud_staging_roundtrip(api_env: tuple[TestClient, object]) -> None:
    _, data_dir = api_env
    from draftlens_api.config import get_settings

    paths = DataPaths.from_settings(get_settings())
    paths.ensure_layout()
    docx = minimal_docx_bytes()
    ref = CloudFileReference(
        provider="google_drive",
        provider_file_id="fid",
        filename="manuscript.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        document_role="main",
    )
    handle = write_staged_bytes(paths, user_id="u1", data=docx, reference=ref)
    blob, out = read_staged(paths, "u1", handle)
    assert blob.read_bytes() == docx
    assert out.filename == "manuscript.docx"


def test_cloud_staging_expires(api_env: tuple[TestClient, object], monkeypatch: pytest.MonkeyPatch) -> None:
    _, _data = api_env
    from draftlens_api.config import get_settings

    paths = DataPaths.from_settings(get_settings())
    paths.ensure_layout()
    ref = CloudFileReference(
        provider="dropbox",
        shared_link="https://example.com/x",
        filename="s.pdf",
        mime_type="application/pdf",
        document_role="supporting",
    )
    fake_now = [1_700_000_000.0]
    monkeypatch.setattr("draftlens_api.cloud.staging.time.time", lambda: fake_now[0])
    handle = write_staged_bytes(paths, user_id="u2", data=b"%PDF-1.4\n", reference=ref)
    fake_now[0] += 7200
    with pytest.raises(TimeoutError):
        read_staged(paths, "u2", handle)


def test_stage_cloud_import_mocked(api_env: tuple[TestClient, object]) -> None:
    import asyncio

    _, _ = api_env

    async def _run() -> None:
        from draftlens_api.config import get_settings

        paths = DataPaths.from_settings(get_settings())
        paths.ensure_layout()
        body = CloudImportBody(
            request=CloudImportRequest(
                provider="google_drive",
                provider_file_id="abc123",
                filename="m.docx",
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                document_role="main",
            ),
            access_token="tok",
        )
        fake = AsyncMock(
            return_value=(
                minimal_docx_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "m.docx",
            )
        )
        with patch("draftlens_api.cloud.service.download_for_import", fake):
            res = await stage_cloud_import(paths, user_id="u-import", body=body)
        assert res.import_handle
        blob, ref = read_staged(paths, "u-import", res.import_handle)
        assert blob.read_bytes() == minimal_docx_bytes()
        assert ref.provider == "google_drive"

    asyncio.run(_run())


async def _fake_execute(**kwargs: Any) -> dict[str, Any]:
    cfg = kwargs["job_config"]
    return fake_pipeline_artifacts(
        paths_root=kwargs["paths"].root,
        job_id=kwargs["job_id"],
        output_mode=cfg.output_mode,
        evidence_aware=bool(kwargs.get("supporting_pairs")),
    )


def test_create_job_with_cloud_main_handle(api_env: tuple[TestClient, object], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("draftlens_api.services.job_runner.execute_review_pipeline", _fake_execute)
    client, _ = api_env
    _cookies_from_start(client, "cloud-job@example.com")
    me = client.get("/api/access/me").json()
    uid = me["user_id"]

    from draftlens_api.config import get_settings

    paths = DataPaths.from_settings(get_settings())
    paths.ensure_layout()
    ref = CloudFileReference(
        provider="google_drive",
        provider_file_id="x",
        filename="manuscript.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        document_role="main",
    )
    handle = write_staged_bytes(paths, user_id=uid, data=minimal_docx_bytes(), reference=ref)

    data = {"output_mode": "review", "review_focus": "standard", "main_cloud_import_handle": handle}
    r = client.post("/api/jobs", data=data)
    assert r.status_code == 200, r.text


def test_create_job_ambiguous_main(api_env: tuple[TestClient, object]) -> None:
    client, _ = api_env
    _cookies_from_start(client, "amb@example.com")
    docx = minimal_docx_bytes()
    files = [
        (
            "main_document",
            ("m.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        )
    ]
    data = {"output_mode": "review", "review_focus": "standard", "main_cloud_import_handle": "some-handle"}
    r = client.post("/api/jobs", files=files, data=data)
    assert r.status_code == 400
    assert r.json()["detail"] == "main_document_ambiguous"
