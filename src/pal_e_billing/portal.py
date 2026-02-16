import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import RedirectResponse

from .auth import require_api_key
from .config import settings
from .db import get_subscriber

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/portal/{telegram_user_id}")
def customer_portal(
    telegram_user_id: str = Path(pattern=r"^\d+$"),
    _key: str = Depends(require_api_key),
):
    subscriber = get_subscriber(telegram_user_id)
    if not subscriber:
        raise HTTPException(404, "No subscription found for this user")

    session = stripe.billing_portal.Session.create(
        customer=subscriber["stripe_customer_id"],
        return_url=settings.portal_return_url,
    )

    return RedirectResponse(session.url)
