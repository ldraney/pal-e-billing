import logging

import stripe
from fastapi import APIRouter, Header, HTTPException, Request

from .config import settings
from .db import VALID_TIERS, update_status_by_subscription, upsert_subscriber

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_tier(session: dict) -> str:
    """Derive the subscription tier from Stripe session metadata.

    Lookup order:
      1. ``session.metadata.tier`` (set on the Checkout Session)
      2. Falls back to ``'base'`` when no metadata is present.

    The actual mapping of Stripe price IDs to tiers is left to Stripe
    product/price metadata configuration done in the dashboard — this
    function simply reads whatever value the checkout flow provides.
    """
    metadata = session.get("metadata") or {}
    tier = metadata.get("tier", "base")
    if tier not in VALID_TIERS:
        logger.warning("Unknown tier '%s' in session metadata, defaulting to 'base'", tier)
        return "base"
    return tier


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="stripe-signature"),
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    event_type = event["type"]
    logger.info("Received Stripe event: %s", event_type)

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        telegram_user_id = session.get("client_reference_id")
        if not telegram_user_id:
            logger.warning("checkout.session.completed without client_reference_id")
            return {"status": "skipped", "reason": "missing client_reference_id"}

        tier = _extract_tier(session)
        customer_email = session.get("customer_details", {}).get("email")

        upsert_subscriber(
            telegram_user_id=telegram_user_id,
            stripe_customer_id=session["customer"],
            stripe_subscription_id=session.get("subscription"),
            status="active",
            tier=tier,
            email=customer_email,
        )
        logger.info("Subscriber activated: %s (tier=%s)", telegram_user_id, tier)

    elif event_type == "customer.subscription.updated":
        sub = event["data"]["object"]
        status = sub["status"]  # active, past_due, canceled, unpaid, etc.
        update_status_by_subscription(sub["id"], status)
        logger.info("Subscription %s updated to %s", sub["id"], status)

    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        update_status_by_subscription(sub["id"], "canceled")
        logger.info("Subscription %s canceled", sub["id"])

    else:
        logger.debug("Unhandled event type: %s", event_type)

    return {"status": "ok"}
