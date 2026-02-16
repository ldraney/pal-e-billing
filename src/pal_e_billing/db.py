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

VALID_TIERS = {"base", "pro", "custom"}

# Columns added for tier support. ALTER TABLE ADD COLUMN is safe to
# retry — SQLite raises an error if the column already exists, which
# we deliberately ignore so init_db() stays idempotent.
_MIGRATIONS: list[str] = [
    "ALTER TABLE subscribers ADD COLUMN tier TEXT NOT NULL DEFAULT 'base'",
    "ALTER TABLE subscribers ADD COLUMN email TEXT",
    "ALTER TABLE subscribers ADD COLUMN gcal_gmail_status TEXT NOT NULL DEFAULT 'none'",
]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    with _get_conn() as conn:
        result = conn.execute("PRAGMA journal_mode=WAL").fetchone()
        if result[0] != "wal":
            logger.warning("Failed to set WAL mode, got: %s", result[0])
        conn.executescript(_SCHEMA)

        for stmt in _MIGRATIONS:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as exc:
                # "duplicate column name" is expected on subsequent runs.
                if "duplicate column" not in str(exc):
                    raise


def upsert_subscriber(
    telegram_user_id: str,
    stripe_customer_id: str,
    stripe_subscription_id: str | None,
    status: str = "active",
    tier: str = "base",
    email: str | None = None,
) -> None:
    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier '{tier}', must be one of {VALID_TIERS}")
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO subscribers
                (telegram_user_id, stripe_customer_id, stripe_subscription_id, status, tier, email)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_user_id) DO UPDATE SET
                stripe_customer_id = excluded.stripe_customer_id,
                stripe_subscription_id = COALESCE(excluded.stripe_subscription_id, stripe_subscription_id),
                status = excluded.status,
                tier = excluded.tier,
                email = COALESCE(excluded.email, subscribers.email),
                updated_at = datetime('now')
            """,
            (telegram_user_id, stripe_customer_id, stripe_subscription_id, status, tier, email),
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


_VALID_GCAL_GMAIL_STATUSES = {"none", "pending", "active"}


def update_gcal_gmail_status(telegram_user_id: str, gcal_gmail_status: str) -> bool:
    """Update gcal_gmail_status for a subscriber. Returns True if a row was updated."""
    if gcal_gmail_status not in _VALID_GCAL_GMAIL_STATUSES:
        raise ValueError(
            f"Invalid gcal_gmail_status '{gcal_gmail_status}', "
            f"must be one of {_VALID_GCAL_GMAIL_STATUSES}"
        )
    with _get_conn() as conn:
        cursor = conn.execute(
            "UPDATE subscribers SET gcal_gmail_status = ?, updated_at = datetime('now') WHERE telegram_user_id = ?",
            (gcal_gmail_status, telegram_user_id),
        )
        if cursor.rowcount == 0:
            logger.warning(
                "update_gcal_gmail_status: no rows matched telegram_user_id=%s",
                telegram_user_id,
            )
            return False
        return True
