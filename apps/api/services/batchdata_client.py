"""BatchData property-search client.

We already pay BatchData for skip-trace (services/skip_trace_providers.py).
The same key works for their /api/v1/property/search endpoint, which
exposes:

  * Pre-foreclosure NOD/NTS lists by state/county/zip
  * Tax-default
  * Vacant + absentee
  * Liens (mechanics + tax + judgment)
  * High equity
  * Auction sale-date filings

Why we add this on top of PropertyRadar:
  - BatchData includes skip-trace metadata in the same row, so a single
    record gives us address + owner phone/email *and* the distress flag.
  - Bulk-friendly: 1000 records per call, 10k/min throughput.
  - We already pay for it — marginal cost is zero.

Set env (already set if BatchData skip-trace is enabled):
  BATCHDATA_API_KEY=batch_xxx
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

API_KEY = os.environ.get("BATCHDATA_API_KEY")
SEARCH_URL = os.environ.get(
    "BATCHDATA_SEARCH_URL",
    "https://api.batchdata.com/api/v1/property/search",
)
HTTP_TIMEOUT = 30.0


def is_live() -> bool:
    return bool(API_KEY)


# ---- Pre-built filter blocks --------------------------------------------

FILTER_PREFORECLOSURE = {"foreclosure": {"any": ["nod", "lis_pendens"]}}
FILTER_AUCTION = {"foreclosure": {"any": ["nts", "auction"]}}
FILTER_TAX_DEFAULT = {"taxDelinquent": True}
FILTER_VACANT = {"vacant": True}
FILTER_ABSENTEE = {"ownerOccupied": False}
FILTER_HIGH_EQUITY = {"equityPercent": {"min": 50}, "yearsOwned": {"min": 5}}


async def search(
    filter_block: dict[str, Any],
    *,
    states: list[str] | None = None,
    page: int = 1,
    take: int = 1000,
) -> list[dict[str, Any]]:
    """POST a property search. Returns a list of property records.

    Records include `address`, `owner`, `valuation`, `mortgage`,
    `foreclosure`, `vacancy`, `taxes`, plus full lat/lng + APN.
    """
    if not is_live():
        return []
    body: dict[str, Any] = {
        "searchCriteria": filter_block,
        "options": {"page": page, "take": min(int(take), 1000)},
    }
    if states:
        body["searchCriteria"] = {**filter_block, "address": {"state": {"any": states}}}

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as cx:
            r = await cx.post(
                SEARCH_URL,
                json=body,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            if r.status_code == 401:
                log.error("BatchData 401 — bad key")
                return []
            if r.status_code == 429:
                log.warning("BatchData rate-limited")
                return []
            r.raise_for_status()
            data = r.json()
            return (
                data.get("results")
                or data.get("properties")
                or data.get("data")
                or []
            )
    except Exception as exc:
        log.warning("BatchData search failed: %s", exc)
        return []
