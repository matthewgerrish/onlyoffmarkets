"""User membership persistence.

  user_memberships     One row per user_id. Active plan + Stripe ids.

The Stripe customer / subscription columns stay optional so the
mock-checkout path (no STRIPE_SECRET_KEY) writes the same shape.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from storage.off_market_db import _conn, _ph

log = logging.getLogger(__name__)


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_memberships (
    user_id              TEXT PRIMARY KEY,
    plan                 TEXT NOT NULL DEFAULT 'free',
    status               TEXT NOT NULL DEFAULT 'active',
    stripe_customer_id   TEXT,
    stripe_subscription_id TEXT,
    current_period_end   TEXT,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    started_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS user_memberships_sub_idx
    ON user_memberships(stripe_subscription_id);
"""

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_memberships (
    user_id              TEXT PRIMARY KEY,
    plan                 TEXT NOT NULL DEFAULT 'free',
    status               TEXT NOT NULL DEFAULT 'active',
    stripe_customer_id   TEXT,
    stripe_subscription_id TEXT,
    current_period_end   TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    started_at           TIMESTAMPTZ NOT NULL,
    updated_at           TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS user_memberships_sub_idx
    ON user_memberships(stripe_subscription_id);
"""


def _ensure(cur, dialect: str) -> None:
    if dialect == "pg":
        cur.execute(_PG_SCHEMA)
    else:
        cur.executescript(_SQLITE_SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: Any) -> dict:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    cols = [
        "user_id", "plan", "status", "stripe_customer_id", "stripe_subscription_id",
        "current_period_end", "cancel_at_period_end", "started_at", "updated_at",
    ]
    return dict(zip(cols, row))


def get(user_id: str) -> dict:
    """Return the user's membership row. Defaults to a Free plan if missing."""
    if not user_id:
        return {"plan": "free", "status": "active"}
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(f"SELECT * FROM user_memberships WHERE user_id = {ph}", (user_id,))
        row = cur.fetchone()
        if not row:
            return {"plan": "free", "status": "active"}
        d = _row_to_dict(row)
        # Stringify timestamps for JSON-friendly responses.
        if d.get("current_period_end") and not isinstance(d["current_period_end"], str):
            d["current_period_end"] = str(d["current_period_end"])
        if d.get("started_at") and not isinstance(d["started_at"], str):
            d["started_at"] = str(d["started_at"])
        return d


def set_plan(
    user_id: str,
    plan: str,
    *,
    status: str = "active",
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    current_period_end: str | None = None,
    cancel_at_period_end: bool = False,
) -> dict:
    """Upsert the user's plan. Used by Stripe webhook + mock checkout."""
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(f"SELECT user_id FROM user_memberships WHERE user_id = {ph}", (user_id,))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(
                f"""
                UPDATE user_memberships SET
                  plan = {ph}, status = {ph},
                  stripe_customer_id = COALESCE({ph}, stripe_customer_id),
                  stripe_subscription_id = COALESCE({ph}, stripe_subscription_id),
                  current_period_end = COALESCE({ph}, current_period_end),
                  cancel_at_period_end = {ph},
                  updated_at = {ph}
                WHERE user_id = {ph}
                """,
                (
                    plan, status,
                    stripe_customer_id, stripe_subscription_id, current_period_end,
                    bool(cancel_at_period_end) if dialect == "pg" else (1 if cancel_at_period_end else 0),
                    _now(),
                    user_id,
                ),
            )
        else:
            cur.execute(
                f"""
                INSERT INTO user_memberships (
                  user_id, plan, status, stripe_customer_id, stripe_subscription_id,
                  current_period_end, cancel_at_period_end, started_at, updated_at
                ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (
                    user_id, plan, status,
                    stripe_customer_id, stripe_subscription_id, current_period_end,
                    bool(cancel_at_period_end) if dialect == "pg" else (1 if cancel_at_period_end else 0),
                    _now(), _now(),
                ),
            )
    return get(user_id)


def set_by_subscription_id(
    stripe_subscription_id: str,
    plan: str,
    *,
    status: str,
    current_period_end: str | None = None,
    cancel_at_period_end: bool = False,
) -> bool:
    """Resolve a webhook event by subscription id (when we don't have user_id)."""
    if not stripe_subscription_id:
        return False
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(
            f"""
            UPDATE user_memberships SET
              plan = {ph}, status = {ph},
              current_period_end = COALESCE({ph}, current_period_end),
              cancel_at_period_end = {ph},
              updated_at = {ph}
            WHERE stripe_subscription_id = {ph}
            """,
            (
                plan, status, current_period_end,
                bool(cancel_at_period_end) if dialect == "pg" else (1 if cancel_at_period_end else 0),
                _now(), stripe_subscription_id,
            ),
        )
        return cur.rowcount > 0
