"""User identity persistence.

Single source of truth for who someone is. Keyed by an opaque
`user_id` string (we use the lowercase email for sign-in users so the
schema is human-readable, and a UUID for legacy localStorage users).

Relationships:
  - user_memberships.user_id  → users.id
  - user_tokens.user_id       → users.id
  - token_transactions.user_id
  - skip_trace_usage.user_id

When a magic-link sign-in matches a user_id that already has data
under a different localStorage UUID, we run `migrate_user_id()` to
rewrite the foreign keys so the wallet + plan move with the email.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from storage.off_market_db import _conn, _ph

log = logging.getLogger(__name__)


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    email        TEXT UNIQUE,
    created_at   TEXT NOT NULL,
    last_login   TEXT
);
CREATE INDEX IF NOT EXISTS users_email_idx ON users(email);
"""

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    email        TEXT UNIQUE,
    created_at   TIMESTAMPTZ NOT NULL,
    last_login   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS users_email_idx ON users(email);
"""


def _ensure(cur, dialect: str) -> None:
    if dialect == "pg":
        cur.execute(_PG_SCHEMA)
    else:
        cur.executescript(_SQLITE_SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: Any) -> dict | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    cols = ["id", "email", "created_at", "last_login"]
    return dict(zip(cols, row))


def get_by_email(email: str) -> dict | None:
    if not email:
        return None
    email = email.strip().lower()
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(f"SELECT id, email, created_at, last_login FROM users WHERE email = {ph}", (email,))
        return _row_to_dict(cur.fetchone())


def get_by_id(user_id: str) -> dict | None:
    if not user_id:
        return None
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(f"SELECT id, email, created_at, last_login FROM users WHERE id = {ph}", (user_id,))
        return _row_to_dict(cur.fetchone())


def upsert_by_email(email: str) -> dict:
    """Find or create a user keyed by email. Returns the canonical row."""
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("invalid email")
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(f"SELECT id, email, created_at, last_login FROM users WHERE email = {ph}", (email,))
        existing = _row_to_dict(cur.fetchone())
        if existing:
            cur.execute(f"UPDATE users SET last_login = {ph} WHERE id = {ph}", (_now(), existing["id"]))
            existing["last_login"] = _now()
            return existing
        # Use the email as the canonical id — short, stable, human-readable.
        new_id = email
        cur.execute(
            f"INSERT INTO users (id, email, created_at, last_login) VALUES ({ph}, {ph}, {ph}, {ph})",
            (new_id, email, _now(), _now()),
        )
        return {"id": new_id, "email": email, "created_at": _now(), "last_login": _now()}


def ensure_anon(user_id: str) -> dict:
    """Make sure an anonymous (UUID-based) user exists in the users table.

    Frontend hits this implicitly when a localStorage UUID first calls
    /tokens/balance — keeps row referential integrity for future joins.
    Idempotent: returns the existing row when present.
    """
    if not user_id:
        raise ValueError("user_id required")
    existing = get_by_id(user_id)
    if existing:
        return existing
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        try:
            cur.execute(
                f"INSERT INTO users (id, email, created_at, last_login) VALUES ({ph}, NULL, {ph}, NULL)",
                (user_id, _now()),
            )
        except Exception:
            # Concurrent insert — fine, just re-read.
            pass
    return get_by_id(user_id) or {"id": user_id, "email": None, "created_at": _now(), "last_login": None}


# ----------------------- migration ----------------------------------------

_MIGRATION_TARGETS: list[tuple[str, str]] = [
    ("user_memberships",   "user_id"),
    ("user_tokens",        "user_id"),
    ("token_transactions", "user_id"),
    ("skip_trace_usage",   "user_id"),
]


def migrate_user_id(old_id: str, new_id: str) -> int:
    """Rewrite all FKs from old_id → new_id. Returns total rows updated.

    Used when a localStorage user signs in with email for the first time:
    their UUID-keyed wallet + plan migrate to the email-keyed user.
    Resolves PK collisions on user_memberships / user_tokens by merging
    the rows (sum balances, prefer the most-recently-active membership).
    """
    if not old_id or not new_id or old_id == new_id:
        return 0
    total = 0
    with _conn() as (cur, dialect):
        ph = _ph(dialect)

        # 1) user_tokens — sum balances if both rows exist.
        try:
            cur.execute(f"SELECT balance, lifetime_purchased, lifetime_spent FROM user_tokens WHERE user_id = {ph}", (old_id,))
            old = cur.fetchone()
            if old:
                old_bal = int(old[0] if not isinstance(old, dict) else old["balance"])
                old_lp = int(old[1] if not isinstance(old, dict) else old["lifetime_purchased"])
                old_ls = int(old[2] if not isinstance(old, dict) else old["lifetime_spent"])
                cur.execute(f"SELECT balance, lifetime_purchased, lifetime_spent FROM user_tokens WHERE user_id = {ph}", (new_id,))
                new = cur.fetchone()
                if new:
                    new_bal = int(new[0] if not isinstance(new, dict) else new["balance"])
                    new_lp = int(new[1] if not isinstance(new, dict) else new["lifetime_purchased"])
                    new_ls = int(new[2] if not isinstance(new, dict) else new["lifetime_spent"])
                    cur.execute(
                        f"""UPDATE user_tokens SET balance = {ph},
                            lifetime_purchased = {ph}, lifetime_spent = {ph},
                            updated_at = {ph} WHERE user_id = {ph}""",
                        (new_bal + old_bal, new_lp + old_lp, new_ls + old_ls, _now(), new_id),
                    )
                    cur.execute(f"DELETE FROM user_tokens WHERE user_id = {ph}", (old_id,))
                else:
                    cur.execute(f"UPDATE user_tokens SET user_id = {ph} WHERE user_id = {ph}", (new_id, old_id))
                total += 1
        except Exception as exc:
            log.warning("migrate user_tokens failed: %s", exc)

        # 2) user_memberships — prefer the paid plan, drop the free one.
        try:
            cur.execute(f"SELECT plan, status FROM user_memberships WHERE user_id = {ph}", (old_id,))
            old = cur.fetchone()
            cur.execute(f"SELECT plan, status FROM user_memberships WHERE user_id = {ph}", (new_id,))
            new = cur.fetchone()
            if old and new:
                old_plan = old[0] if not isinstance(old, dict) else old["plan"]
                new_plan = new[0] if not isinstance(new, dict) else new["plan"]
                rank = {"free": 0, "standard": 1, "premium": 2}
                if rank.get(old_plan, 0) > rank.get(new_plan, 0):
                    # Promote to old plan, then delete the old row.
                    cur.execute(f"DELETE FROM user_memberships WHERE user_id = {ph}", (new_id,))
                    cur.execute(f"UPDATE user_memberships SET user_id = {ph} WHERE user_id = {ph}", (new_id, old_id))
                else:
                    cur.execute(f"DELETE FROM user_memberships WHERE user_id = {ph}", (old_id,))
            elif old and not new:
                cur.execute(f"UPDATE user_memberships SET user_id = {ph} WHERE user_id = {ph}", (new_id, old_id))
            total += 1
        except Exception as exc:
            log.warning("migrate user_memberships failed: %s", exc)

        # 3) Append-only ledger tables — straight rename.
        for table, col in (("token_transactions", "user_id"), ("skip_trace_usage", "user_id")):
            try:
                cur.execute(f"UPDATE {table} SET {col} = {ph} WHERE {col} = {ph}", (new_id, old_id))
                total += cur.rowcount or 0
            except Exception as exc:
                log.warning("migrate %s failed: %s", table, exc)

        # 4) Drop the legacy users row.
        try:
            cur.execute(f"DELETE FROM users WHERE id = {ph}", (old_id,))
        except Exception as exc:
            log.warning("delete legacy users row failed: %s", exc)

    log.info("migrated user %s → %s (%d affected rows)", old_id, new_id, total)
    return total
