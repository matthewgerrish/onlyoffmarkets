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
from storage.off_market_db import query as db_query, get_one

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

    # Source counts for the filter UI badges
    all_rows = db_query(state=state.upper() if state else None, county=county, limit=10_000)
    counts = {"all": len(all_rows)}
    for r in all_rows:
        for tag in r.get("source_tags") or []:
            counts[tag] = counts.get(tag, 0) + 1

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


@router.get("/{parcel_key}")
async def get_off_market(parcel_key: str) -> dict:
    row = get_one(parcel_key)
    if not row:
        raise HTTPException(status_code=404, detail="Property not found")
    return row
