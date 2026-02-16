import logging
from contextlib import asynccontextmanager

import stripe
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Path

from .auth import require_api_key
from .config import settings
from .db import get_subscriber, init_db, update_gcal_gmail_status
from .portal import router as portal_router
from .stripe_webhook import router as webhook_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="pal-e-billing", lifespan=lifespan)

stripe.api_key = settings.stripe_api_key

app.include_router(webhook_router)
app.include_router(portal_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status/{telegram_user_id}")
def subscription_status(
    telegram_user_id: str = Path(pattern=r"^\d+$"),
    _key: str = Depends(require_api_key),
):
    subscriber = get_subscriber(telegram_user_id)
    if not subscriber:
        return {"is_active": False, "status": "none", "tier": None, "email": None, "gcal_gmail_status": "none"}
    return {
        "is_active": subscriber["status"] == "active",
        "status": subscriber["status"],
        "tier": subscriber["tier"],
        "email": subscriber["email"],
        "gcal_gmail_status": subscriber["gcal_gmail_status"],
    }


@app.put("/activate-gcal/{telegram_user_id}")
def activate_gcal(
    telegram_user_id: str = Path(pattern=r"^\d+$"),
    _key: str = Depends(require_api_key),
):
    subscriber = get_subscriber(telegram_user_id)
    if not subscriber:
        raise HTTPException(404, "No subscription found for this user")
    updated = update_gcal_gmail_status(telegram_user_id, "active")
    if not updated:
        raise HTTPException(500, "Failed to update gcal_gmail_status")
    return {"telegram_user_id": telegram_user_id, "gcal_gmail_status": "active"}


def cli():
    uvicorn.run(
        "pal_e_billing.main:app",
        host=settings.host,
        port=settings.port,
    )
