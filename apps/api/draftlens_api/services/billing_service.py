from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import stripe
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from draftlens_api.config import Settings
from draftlens_api.persistence.orm import BillingEvent, Entitlement, Subscription, User, WebhookEvent

logger = logging.getLogger(__name__)

PRO_ACCESS_STATUSES = frozenset({"active", "trialing", "past_due"})


def _stripe_obj_to_dict(obj: Any) -> dict:
    if isinstance(obj, dict):
        return obj
    fn = getattr(obj, "to_dict", None)
    if callable(fn):
        try:
            return fn()
        except Exception:  # noqa: BLE001
            pass
    try:
        return dict(obj)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return {}


def _dt_from_unix(ts: Any) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


class BillingService:
    """Stripe operations, customer lifecycle, webhooks (source of truth), and billing audit."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if settings.stripe_secret_key:
            stripe.api_key = settings.stripe_secret_key

    def require_stripe(self) -> None:
        if not self._settings.stripe_secret_key:
            raise HTTPException(status_code=503, detail="stripe_not_configured")

    def ensure_stripe_customer(self, db: Session, user: User) -> str:
        """Create Stripe Customer on first qualifying interaction (e.g. Checkout)."""
        self.require_stripe()
        if user.stripe_customer_id:
            return user.stripe_customer_id
        cust = stripe.Customer.create(
            email=user.email,
            metadata={"draftlens_user_id": user.id},
        )
        cid = str(cust.get("id") or "")
        if not cid:
            raise HTTPException(status_code=502, detail="stripe_customer_create_failed")
        user.stripe_customer_id = cid
        db.flush()
        return cid

    def create_checkout_session(
        self, db: Session, *, user: User, success_url: str | None, cancel_url: str | None
    ) -> str:
        self.require_stripe()
        if not self._settings.stripe_price_id_pro_monthly:
            raise HTTPException(status_code=503, detail="stripe_price_not_configured")
        customer_id = self.ensure_stripe_customer(db, user)
        kwargs: dict[str, Any] = {
            "mode": "subscription",
            "customer": customer_id,
            "client_reference_id": user.id,
            "success_url": success_url or self._settings.stripe_success_url,
            "cancel_url": cancel_url or self._settings.stripe_cancel_url,
            "line_items": [{"price": self._settings.stripe_price_id_pro_monthly, "quantity": 1}],
            "metadata": {"draftlens_user_id": user.id},
            "subscription_data": {
                "metadata": {"draftlens_user_id": user.id},
            },
            "allow_promotion_codes": True,
        }
        session_obj = stripe.checkout.Session.create(**kwargs)
        url = session_obj.get("url")
        if not isinstance(url, str):
            raise HTTPException(status_code=502, detail="stripe_no_url")
        return url

    def create_portal_session(self, db: Session, *, user: User, return_url: str | None) -> str:
        self.require_stripe()
        customer_id = self.ensure_stripe_customer(db, user)
        portal = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url or self._settings.next_public_app_url,
        )
        url = portal.get("url")
        if not isinstance(url, str):
            raise HTTPException(status_code=502, detail="stripe_no_url")
        return url

    def record_billing_event(
        self, db: Session, *, user_id: str | None, stripe_event_id: str, event_type: str, payload: dict
    ) -> None:
        exists = db.execute(
            select(BillingEvent).where(BillingEvent.stripe_event_id == stripe_event_id)
        ).scalar_one_or_none()
        if exists:
            return
        db.add(
            BillingEvent(
                user_id=user_id,
                stripe_event_id=stripe_event_id,
                event_type=event_type,
                payload=payload,
            )
        )
        db.flush()

    def _upsert_entitlement(self, db: Session, user_id: str, *, tier: str) -> None:
        ent = (
            db.execute(
                select(Entitlement)
                .where(Entitlement.user_id == user_id)
                .order_by(Entitlement.updated_at.desc())
            )
            .scalars()
            .first()
        )
        if ent:
            ent.tier = tier
            ent.source = "stripe"
        else:
            db.add(Entitlement(user_id=user_id, tier=tier, source="stripe"))
        db.flush()

    def upsert_subscription_row(
        self,
        db: Session,
        *,
        user_id: str,
        stripe_subscription_id: str,
        status: str,
        current_period_end: datetime | None,
        payload: dict | None,
    ) -> None:
        row = db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
        ).scalar_one_or_none()
        if row:
            row.user_id = user_id
            row.status = status
            row.current_period_end = current_period_end
            row.payload = payload
        else:
            db.add(
                Subscription(
                    user_id=user_id,
                    stripe_subscription_id=stripe_subscription_id,
                    status=status,
                    plan_code="pro_monthly",
                    current_period_end=current_period_end,
                    payload=payload,
                )
            )
        db.flush()

    def sync_user_and_entitlements_from_subscription(
        self,
        db: Session,
        *,
        user: User,
        stripe_subscription_id: str | None,
        status: str | None,
        current_period_end: datetime | None,
        payload: dict | None = None,
    ) -> None:
        st = str(status or "")
        paid = st in PRO_ACCESS_STATUSES
        user.plan = "pro" if paid else "free"
        user.billing_status = st or ("none" if not stripe_subscription_id else st)
        user.subscription_current_period_end = current_period_end if paid else None
        sid = str(stripe_subscription_id) if stripe_subscription_id else None
        if sid:
            self.upsert_subscription_row(
                db,
                user_id=user.id,
                stripe_subscription_id=sid,
                status=st or "unknown",
                current_period_end=current_period_end,
                payload=payload,
            )
        if paid and sid:
            user.stripe_subscription_id = sid
        else:
            user.stripe_subscription_id = None
        self._upsert_entitlement(db, user.id, tier="pro" if paid else "free")
        db.flush()

    def _user_by_stripe_customer(self, db: Session, customer_id: str | None) -> User | None:
        if not customer_id:
            return None
        return db.execute(select(User).where(User.stripe_customer_id == str(customer_id))).scalar_one_or_none()

    def _apply_subscription_object(self, db: Session, sub_obj: dict) -> str | None:
        customer_id = str(sub_obj.get("customer") or "")
        sub_id = str(sub_obj.get("id") or "")
        status = str(sub_obj.get("status") or "")
        period_end = _dt_from_unix(sub_obj.get("current_period_end"))
        user = self._user_by_stripe_customer(db, customer_id or None)
        if user is None:
            logger.warning("stripe subscription %s: no user for customer %s", sub_id, customer_id)
            return None
        self.sync_user_and_entitlements_from_subscription(
            db,
            user=user,
            stripe_subscription_id=sub_id or None,
            status=status,
            current_period_end=period_end,
            payload=sub_obj,
        )
        return user.id

    def process_stripe_event(self, db: Session, event: dict) -> None:
        eid = str(event.get("id", ""))
        etype = str(event.get("type", ""))
        data_object = (event.get("data") or {}).get("object") or {}

        if not eid:
            return

        existing_wh = db.execute(
            select(WebhookEvent).where(WebhookEvent.stripe_event_id == eid)
        ).scalar_one_or_none()
        if existing_wh and existing_wh.processed:
            return

        if existing_wh is None:
            try:
                with db.begin_nested():
                    db.add(WebhookEvent(stripe_event_id=eid, processed=False, payload=event))
                    db.flush()
            except IntegrityError:
                existing_wh = db.execute(
                    select(WebhookEvent).where(WebhookEvent.stripe_event_id == eid)
                ).scalar_one_or_none()
                if existing_wh and existing_wh.processed:
                    return
        else:
            existing_wh.payload = event

        user_id_for_log: str | None = None

        if etype == "checkout.session.completed":
            mode = str(data_object.get("mode") or "")
            if mode != "subscription":
                pass
            else:
                customer_id = data_object.get("customer")
                subscription_id = data_object.get("subscription")
                meta = data_object.get("metadata") or {}
                uid = meta.get("draftlens_user_id")
                user: User | None = None
                if uid:
                    user = db.get(User, str(uid))
                if user is None and customer_id:
                    user = self._user_by_stripe_customer(db, str(customer_id))
                if user is None:
                    email = data_object.get("customer_email") or (
                        (data_object.get("customer_details") or {}).get("email")
                    )
                    if email:
                        user = db.execute(
                            select(User).where(User.email == str(email).lower())
                        ).scalar_one_or_none()
                if user:
                    if customer_id:
                        user.stripe_customer_id = str(customer_id)
                    if subscription_id:
                        try:
                            sub_full = stripe.Subscription.retrieve(str(subscription_id))
                            sub_d = _stripe_obj_to_dict(sub_full)
                            user_id_for_log = self._apply_subscription_object(db, sub_d)
                        except Exception:  # noqa: BLE001
                            logger.exception("checkout.session.completed: could not load subscription")
                            user.stripe_subscription_id = str(subscription_id)
                            user.plan = "pro"
                            user.billing_status = "active"
                            user_id_for_log = user.id
                            self._upsert_entitlement(db, user.id, tier="pro")
                            self.upsert_subscription_row(
                                db,
                                user_id=user.id,
                                stripe_subscription_id=str(subscription_id),
                                status="active",
                                current_period_end=None,
                                payload={"source": "checkout.session.completed"},
                            )
                            db.flush()

        elif etype in {"customer.subscription.created", "customer.subscription.updated"}:
            user_id_for_log = self._apply_subscription_object(db, data_object)

        elif etype == "customer.subscription.deleted":
            user_id_for_log = self._apply_subscription_object(db, data_object)

        elif etype == "invoice.paid":
            customer_id = str(data_object.get("customer") or "")
            user = self._user_by_stripe_customer(db, customer_id)
            sub_ref = data_object.get("subscription")
            sid = str(sub_ref) if sub_ref else None
            if user and sid:
                try:
                    sub_full = stripe.Subscription.retrieve(sid)
                    sub_d = _stripe_obj_to_dict(sub_full)
                    user_id_for_log = self._apply_subscription_object(db, sub_d)
                except Exception:  # noqa: BLE001
                    logger.exception("invoice.paid: subscription retrieve failed")
                    user.billing_status = "active"
                    user_id_for_log = user.id
                    db.flush()

        elif etype == "invoice.payment_failed":
            customer_id = str(data_object.get("customer") or "")
            user = self._user_by_stripe_customer(db, customer_id)
            sub_ref = data_object.get("subscription")
            sid = str(sub_ref) if sub_ref else None
            if user and sid:
                try:
                    sub_full = stripe.Subscription.retrieve(sid)
                    sub_d = _stripe_obj_to_dict(sub_full)
                    user_id_for_log = self._apply_subscription_object(db, sub_d)
                except Exception:  # noqa: BLE001
                    logger.exception("invoice.payment_failed: subscription retrieve failed")
                    user.billing_status = "past_due"
                    user_id_for_log = user.id
                    db.flush()
            elif user:
                user.billing_status = "past_due"
                user_id_for_log = user.id
                db.flush()

        self.record_billing_event(
            db,
            user_id=user_id_for_log,
            stripe_event_id=eid,
            event_type=etype,
            payload=data_object if isinstance(data_object, dict) else {},
        )

        wh_final = db.execute(select(WebhookEvent).where(WebhookEvent.stripe_event_id == eid)).scalar_one_or_none()
        if wh_final:
            wh_final.processed = True
