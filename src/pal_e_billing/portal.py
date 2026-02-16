import logging

import stripe
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from .config import settings
from .db import get_subscriber

logger = logging.getLogger(__name__)
router = APIRouter()

RETURN_URL = "https://t.me/personal_assistant_ldraney_bot"


@router.get("/portal/{telegram_user_id}")
async def customer_portal(telegram_user_id: str):
    subscriber = get_subscriber(telegram_user_id)
    if not subscriber:
        raise HTTPException(404, "No subscription found for this user")

    stripe.api_key = settings.stripe_api_key
    session = stripe.billing_portal.Session.create(
        customer=subscriber["stripe_customer_id"],
        return_url=RETURN_URL,
    )

    return RedirectResponse(session.url)
