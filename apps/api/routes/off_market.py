"""
Public read API for off-market signals.

Read-only — writes happen only from the nightly pipeline. Cached for
10 minutes per filter combination to absorb traffic spikes without
re-hitting SQLite/Postgres.

Two endpoints:
  GET /off-market               — paginated list with source counts
  GET /off-market/{parcel_key}  — single record with raw source log
"""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from cache import cache
from storage.off_market_db import query as db_query, get_one, source_counts

log = logging.getLogger(__name__)

router = APIRouter(prefix="/off-market", tags=["off-market"])


SOURCE_TYPES = Literal[
    "all", "preforeclosure", "auction", "fsbo", "tax-lien",
    "probate", "vacant", "reo", "canceled", "expired",
    "motivated_seller", "wholesale", "network",
]


@router.get("")
async def list_off_market(
    source: SOURCE_TYPES = "all",
    state: str | None = Query(None, min_length=2, max_length=2, description="Two-letter state code"),
    county: str | None = None,
    limit: int = Query(60, ge=1, le=300),
) -> dict:
    cache_key = f"off-market:list:{source}:{state or 'any'}:{county or 'any'}:{limit}"
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

    rows = db_query(
        state=state.upper() if state else None,
        county=county,
        source=None if source == "all" else source,
        limit=limit,
    )

    # Source counts via single grouped SQL query (was: pull 10k rows + Python loop)
    counts = source_counts(state=state.upper() if state else None, county=county)

    payload = {
        "results": rows,
        "counts": counts,
        "disclaimer": (
            "Records aggregated from public county recorder, treasurer, court, "
            "and assessor filings. Verify with the source before making offers."
        ),
    }
    await cache.set_json(cache_key, 600, payload)
    return payload


@router.get("/_/coverage")
async def coverage_summary() -> dict:
    """Public coverage summary — totals + state breakdown.

    Cheap (single grouped SQL query). No token. Used by the hero stats
    on the marketing site.
    """
    cached = await cache.get_json("off-market:coverage")
    if cached:
        return cached

    counts = source_counts()
    # Per-state breakdown via a separate single-pass query
    from storage.off_market_db import _conn, _ph
    with _conn() as (cur, dialect):
        cur.execute(
            "SELECT state, count(*) FROM off_market_listings WHERE state IS NOT NULL GROUP BY state ORDER BY count(*) DESC LIMIT 60"
        )
        states_rows = cur.fetchall()
    by_state = {}
    for row in states_rows:
        if dialect == "pg":
            by_state[row[0]] = row[1]
        else:
            by_state[row["state"]] = row["count(*)"]

    payload = {
        "total_parcels":  counts["all"],
        "by_source":      {k: v for k, v in counts.items() if k != "all"},
        "by_state":       by_state,
        "states_covered": len(by_state),
    }
    await cache.set_json("off-market:coverage", 600, payload)
    return payload


@router.get("/{parcel_key}")
async def get_off_market(parcel_key: str) -> dict:
    row = get_one(parcel_key)
    if not row:
        raise HTTPException(status_code=404, detail="Property not found")
    return row
