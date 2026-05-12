"""POST /api/jobs/{id}/apply-fixes — derived fix job from completed review + lineage."""

from __future__ import annotations

import time
from typing import Any

import pytest
from sqlalchemy import select

from draftlens_api.db import get_db_session
from draftlens_api.engine.status_stage_order import validate_monotonic_stage_sequence
from draftlens_api.persistence.orm import JobStatusEventRow
from draftlens_api.services.entitlement_service import EntitlementService
from tests.conftest import fake_pipeline_artifacts, minimal_docx_bytes
from tests.integration.test_mvp_app import _cookies_from_start


async def _fake_execute_review_pipeline(**kwargs: Any) -> dict[str, Any]:
    cfg = kwargs["job_config"]
    return fake_pipeline_artifacts(
        paths_root=kwargs["paths"].root,
        job_id=kwargs["job_id"],
        output_mode=cfg.output_mode,
        evidence_aware=bool(kwargs.get("supporting_pairs")),
    )


def test_apply_fixes_creates_derived_fix_job(api_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "draftlens_api.services.job_runner.execute_review_pipeline",
        _fake_execute_review_pipeline,
    )
    monkeypatch.setattr(EntitlementService, "assert_job_allowed", lambda self, **kwargs: None)

    client, _data_dir = api_env
    _cookies_from_start(client, "apply-fix-user@example.com")

    docx = minimal_docx_bytes()
    r = client.post(
        "/api/jobs",
        files=[
            (
                "main_document",
                ("m.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            )
        ],
        data={"output_mode": "review", "review_focus": "standard"},
    )
    assert r.status_code == 200, r.text
    review_id = r.json()["job"]["id"]

    for _ in range(80):
        g = client.get(f"/api/jobs/{review_id}")
        assert g.status_code == 200
        if g.json()["status"] == "completed":
            break
        time.sleep(0.05)
    arts = {a["name"] for a in client.get(f"/api/jobs/{review_id}/artifacts").json()["artifacts"]}
    assert "fix_seed_snapshot.json" in arts

    af = client.post(f"/api/jobs/{review_id}/apply-fixes")
    assert af.status_code == 200, af.text
    body = af.json()
    assert body["source_review_job_id"] == review_id
    fix_job = body["job"]
    assert fix_job["output_mode"] == "fix"
    assert fix_job["fix_generation_started_from_review"] is True
    assert fix_job["post_review_fix_seed_job_id"] == review_id

    fix_id = fix_job["id"]
    for _ in range(80):
        g2 = client.get(f"/api/jobs/{fix_id}")
        assert g2.status_code == 200
        if g2.json()["status"] == "completed":
            break
        time.sleep(0.05)

    db = get_db_session()
    try:
        stages = list(
            db.execute(
                select(JobStatusEventRow.stage).where(JobStatusEventRow.job_id == fix_id).order_by(JobStatusEventRow.id)
            ).scalars()
        )
        ok, err = validate_monotonic_stage_sequence(stages)
        assert ok, err

        details = list(
            db.execute(
                select(JobStatusEventRow.detail).where(JobStatusEventRow.job_id == fix_id).order_by(JobStatusEventRow.id)
            ).scalars()
        )
        any_progress = any(
            isinstance(d, dict) and isinstance(d.get("progress_percent"), (int, float)) for d in details if d
        )
        assert any_progress, "expected progress_percent on at least one persisted event"
    finally:
        db.close()


def test_apply_fixes_requires_seed(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Completed review without fix_seed_snapshot returns 409."""
    monkeypatch.setattr(EntitlementService, "assert_job_allowed", lambda self, **kwargs: None)

    from draftlens_api import config as cfg
    from draftlens_api import db as dbm
    from draftlens_api.db import init_db
    from draftlens_api.main import create_app
    from draftlens_api.domain.models import ReviewJobConfig
    from draftlens_api.persistence.orm import Artifact, Job, Upload

    db_path = tmp_path / "seedless.db"
    data_dir = tmp_path / "seedless-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("APP_SESSION_SECRET", "x" * 40)
    monkeypatch.setenv("DRAFTLENS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("DRAFTLENS_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("FREE_MONTHLY_PROOFS", "1")
    monkeypatch.setenv("FREE_MAX_PAGES", "25")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_testsecret")
    monkeypatch.setenv("STRIPE_PRICE_ID_PRO_MONTHLY", "price_test_123")

    cfg.get_settings.cache_clear()
    cfg.get_provider_env.cache_clear()
    dbm._engine = None
    dbm._SessionLocal = None
    init_db()
    app = create_app()

    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=True) as client:
        r0 = client.post("/api/access/start", json={"email": "seedless@example.com"})
        assert r0.status_code == 200
        from draftlens_api.config import get_settings

        name = get_settings().cookie_name
        client.cookies.set(name, r0.cookies[name])

        db = get_db_session()
        try:
            uid = r0.json()["user_id"]
            job_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
            from draftlens_api.services.paths import DataPaths, main_upload_path

            paths = DataPaths.from_settings(cfg.get_settings())
            paths.ensure_layout()
            p = main_upload_path(paths, job_id, "m.docx")
            p.write_bytes(minimal_docx_bytes())
            rel = str(p.relative_to(paths.root))
            job_cfg = ReviewJobConfig(
                output_mode="review",
                main_original_filename="m.docx",
                main_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            db.add(
                Job(
                    id=job_id,
                    user_id=uid,
                    status="completed",
                    output_mode="review",
                    review_focus="standard",
                    sensitive_mode=False,
                    page_count=1,
                    working_root=str(paths.job_working(job_id)),
                    job_config=job_cfg.model_dump(mode="json"),
                )
            )
            db.add(
                Upload(
                    id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                    job_id=job_id,
                    kind="main",
                    storage_path=rel,
                    original_name="m.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    byte_size=p.stat().st_size,
                )
            )
            art_dir = paths.job_artifacts(job_id)
            art_dir.mkdir(parents=True, exist_ok=True)
            stats = art_dir / "pipeline_stats.json"
            stats.write_text('{"consensus_reached": true}', encoding="utf-8")
            db.add(
                Artifact(
                    id="cccccccc-cccc-cccc-cccc-cccccccccccc",
                    job_id=job_id,
                    name="pipeline_stats.json",
                    storage_path=str(stats.resolve()),
                    mime="application/json",
                    byte_size=stats.stat().st_size,
                )
            )
            db.commit()
        finally:
            db.close()

        resp = client.post(f"/api/jobs/{job_id}/apply-fixes")
        assert resp.status_code == 409
        assert resp.json()["detail"] == "apply_fixes_seed_missing_reprocess_review"
