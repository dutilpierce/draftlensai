from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from draftlens_api.config import get_settings
from draftlens_api.deps import get_db
from draftlens_api.models.schemas import (
    BillingCheckoutRequest,
    BillingCheckoutResponse,
    BillingPortalRequest,
    BillingPortalResponse,
)
from draftlens_api.persistence.orm import User
from draftlens_api.security.session import session_user_id_or_none
from draftlens_api.services.billing_service import BillingService

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger(__name__)


def _stripe_user(request: Request, db: Session) -> User:
    uid = session_user_id_or_none(request)
    if not uid:
        raise HTTPException(status_code=401, detail="not_signed_in")
    user = db.get(User, uid)
    if user is None:
        raise HTTPException(status_code=401, detail="not_signed_in")
    return user


@router.post("/checkout", response_model=BillingCheckoutResponse)
def billing_checkout(
    payload: BillingCheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    svc = BillingService(settings)
    user = _stripe_user(request, db)
    url = svc.create_checkout_session(
        db, user=user, success_url=payload.success_url, cancel_url=payload.cancel_url
    )
    return BillingCheckoutResponse(url=url)


@router.post("/portal", response_model=BillingPortalResponse)
def billing_portal(
    payload: BillingPortalRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    svc = BillingService(settings)
    user = _stripe_user(request, db)
    url = svc.create_portal_session(db, user=user, return_url=payload.return_url)
    return BillingPortalResponse(url=url)


@router.post("/webhook")
async def billing_webhook(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="stripe_webhook_not_configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    if not sig:
        raise HTTPException(status_code=400, detail="missing_signature")
    stripe.api_key = settings.stripe_secret_key
    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig, secret=settings.stripe_webhook_secret
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("stripe webhook verify failed: %s", exc)
        raise HTTPException(status_code=400, detail="invalid_signature") from exc

    event_dict = event.to_dict() if hasattr(event, "to_dict") else dict(event)
    BillingService(settings).process_stripe_event(db, event_dict)
    return {"received": True}
