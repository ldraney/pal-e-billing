import logging

import stripe
from fastapi import APIRouter, Header, HTTPException, Request

from .config import settings
from .db import update_status_by_subscription, upsert_subscriber

logger = logging.getLogger(__name__)
router = APIRouter()


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

        upsert_subscriber(
            telegram_user_id=telegram_user_id,
            stripe_customer_id=session["customer"],
            stripe_subscription_id=session.get("subscription"),
            status="active",
        )
        logger.info("Subscriber activated: %s", telegram_user_id)

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
