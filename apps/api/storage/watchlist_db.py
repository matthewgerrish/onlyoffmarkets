"""User watchlist — saved Recon results.

One row per (user_id, parcel_key). Captures the snapshot the user
saw when they saved (so the watchlist doesn't change retroactively
when our scoring formula evolves).

Schema:
  user_watchlist
    id           autoincrement / bigserial
    user_id      TEXT NOT NULL
    parcel_key   TEXT NOT NULL                    # APN if available, else slug
    address      TEXT NOT NULL
    city         TEXT
    state        TEXT
    zip          TEXT
    lat          REAL
    lng          REAL
    deal_score   INT
    deal_band    TEXT
    adu_score    INT
    adu_band     TEXT
    snapshot     TEXT  (JSON of the full analyzer result at save time)
    notes        TEXT
    saved_at     TIMESTAMPTZ NOT NULL
    UNIQUE(user_id, parcel_key)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from storage.off_market_db import _conn, _ph

log = logging.getLogger(__name__)


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_watchlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    parcel_key  TEXT NOT NULL,
    address     TEXT NOT NULL,
    city        TEXT,
    state       TEXT,
    zip         TEXT,
    lat         REAL,
    lng         REAL,
    deal_score  INTEGER,
    deal_band   TEXT,
    adu_score   INTEGER,
    adu_band    TEXT,
    snapshot    TEXT,
    notes       TEXT,
    saved_at    TEXT NOT NULL,
    UNIQUE(user_id, parcel_key)
);
CREATE INDEX IF NOT EXISTS user_watchlist_user_idx
    ON user_watchlist(user_id, saved_at DESC);
"""

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_watchlist (
    id          BIGSERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    parcel_key  TEXT NOT NULL,
    address     TEXT NOT NULL,
    city        TEXT,
    state       TEXT,
    zip         TEXT,
    lat         DOUBLE PRECISION,
    lng         DOUBLE PRECISION,
    deal_score  INTEGER,
    deal_band   TEXT,
    adu_score   INTEGER,
    adu_band    TEXT,
    snapshot    JSONB,
    notes       TEXT,
    saved_at    TIMESTAMPTZ NOT NULL,
    UNIQUE(user_id, parcel_key)
);
CREATE INDEX IF NOT EXISTS user_watchlist_user_idx
    ON user_watchlist(user_id, saved_at DESC);
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
        d = dict(row)
    else:
        cols = ["id","user_id","parcel_key","address","city","state","zip",
                "lat","lng","deal_score","deal_band","adu_score","adu_band",
                "snapshot","notes","saved_at"]
        d = dict(zip(cols, row))
    snap = d.get("snapshot")
    if isinstance(snap, str):
        try:
            d["snapshot"] = json.loads(snap)
        except Exception:
            d["snapshot"] = None
    if d.get("saved_at") and not isinstance(d["saved_at"], str):
        d["saved_at"] = str(d["saved_at"])
    return d


def save(
    user_id: str,
    *,
    parcel_key: str,
    address: str,
    city: str | None = None,
    state: str | None = None,
    zip_: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    deal_score: int | None = None,
    deal_band: str | None = None,
    adu_score: int | None = None,
    adu_band: str | None = None,
    snapshot: dict | None = None,
    notes: str | None = None,
) -> dict:
    """Upsert a watchlist entry. Returns the saved row."""
    if not user_id or not parcel_key or not address:
        raise ValueError("user_id, parcel_key, address required")
    snap_text = json.dumps(snapshot) if snapshot is not None else None
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        # Try to update first
        cur.execute(
            f"""SELECT id FROM user_watchlist
                WHERE user_id = {ph} AND parcel_key = {ph}""",
            (user_id, parcel_key),
        )
        existing = cur.fetchone()
        if existing:
            cur.execute(
                f"""UPDATE user_watchlist SET
                      address={ph}, city={ph}, state={ph}, zip={ph},
                      lat={ph}, lng={ph},
                      deal_score={ph}, deal_band={ph},
                      adu_score={ph}, adu_band={ph},
                      snapshot={ph}, notes=COALESCE({ph}, notes),
                      saved_at={ph}
                    WHERE user_id={ph} AND parcel_key={ph}""",
                (address, city, state, zip_, lat, lng,
                 deal_score, deal_band, adu_score, adu_band,
                 snap_text, notes, _now(), user_id, parcel_key),
            )
        else:
            cur.execute(
                f"""INSERT INTO user_watchlist
                    (user_id, parcel_key, address, city, state, zip,
                     lat, lng,
                     deal_score, deal_band, adu_score, adu_band,
                     snapshot, notes, saved_at)
                    VALUES ({ph},{ph},{ph},{ph},{ph},{ph},
                            {ph},{ph},{ph},{ph},{ph},{ph},
                            {ph},{ph},{ph})""",
                (user_id, parcel_key, address, city, state, zip_,
                 lat, lng,
                 deal_score, deal_band, adu_score, adu_band,
                 snap_text, notes, _now()),
            )
    log.info("watchlist saved %s/%s", user_id, parcel_key)
    return get(user_id, parcel_key) or {}


def get(user_id: str, parcel_key: str) -> dict | None:
    if not user_id or not parcel_key:
        return None
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(
            f"""SELECT id, user_id, parcel_key, address, city, state, zip,
                       lat, lng, deal_score, deal_band, adu_score, adu_band,
                       snapshot, notes, saved_at
                FROM user_watchlist
                WHERE user_id = {ph} AND parcel_key = {ph}""",
            (user_id, parcel_key),
        )
        return _row_to_dict(cur.fetchone())


def list_for(user_id: str, *, limit: int = 100) -> list[dict]:
    if not user_id:
        return []
    out: list[dict] = []
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(
            f"""SELECT id, user_id, parcel_key, address, city, state, zip,
                       lat, lng, deal_score, deal_band, adu_score, adu_band,
                       NULL as snapshot, notes, saved_at
                FROM user_watchlist
                WHERE user_id = {ph}
                ORDER BY saved_at DESC
                LIMIT {ph}""",
            (user_id, int(limit)),
        )
        for r in cur.fetchall() or []:
            d = _row_to_dict(r)
            if d:
                out.append(d)
    return out


def remove(user_id: str, parcel_key: str) -> bool:
    if not user_id or not parcel_key:
        return False
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(
            f"DELETE FROM user_watchlist WHERE user_id = {ph} AND parcel_key = {ph}",
            (user_id, parcel_key),
        )
        return (cur.rowcount or 0) > 0


def update_notes(user_id: str, parcel_key: str, notes: str) -> bool:
    with _conn() as (cur, dialect):
        _ensure(cur, dialect)
        ph = _ph(dialect)
        cur.execute(
            f"""UPDATE user_watchlist
                SET notes = {ph}
                WHERE user_id = {ph} AND parcel_key = {ph}""",
            (notes, user_id, parcel_key),
        )
        return (cur.rowcount or 0) > 0
