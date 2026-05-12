from __future__ import annotations

import time
from typing import Any

import pytest
from sqlalchemy import select

from draftlens_api.config import get_settings
from draftlens_api.db import get_db_session
from draftlens_api.engine.status_stage_order import validate_monotonic_stage_sequence
from draftlens_api.persistence.orm import JobStatusEventRow
from tests.conftest import fake_pipeline_artifacts, minimal_docx_bytes


async def _fake_execute_review_pipeline(**kwargs: Any) -> dict[str, Any]:
    cfg = kwargs["job_config"]
    return fake_pipeline_artifacts(
        paths_root=kwargs["paths"].root,
        job_id=kwargs["job_id"],
        output_mode=cfg.output_mode,
        evidence_aware=bool(kwargs.get("supporting_pairs")),
    )


def _cookies_from_start(client, email: str) -> None:
    r = client.post("/api/access/start", json={"email": email})
    assert r.status_code == 200
    assert r.json()["access_tier"] == "free"
    name = get_settings().cookie_name
    assert name in r.cookies
    client.cookies.set(name, r.cookies[name])


def test_integration_access_entitlements_and_review_job(api_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "draftlens_api.services.job_runner.execute_review_pipeline",
        _fake_execute_review_pipeline,
    )
    client, _ = api_env
    _cookies_from_start(client, "mvp-free@example.com")

    docx = minimal_docx_bytes()
    files = [
        (
            "main_document",
            (
                "manuscript.docx",
                docx,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        )
    ]
    data = {"output_mode": "review", "review_focus": "standard"}
    r = client.post("/api/jobs", files=files, data=data)
    assert r.status_code == 200, r.text
    job_id = r.json()["job"]["id"]

    status = None
    for _ in range(80):
        g = client.get(f"/api/jobs/{job_id}")
        assert g.status_code == 200
        status = g.json()["status"]
        if status == "completed":
            break
        if status == "failed":
            raise AssertionError(g.json().get("error_message"))
        time.sleep(0.05)
    assert status == "completed"

    arts = client.get(f"/api/jobs/{job_id}/artifacts").json()["artifacts"]
    names = {a["name"] for a in arts}
    assert "reviewed.docx" in names
    assert "pipeline_stats.json" in names
    assert "fix_seed_snapshot.json" in names

    db = get_db_session()
    try:
        stages = list(
            db.execute(
                select(JobStatusEventRow.stage).where(JobStatusEventRow.job_id == job_id).order_by(JobStatusEventRow.id)
            ).scalars()
        )
        ok, err = validate_monotonic_stage_sequence(stages)
        assert ok, err
    finally:
        db.close()


def test_integration_free_blocks_fix_and_supporting(api_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "draftlens_api.services.job_runner.execute_review_pipeline",
        _fake_execute_review_pipeline,
    )
    client, _ = api_env
    _cookies_from_start(client, "mvp-block@example.com")
    docx = minimal_docx_bytes()

    r_fix = client.post(
        "/api/jobs",
        files=[("main_document", ("m.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        data={"output_mode": "fix", "review_focus": "standard"},
    )
    assert r_fix.status_code == 403
    assert r_fix.json()["detail"] == "fix_mode_requires_pro"

    r_sup = client.post(
        "/api/jobs",
        files=[
            ("main_document", ("m.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("supporting_files", ("note.txt", b"evidence only", "text/plain")),
        ],
        data={"output_mode": "review", "review_focus": "standard"},
    )
    assert r_sup.status_code == 403
    assert r_sup.json()["detail"] == "supporting_files_require_pro"


def test_integration_pro_checkout_webhook_fix_supporting_evidence_and_downgrade(api_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "draftlens_api.services.job_runner.execute_review_pipeline",
        _fake_execute_review_pipeline,
    )
    monkeypatch.setattr(
        "stripe.checkout.Session.create",
        lambda **kwargs: {"url": "https://stripe.test/checkout-session"},
    )

    client, _ = api_env
    _cookies_from_start(client, "mvp-pro@example.com")

    monkeypatch.setattr(
        "stripe.Customer.create",
        lambda **kwargs: {"id": "cus_mvp_pro"},
    )

    chk = client.post("/api/billing/checkout", json={})
    assert chk.status_code == 200
    assert chk.json()["url"].startswith("https://stripe.test/")

    me = client.get("/api/access/me")
    uid = me.json()["user_id"]
    db = get_db_session()
    try:
        from draftlens_api.persistence.orm import User

        user = db.get(User, uid)
        assert user is not None
        assert user.stripe_customer_id == "cus_mvp_pro"
    finally:
        db.close()

    from tests.conftest import stripe_signature_header

    up_event = {
        "id": "evt_sub_up",
        "object": "event",
        "api_version": "2023-10-16",
        "created": int(time.time()),
        "livemode": False,
        "pending_webhooks": 0,
        "request": {"id": None, "idempotency_key": None},
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_mvp",
                "customer": "cus_mvp_pro",
                "status": "active",
                "current_period_end": int(time.time()) + 10_000,
            }
        },
    }
    raw = __import__("json").dumps(up_event).encode("utf-8")
    sig = stripe_signature_header(payload=raw, secret=get_settings().stripe_webhook_secret)
    wh = client.post("/api/billing/webhook", content=raw, headers={"stripe-signature": sig})
    assert wh.status_code == 200

    me2 = client.get("/api/access/me")
    body = me2.json()
    assert body["access_tier"] == "pro"
    assert body["fix_mode_allowed"] is True
    assert body["supporting_files_allowed"] is True

    docx = minimal_docx_bytes()
    r_fix = client.post(
        "/api/jobs",
        files=[("main_document", ("m.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        data={"output_mode": "fix", "review_focus": "standard"},
    )
    assert r_fix.status_code == 200, r_fix.text
    job_fix = r_fix.json()["job"]["id"]
    for _ in range(80):
        g = client.get(f"/api/jobs/{job_fix}")
        if g.json()["status"] == "completed":
            break
        time.sleep(0.05)
    arts_fix = client.get(f"/api/jobs/{job_fix}/artifacts").json()["artifacts"]
    assert "corrected.docx" in {a["name"] for a in arts_fix}

    r_ev = client.post(
        "/api/jobs",
        files=[
            ("main_document", ("m.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("supporting_files", ("evidence.txt", b"particle physics alpha beta", "text/plain")),
        ],
        data={"output_mode": "review", "review_focus": "standard"},
    )
    assert r_ev.status_code == 200, r_ev.text
    job_ev = r_ev.json()["job"]["id"]
    for _ in range(80):
        g = client.get(f"/api/jobs/{job_ev}")
        if g.json()["status"] == "completed":
            break
        time.sleep(0.05)
    arts_ev = client.get(f"/api/jobs/{job_ev}/artifacts").json()["artifacts"]
    assert "evidence_snippets.md" in {a["name"] for a in arts_ev}

    down = {
        "id": "evt_sub_down",
        "object": "event",
        "api_version": "2023-10-16",
        "created": int(time.time()),
        "livemode": False,
        "pending_webhooks": 0,
        "request": {"id": None, "idempotency_key": None},
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_mvp",
                "customer": "cus_mvp_pro",
                "status": "canceled",
                "current_period_end": int(time.time()),
            }
        },
    }
    raw2 = __import__("json").dumps(down).encode("utf-8")
    sig2 = stripe_signature_header(payload=raw2, secret=get_settings().stripe_webhook_secret)
    wh2 = client.post("/api/billing/webhook", content=raw2, headers={"stripe-signature": sig2})
    assert wh2.status_code == 200

    me3 = client.get("/api/access/me")
    assert me3.json()["access_tier"] == "free"

    r_fix2 = client.post(
        "/api/jobs",
        files=[("main_document", ("m.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        data={"output_mode": "fix", "review_focus": "standard"},
    )
    assert r_fix2.status_code == 403
