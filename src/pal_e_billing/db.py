import logging
import sqlite3
from pathlib import Path

from .config import settings

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS subscribers (
    telegram_user_id TEXT PRIMARY KEY,
    stripe_customer_id TEXT NOT NULL,
    stripe_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'inactive',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_stripe_customer ON subscribers(stripe_customer_id);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    with _get_conn() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)


def upsert_subscriber(
    telegram_user_id: str,
    stripe_customer_id: str,
    stripe_subscription_id: str | None,
    status: str = "active",
) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO subscribers (telegram_user_id, stripe_customer_id, stripe_subscription_id, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_user_id) DO UPDATE SET
                stripe_customer_id = excluded.stripe_customer_id,
                stripe_subscription_id = COALESCE(excluded.stripe_subscription_id, stripe_subscription_id),
                status = excluded.status,
                updated_at = datetime('now')
            """,
            (telegram_user_id, stripe_customer_id, stripe_subscription_id, status),
        )


def update_status_by_customer(stripe_customer_id: str, status: str) -> None:
    with _get_conn() as conn:
        cursor = conn.execute(
            "UPDATE subscribers SET status = ?, updated_at = datetime('now') WHERE stripe_customer_id = ?",
            (status, stripe_customer_id),
        )
        if cursor.rowcount == 0:
            logger.warning(
                "update_status_by_customer: no rows matched stripe_customer_id=%s",
                stripe_customer_id,
            )


def update_status_by_subscription(stripe_subscription_id: str, status: str) -> None:
    with _get_conn() as conn:
        cursor = conn.execute(
            "UPDATE subscribers SET status = ?, updated_at = datetime('now') WHERE stripe_subscription_id = ?",
            (status, stripe_subscription_id),
        )
        if cursor.rowcount == 0:
            logger.warning(
                "update_status_by_subscription: no rows matched stripe_subscription_id=%s",
                stripe_subscription_id,
            )


def get_subscriber(telegram_user_id: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM subscribers WHERE telegram_user_id = ?",
            (telegram_user_id,),
        ).fetchone()
    return dict(row) if row else None


def get_subscriber_by_customer(stripe_customer_id: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM subscribers WHERE stripe_customer_id = ?",
            (stripe_customer_id,),
        ).fetchone()
    return dict(row) if row else None
