"""BatchData property-search client.

Now the *primary* paid source after the PropertyRadar pivot.

Endpoint families we use:
  * /api/v1/property/search        property + distress filters
  * /api/v1/property/skip-trace    skip-trace (used by services/skip_trace_providers.py)

BatchData runs sandbox + production environments on the SAME base host
but use different API tokens. Sandbox keys are typically prefixed
`batch_test_` or are flagged by their backend; production keys hit the
same URL and just bill you for real. To switch envs, change the key —
URL stays put.

Set on Fly:
  fly secrets set BATCHDATA_API_KEY=batch_test_xxx -a onlyoffmarkets-api  # sandbox
  fly secrets set BATCHDATA_API_KEY=batch_xxx -a onlyoffmarkets-api       # live

Optional override (only needed if BatchData splits hosts later):
  fly secrets set BATCHDATA_BASE_URL=https://api-sandbox.batchdata.com -a onlyoffmarkets-api
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

API_KEY = os.environ.get("BATCHDATA_API_KEY")
BASE_URL = os.environ.get("BATCHDATA_BASE_URL", "https://api.batchdata.com").rstrip("/")
SEARCH_URL = os.environ.get("BATCHDATA_SEARCH_URL", f"{BASE_URL}/api/v1/property/search")
HTTP_TIMEOUT = 30.0


def is_live() -> bool:
    return bool(API_KEY)


def is_sandbox() -> bool:
    """Heuristic — BatchData sandbox keys typically include 'test' or
    'sandbox' in the prefix. Used only for log breadcrumbs / UI hints."""
    if not API_KEY:
        return False
    head = API_KEY.lower()
    return "test" in head[:14] or "sandbox" in head[:14] or "sand" in head[:8]


def key_shape() -> dict[str, Any]:
    """Return SHAPE only — never the secret itself. Useful for confirming
    a copy-paste landed clean (no Cyrillic homoglyphs, no whitespace)."""
    k = API_KEY or ""
    return {
        "set": bool(k),
        "length": len(k),
        "prefix": k[:6] if k else "",
        "starts_with_batch_": k.startswith("batch_"),
        "looks_sandbox": is_sandbox(),
        "has_whitespace": any(c.isspace() for c in k),
        "has_newline": "\n" in k or "\r" in k,
        "has_quotes": any(c in k for c in ('"', "'")),
        "non_ascii": any(ord(c) > 127 for c in k),
        "base_url": BASE_URL,
        "search_url": SEARCH_URL,
    }


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

    env = "sandbox" if is_sandbox() else "live"
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
                log.error(
                    "BatchData 401 (%s key) — token rejected by %s. "
                    "Verify the key from BatchData Dashboard → Settings → API Keys. Body: %s",
                    env, SEARCH_URL, (r.text or "")[:200],
                )
                return []
            if r.status_code == 403:
                log.error(
                    "BatchData 403 (%s key) — token lacks /property/search permission. "
                    "Check your plan tier or upgrade the key scope. Body: %s",
                    env, (r.text or "")[:200],
                )
                return []
            if r.status_code == 429:
                log.warning("BatchData 429 (%s key) — per-min rate limit hit. Retrying later.", env)
                return []
            if r.status_code >= 400:
                log.warning(
                    "BatchData %d (%s key) on /property/search. Body: %s",
                    r.status_code, env, (r.text or "")[:300],
                )
                return []
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
