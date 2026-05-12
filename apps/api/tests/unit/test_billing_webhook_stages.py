from __future__ import annotations

import json
import time

from sqlalchemy import select

from draftlens_api.db import get_db_session
from draftlens_api.persistence.orm import BillingEvent, User, WebhookEvent
from draftlens_api.services.billing_service import BillingService


def test_webhook_signature_verification(api_env) -> None:
    client, _ = api_env
    r = client.post("/api/billing/webhook", data=b"{}", headers={"stripe-signature": "bad"})
    assert r.status_code == 400
    assert r.json()["detail"] == "invalid_signature"

    r2 = client.post("/api/billing/webhook", data=b"{}")
    assert r2.status_code == 400
    assert r2.json()["detail"] == "missing_signature"


def test_webhook_idempotency_on_duplicate_event(api_env) -> None:
    from draftlens_api.config import get_settings

    settings = get_settings()
    db = get_db_session()
    try:
        svc = BillingService(settings)
        evt = {
            "id": "evt_dup_1",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test",
                    "customer": "cus_test",
                    "status": "active",
                    "current_period_end": int(time.time()) + 3600,
                }
            },
        }
        u = User(email="bill@example.com", plan="free", stripe_customer_id="cus_test")
        db.add(u)
        db.commit()
        svc.process_stripe_event(db, evt)
        db.commit()
        svc.process_stripe_event(db, evt)
        db.commit()
        rows = list(db.execute(select(BillingEvent).where(BillingEvent.stripe_event_id == "evt_dup_1")).scalars().all())
        assert len(rows) == 1
        wh = db.execute(select(WebhookEvent).where(WebhookEvent.stripe_event_id == "evt_dup_1")).scalar_one()
        assert wh.processed is True
    finally:
        db.close()


def test_webhook_marks_processed_flag(api_env) -> None:
    from draftlens_api.config import get_settings

    settings = get_settings()
    db = get_db_session()
    try:
        svc = BillingService(settings)
        evt = {
            "id": "evt_proc_1",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_x2",
                    "customer": "cus_x2",
                    "status": "canceled",
                    "current_period_end": int(time.time()),
                }
            },
        }
        u = User(email="bill2@example.com", plan="pro", stripe_customer_id="cus_x2")
        db.add(u)
        db.commit()
        svc.process_stripe_event(db, evt)
        db.commit()
        wh = db.execute(select(WebhookEvent).where(WebhookEvent.stripe_event_id == "evt_proc_1")).scalar_one()
        assert wh.processed is True
    finally:
        db.close()


def test_status_stage_order_monotonic() -> None:
    from draftlens_api.engine.status_stage_order import assert_monotonic_stage_sequence, validate_monotonic_stage_sequence

    good = [
        "UPLOAD_RECEIVED",
        "DOC_PARSED",
        "CHUNKING_COMPLETE",
        "MODEL_REVIEW_GPT_STARTED",
        "MODEL_REVIEW_CLAUDE_STARTED",
        "EXPORT_COMPLETE",
        "completed",
    ]
    assert_monotonic_stage_sequence(good)

    bad = ["UPLOAD_RECEIVED", "EXPORT_COMPLETE", "DOC_PARSED"]
    ok, err = validate_monotonic_stage_sequence(bad)
    assert ok is False
    assert err is not None


def test_signed_webhook_route_accepted(api_env) -> None:
    from draftlens_api.config import get_settings
    from tests.conftest import stripe_signature_header

    client, _ = api_env
    db = get_db_session()
    try:
        u = User(email="hookroute@example.com", plan="free", stripe_customer_id="cus_route")
        db.add(u)
        db.commit()
        uid = u.id
    finally:
        db.close()

    payload = {
        "id": "evt_route_ok",
        "object": "event",
        "api_version": "2023-10-16",
        "created": int(time.time()),
        "livemode": False,
        "pending_webhooks": 0,
        "request": {"id": None, "idempotency_key": None},
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_route",
                "customer": "cus_route",
                "status": "active",
                "current_period_end": int(time.time()) + 7200,
            }
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    secret = get_settings().stripe_webhook_secret
    sig = stripe_signature_header(payload=raw, secret=secret)

    r = client.post("/api/billing/webhook", content=raw, headers={"stripe-signature": sig})
    assert r.status_code == 200
    assert r.json()["received"] is True

    db2 = get_db_session()
    try:
        u2 = db2.get(User, uid)
        assert u2 is not None
        assert u2.plan == "pro"
    finally:
        db2.close()
