"""Token wallet storage.

Two tables:

  user_tokens          One row per user_id. Current balance.
  token_transactions   Append-only ledger. Every credit/debit lands here.
                       Balance = SUM(amount) per user.

`balance()` reads from the cached user_tokens row for speed; `_recalc()`
sums the ledger when something looks off.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from storage.off_market_db import _conn, _ph

log = logging.getLogger(__name__)


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_tokens (
    user_id     TEXT PRIMARY KEY,
    balance     INTEGER NOT NULL DEFAULT 0,
    lifetime_purchased INTEGER NOT NULL DEFAULT 0,
    lifetime_spent     INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS token_transactions (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    kind        TEXT NOT NULL,           -- purchase | spend | refund | grant
    amount      INTEGER NOT NULL,        -- positive for credit, negative for spend
    action_key  TEXT,                    -- e.g. skip_trace_pro, mailer_postcard
    parcel_key  TEXT,
    package_id  TEXT,
    note        TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS token_tx_user_idx ON token_transactions(user_id, created_at);
"""

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_tokens (
    user_id     TEXT PRIMARY KEY,
    balance     INTEGER NOT NULL DEFAULT 0,
    lifetime_purchased INTEGER NOT NULL DEFAULT 0,
    lifetime_spent     INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS token_transactions (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    kind        TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    action_key  TEXT,
    parcel_key  TEXT,
    package_id  TEXT,
    note        TEXT,
    created_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS token_tx_user_idx ON token_transactions(user_id, created_at);
"""


def _ensure(cur, dialect: str) -> None:
    if dialect == "pg":
        cur.execute(_PG_SCHEMA)
    else:
        cur.executescript(_SQLITE_SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def balance(user_id: str) -> int:
    """Return current balance for a user. Creates a fresh row at 0 if missing."""
    if not user_id:
        return 0
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(f"SELECT balance FROM user_tokens WHERE user_id = {ph}", (user_id,))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                f"INSERT INTO user_tokens (user_id, balance, lifetime_purchased, lifetime_spent, updated_at) "
                f"VALUES ({ph}, 0, 0, 0, {ph})",
                (user_id, _now()),
            )
            return 0
        return int(row[0] if not isinstance(row, dict) else row["balance"])


def summary(user_id: str) -> dict:
    if not user_id:
        return {"user_id": "", "balance": 0, "lifetime_purchased": 0, "lifetime_spent": 0}
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(
            f"SELECT balance, lifetime_purchased, lifetime_spent FROM user_tokens WHERE user_id = {ph}",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return {"user_id": user_id, "balance": 0, "lifetime_purchased": 0, "lifetime_spent": 0}
        bal, lp, ls = (row[0], row[1], row[2]) if not isinstance(row, dict) else (row["balance"], row["lifetime_purchased"], row["lifetime_spent"])
        return {
            "user_id": user_id,
            "balance": int(bal),
            "lifetime_purchased": int(lp),
            "lifetime_spent": int(ls),
        }


def credit(
    user_id: str,
    tokens: int,
    *,
    kind: str = "purchase",
    package_id: str | None = None,
    note: str | None = None,
) -> int:
    """Add tokens to a user. Returns new balance."""
    if tokens <= 0:
        raise ValueError("tokens must be positive")
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        # Upsert balance row
        cur.execute(f"SELECT balance FROM user_tokens WHERE user_id = {ph}", (user_id,))
        row = cur.fetchone()
        if row is None:
            new_bal = tokens
            cur.execute(
                f"INSERT INTO user_tokens (user_id, balance, lifetime_purchased, lifetime_spent, updated_at) "
                f"VALUES ({ph}, {ph}, {ph}, 0, {ph})",
                (user_id, new_bal, tokens if kind == "purchase" else 0, _now()),
            )
        else:
            cur.execute(
                f"UPDATE user_tokens SET balance = balance + {ph}, "
                f"lifetime_purchased = lifetime_purchased + {ph}, updated_at = {ph} "
                f"WHERE user_id = {ph}",
                (tokens, tokens if kind == "purchase" else 0, _now(), user_id),
            )
            cur.execute(f"SELECT balance FROM user_tokens WHERE user_id = {ph}", (user_id,))
            new_bal = int(cur.fetchone()[0])
        # Append ledger
        cur.execute(
            f"INSERT INTO token_transactions (id, user_id, kind, amount, package_id, note, created_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            ("tx_" + uuid.uuid4().hex[:12], user_id, kind, int(tokens), package_id, note, _now()),
        )
        return new_bal


def debit(
    user_id: str,
    tokens: int,
    *,
    action_key: str,
    parcel_key: str | None = None,
    note: str | None = None,
) -> tuple[bool, int]:
    """Spend tokens atomically. Returns (success, balance_after).

    Refuses to overdraft; on insufficient funds returns (False, current_balance).
    """
    if tokens <= 0:
        raise ValueError("tokens must be positive")
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        # Lock row in pg; sqlite serial connections give us atomicity for free.
        if dialect == "pg":
            cur.execute(
                f"SELECT balance FROM user_tokens WHERE user_id = {ph} FOR UPDATE",
                (user_id,),
            )
        else:
            cur.execute(f"SELECT balance FROM user_tokens WHERE user_id = {ph}", (user_id,))
        row = cur.fetchone()
        cur_bal = int(row[0]) if row else 0
        if cur_bal < tokens:
            # No row created — debit failed. Caller should prompt purchase.
            return (False, cur_bal)

        new_bal = cur_bal - tokens
        cur.execute(
            f"UPDATE user_tokens SET balance = {ph}, lifetime_spent = lifetime_spent + {ph}, "
            f"updated_at = {ph} WHERE user_id = {ph}",
            (new_bal, tokens, _now(), user_id),
        )
        cur.execute(
            f"INSERT INTO token_transactions (id, user_id, kind, amount, action_key, parcel_key, note, created_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            ("tx_" + uuid.uuid4().hex[:12], user_id, "spend", -int(tokens), action_key, parcel_key, note, _now()),
        )
        return (True, new_bal)


def refund(user_id: str, tokens: int, *, action_key: str, note: str | None = None) -> int:
    """Refund a previously debited amount (e.g. provider call hard-failed)."""
    if tokens <= 0:
        return balance(user_id)
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(
            f"UPDATE user_tokens SET balance = balance + {ph}, "
            f"lifetime_spent = lifetime_spent - {ph}, updated_at = {ph} WHERE user_id = {ph}",
            (tokens, tokens, _now(), user_id),
        )
        cur.execute(f"SELECT balance FROM user_tokens WHERE user_id = {ph}", (user_id,))
        row = cur.fetchone()
        new_bal = int(row[0]) if row else 0
        cur.execute(
            f"INSERT INTO token_transactions (id, user_id, kind, amount, action_key, note, created_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            ("tx_" + uuid.uuid4().hex[:12], user_id, "refund", int(tokens), action_key, note, _now()),
        )
        return new_bal


def transactions(user_id: str, limit: int = 50) -> list[dict]:
    if not user_id:
        return []
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(
            f"""
            SELECT id, kind, amount, action_key, parcel_key, package_id, note, created_at
            FROM token_transactions
            WHERE user_id = {ph}
            ORDER BY created_at DESC
            LIMIT {ph}
            """,
            (user_id, int(limit)),
        )
        rows = cur.fetchall() or []
        out = []
        for r in rows:
            d = dict(r) if isinstance(r, dict) else {
                "id": r[0], "kind": r[1], "amount": r[2], "action_key": r[3],
                "parcel_key": r[4], "package_id": r[5], "note": r[6], "created_at": r[7],
            }
            d["amount"] = int(d["amount"])
            d["created_at"] = str(d["created_at"]) if d.get("created_at") else None
            out.append(d)
        return out
