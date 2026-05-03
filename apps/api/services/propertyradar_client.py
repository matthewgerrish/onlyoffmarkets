"""PropertyRadar API client.

PropertyRadar is the single best paid source for nationwide off-market
distress signals — one API surface covers preforeclosure, auction,
tax-default, probate, vacant, absentee owners, high-equity owners
(150M+ properties).

Pricing (as of 2026):
  Starter   $199/mo  —  5,000 records/mo, all signals
  Pro       $299/mo  — 25,000 records/mo + lists + alerts
  Team      $499/mo  — 100k records, 5 seats

Auth:
  Bearer token (header: `Authorization: Bearer <PROPERTYRADAR_API_KEY>`)
  Pre-built lists discovered via /v1/lists.

Set on Fly:
  fly secrets set PROPERTYRADAR_API_KEY=pr_xxx -a onlyoffmarkets-api

Until the key lands, every method here returns an empty list — the
scraper sees zero leads and logs once instead of crashing.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Iterable

import httpx

log = logging.getLogger(__name__)

API_BASE = os.environ.get("PROPERTYRADAR_BASE_URL", "https://api.propertyradar.com").rstrip("/")
API_KEY  = os.environ.get("PROPERTYRADAR_API_KEY")
HTTP_TIMEOUT = 30.0


def is_live() -> bool:
    return bool(API_KEY)


def _headers() -> dict[str, str]:
    if not API_KEY:
        raise RuntimeError("PROPERTYRADAR_API_KEY not set")
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# ---- Signal-specific list builders --------------------------------------

# PropertyRadar exposes property quick-lists by criteria. Each scraper
# below uses the v1/properties search with the matching criteria array.
#
# Reference: https://www.propertyradar.com/api-reference

CRITERIA_PREFORECLOSURE = [
    {"name": "ForeclosureStage", "value": ["NOD", "NTS"]},
]
CRITERIA_AUCTION = [
    {"name": "ForeclosureStage", "value": ["Auction"]},
]
CRITERIA_TAX_DEFAULT = [
    {"name": "TaxDelinquentYear", "value": ["1+"]},
]
CRITERIA_PROBATE = [
    # PropertyRadar's "Probate" smart-list bucket
    {"name": "InProbate", "value": ["1"]},
]
CRITERIA_VACANT = [
    {"name": "Vacant", "value": ["1"]},
]
CRITERIA_ABSENTEE = [
    {"name": "OwnerOccupied", "value": ["0"]},
]
CRITERIA_HIGH_EQUITY = [
    # 50%+ equity AND owned 5+ years — classic seller pool
    {"name": "EquityPercent", "value": ["50:"]},
    {"name": "YearsOwned", "value": ["5:"]},
]


# ---- Search call --------------------------------------------------------

async def search_properties(
    criteria: list[dict[str, Any]],
    *,
    states: list[str] | None = None,
    limit: int = 1000,
    fields: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """POST /v1/properties.

    Returns a list of property dicts; each one has APN, address, city,
    state, zip, lat/lng, owner info, valuation, foreclosure stage, and
    distress signals — exact field names per PropertyRadar's API ref.
    """
    if not is_live():
        log.warning("PropertyRadar called without API key — returning empty")
        return []

    body = {"criteria": list(criteria)}
    if states:
        body["criteria"].append({"name": "State", "value": states})

    params: dict[str, str] = {"limit": str(min(int(limit), 5000))}
    if fields:
        params["fields"] = ",".join(fields)

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as cx:
            r = await cx.post(
                f"{API_BASE}/v1/properties",
                json=body,
                params=params,
                headers=_headers(),
            )
            if r.status_code == 401:
                log.error("PropertyRadar 401 — bad API key. Run `fly secrets set PROPERTYRADAR_API_KEY=...`")
                return []
            if r.status_code == 429:
                log.warning("PropertyRadar rate-limited (monthly cap?). Skipping batch.")
                return []
            r.raise_for_status()
            data = r.json()
            return data.get("results") or data.get("properties") or data.get("data") or []
    except Exception as exc:
        log.warning("PropertyRadar fetch failed: %s", exc)
        return []
