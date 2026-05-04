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


def _headers(scheme: str = "bearer") -> dict[str, str]:
    """PropertyRadar accepts multiple auth schemes depending on the
    account / partner type. We try them in order — Bearer first
    (most common), then `Token`, then HTTP Basic with empty user."""
    if not API_KEY:
        raise RuntimeError("PROPERTYRADAR_API_KEY not set")
    base = {"Accept": "application/json", "Content-Type": "application/json"}
    if scheme == "bearer":
        base["Authorization"] = f"Bearer {API_KEY}"
    elif scheme == "token":
        base["Authorization"] = f"Token {API_KEY}"
    elif scheme == "apikey":
        base["X-API-Key"] = API_KEY
    elif scheme == "basic":
        import base64
        b = base64.b64encode(f":{API_KEY}".encode()).decode()
        base["Authorization"] = f"Basic {b}"
    return base


def key_shape() -> dict[str, Any]:
    """Diagnostic only — never returns the secret value."""
    k = API_KEY or ""
    return {
        "set": bool(k),
        "length": len(k),
        "prefix": k[:4] if k else "",
        "starts_with_pr_": k.startswith("pr_"),
        "has_whitespace": any(c.isspace() for c in k),
        "has_newline": "\n" in k or "\r" in k,
        "has_quotes": any(c in k for c in ('"', "'")),
        "has_non_ascii": any(ord(c) > 127 for c in k),
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

    # Try each auth scheme in turn — first 200 wins. PropertyRadar
    # mixes Bearer / Token / Basic / X-API-Key depending on tier.
    schemes = ["bearer", "token", "apikey", "basic"]
    last_status = 0
    last_body = ""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as cx:
            for scheme in schemes:
                r = await cx.post(
                    f"{API_BASE}/v1/properties",
                    json=body,
                    params=params,
                    headers=_headers(scheme),
                )
                last_status = r.status_code
                last_body = (r.text or "")[:300]
                if r.status_code == 200:
                    log.info("PropertyRadar auth OK via %s", scheme)
                    data = r.json()
                    return data.get("results") or data.get("properties") or data.get("data") or []
                if r.status_code == 429:
                    log.warning("PropertyRadar rate-limited (monthly cap?). Skipping batch.")
                    return []
                if r.status_code in (400, 422):
                    # Auth ok but request shape rejected — surface details + stop.
                    log.warning("PropertyRadar %d %s body=%s", r.status_code, scheme, last_body)
                    return []
                # 401/403 → try next scheme
        log.error(
            "PropertyRadar all auth schemes returned %d. Body: %s",
            last_status, last_body,
        )
        return []
    except Exception as exc:
        log.warning("PropertyRadar fetch failed: %s", exc)
        return []
