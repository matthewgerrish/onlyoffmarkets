"""Per-user / per-tier usage log for skip-trace lookups.

Writes one row per lookup so we can:
  - bill users at end of period
  - track margin (cost vs advertised) over time
  - detect runaway scripts hitting the endpoint

Schema is intentionally minimal — extend with `user_id` once auth ships.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from storage.off_market_db import _conn, _ph

log = logging.getLogger(__name__)


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS skip_trace_usage (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    parcel_key   TEXT NOT NULL,
    tier         TEXT NOT NULL,
    provider     TEXT NOT NULL,
    cost_usd     REAL NOT NULL,
    charged_usd  REAL NOT NULL,
    success      INTEGER NOT NULL,
    user_id      TEXT,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS skip_trace_usage_parcel_idx
    ON skip_trace_usage(parcel_key);
CREATE INDEX IF NOT EXISTS skip_trace_usage_user_idx
    ON skip_trace_usage(user_id, created_at);
"""

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS skip_trace_usage (
    id           BIGSERIAL PRIMARY KEY,
    parcel_key   TEXT NOT NULL,
    tier         TEXT NOT NULL,
    provider     TEXT NOT NULL,
    cost_usd     DOUBLE PRECISION NOT NULL,
    charged_usd  DOUBLE PRECISION NOT NULL,
    success      BOOLEAN NOT NULL,
    user_id      TEXT,
    created_at   TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS skip_trace_usage_parcel_idx
    ON skip_trace_usage(parcel_key);
CREATE INDEX IF NOT EXISTS skip_trace_usage_user_idx
    ON skip_trace_usage(user_id, created_at);
"""


def _ensure_table(cur, dialect: str) -> None:
    if dialect == "pg":
        cur.execute(_PG_SCHEMA)
    else:
        cur.executescript(_SQLITE_SCHEMA)


def record(
    parcel_key: str,
    tier: str,
    provider: str,
    cost_usd: float,
    charged_usd: float,
    success: bool,
    user_id: str | None = None,
) -> None:
    """Append a single usage row. Failures swallow + log — never block the lookup."""
    try:
        with _conn() as (cur, dialect):
            _ensure_table(cur, dialect)
            ph = _ph(dialect)
            cur.execute(
                f"""
                INSERT INTO skip_trace_usage
                  (parcel_key, tier, provider, cost_usd, charged_usd, success, user_id, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (
                    parcel_key,
                    tier,
                    provider,
                    float(cost_usd),
                    float(charged_usd),
                    bool(success) if dialect == "pg" else (1 if success else 0),
                    user_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
    except Exception as exc:  # pragma: no cover
        log.warning("usage_log.record failed: %s", exc)


def summary(user_id: str | None = None) -> dict:
    """Return aggregate spend + count for an optional user — used by /admin and /me."""
    try:
        with _conn() as (cur, dialect):
            _ensure_table(cur, dialect)
            ph = _ph(dialect)
            if user_id:
                cur.execute(
                    f"""
                    SELECT COUNT(*),
                           COALESCE(SUM(cost_usd), 0),
                           COALESCE(SUM(charged_usd), 0)
                    FROM skip_trace_usage
                    WHERE user_id = {ph}
                    """,
                    (user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*),
                           COALESCE(SUM(cost_usd), 0),
                           COALESCE(SUM(charged_usd), 0)
                    FROM skip_trace_usage
                    """
                )
            count, cost, charged = cur.fetchone() or (0, 0.0, 0.0)
            return {
                "count": int(count),
                "total_cost_usd": float(cost),
                "total_charged_usd": float(charged),
                "margin_usd": float(charged) - float(cost),
            }
    except Exception as exc:
        log.warning("usage_log.summary failed: %s", exc)
        return {"count": 0, "total_cost_usd": 0.0, "total_charged_usd": 0.0, "margin_usd": 0.0}
