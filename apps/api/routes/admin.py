"""Admin endpoints: trigger scrapers, check coverage, force schema upgrade.

All routes require ?token=<ADMIN_TOKEN> matching the env var to prevent
unauthorized scraping. When ADMIN_TOKEN is unset, routes are disabled.
"""
from __future__ import annotations

import json
import logging
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from scrapers.pipeline import SCRAPERS, run_one
from storage.off_market_db import _conn, _ph

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _check_token(token: Optional[str]) -> None:
    expected = os.environ.get("ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(503, detail="Admin endpoints disabled — ADMIN_TOKEN not configured")
    if token != expected:
        raise HTTPException(401, detail="Invalid admin token")


@router.get("/coverage")
async def coverage(token: str = Query(...)) -> dict:
    """Return what we've actually scraped so far — by state and by source."""
    _check_token(token)
    with _conn() as (cur, dialect):
        cur.execute(
            "SELECT state, count(*) FROM off_market_listings WHERE state IS NOT NULL GROUP BY state ORDER BY count(*) DESC"
        )
        by_state = {row[0] if dialect == "pg" else row["state"]:
                    row[1] if dialect == "pg" else row["count(*)"]
                    for row in cur.fetchall()}

        cur.execute(
            "SELECT source, count(*) FROM off_market_sources GROUP BY source ORDER BY count(*) DESC"
        )
        by_source = {row[0] if dialect == "pg" else row["source"]:
                     row[1] if dialect == "pg" else row["count(*)"]
                     for row in cur.fetchall()}

        cur.execute("SELECT count(*) FROM off_market_listings")
        total_parcels = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM off_market_sources")
        total_sources = cur.fetchone()[0]

    return {
        "total_parcels": total_parcels,
        "total_source_records": total_sources,
        "by_state": by_state,
        "by_source": by_source,
        "registered_scrapers": list(SCRAPERS.keys()),
    }


@router.post("/run")
async def run_pipeline(
    token: str = Query(...),
    sources: Optional[List[str]] = Query(default=None, description="Scraper slugs"),
) -> dict:
    """Trigger a one-off scrape. Long-running — typically 5–15 minutes."""
    _check_token(token)
    if not sources:
        sources = list(SCRAPERS.keys())

    results = []
    for slug in sources:
        cls = SCRAPERS.get(slug)
        if not cls:
            results.append({"slug": slug, "error": "unknown scraper"})
            continue
        log.info("admin/run: starting %s", slug)
        try:
            r = await run_one(slug, cls)
            results.append(r)
        except Exception as e:
            log.exception("admin/run: %s crashed", slug)
            results.append({"slug": slug, "error": str(e)[:200]})

    return {"results": results}
