import logging

import stripe
import uvicorn
from fastapi import FastAPI

from .config import settings
from .db import get_subscriber, init_db
from .portal import router as portal_router
from .stripe_webhook import router as webhook_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="pal-e-billing")

stripe.api_key = settings.stripe_api_key

app.include_router(webhook_router)
app.include_router(portal_router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status/{telegram_user_id}")
async def subscription_status(telegram_user_id: str):
    subscriber = get_subscriber(telegram_user_id)
    if not subscriber:
        return {"is_active": False, "status": "none"}
    return {
        "is_active": subscriber["status"] == "active",
        "status": subscriber["status"],
    }


def cli():
    uvicorn.run(
        "pal_e_billing.main:app",
        host=settings.host,
        port=settings.port,
    )
