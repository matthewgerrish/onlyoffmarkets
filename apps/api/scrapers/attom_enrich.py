"""
ATTOM enrichment layer — uses Property + Sales endpoints only.

Designed for an ATTOM subscription that does NOT yet include the
Foreclosure bundle. Fills three jobs that don't need that bundle:

  1. ENRICH county-scraped leads with authoritative parcel data
     (lot size, zoning, year built, recent sales history, assessed value).
  2. FIND absentee owners — parcels where the owner's mailing address
     differs from the property address. High-signal off-market lead type.
  3. PULL sales comps for the "Thinking of selling?" AI valuation on the
     home-value page.

Each function is independent — wire them into whichever part of the app
needs the data. The ATTOM Foreclosure scraper (`attom.py`) remains the
canonical feed for pre-foreclosure/auction/REO once that bundle is added.

Endpoints used (all confirmed live on the current key):

  /propertyapi/v1.0.0/property/basicprofile     — fast address → profile
  /propertyapi/v1.0.0/property/expandedprofile  — full parcel, owner, lot
  /propertyapi/v1.0.0/sale/snapshot             — recent sales in an area
"""
from __future__ import annotations

import logging
import os
from typing import AsyncIterable

import httpx

from config import settings
from scrapers.base import DEFAULT_USER_AGENT
from scrapers.models import RawLead

log = logging.getLogger(__name__)


BASE = os.getenv("ATTOM_BASE_URL", "https://api.gateway.attomdata.com")


def _client() -> httpx.AsyncClient:
    """One-shot async client preconfigured with auth headers."""
    return httpx.AsyncClient(
        timeout=20.0,
        headers={
            "apikey": settings.attom_api_key,
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        },
    )


# ---------- 1. Enrichment ----------

async def enrich_address(address1: str, address2: str) -> dict | None:
    """Given a street + 'City STATE' pair, return ATTOM's expanded parcel
    profile. Safe to call on every county-scraped lead to fill in the
    real lot size, zoning, year built, and owner info.

    `address1`: "4218 N Stevens St"
    `address2`: "Tacoma WA"
    """
    if not settings.attom_api_key:
        return None
    async with _client() as c:
        r = await c.get(
            f"{BASE}/propertyapi/v1.0.0/property/expandedprofile",
            params={"address1": address1, "address2": address2},
        )
    if r.status_code != 200:
        log.debug("ATTOM enrich %s — status %d", address1, r.status_code)
        return None
    data = r.json()
    props = data.get("property") or []
    return props[0] if props else None


# ---------- 2. Absentee owner detection ----------

async def find_absentee_by_zip(
    postal_code: str,
    page_size: int = 100,
    max_pages: int | None = None,
) -> AsyncIterable[RawLead]:
    """Stream absentee RawLeads for a ZIP.

    Uses ATTOM's built-in `assessment.owner.absenteeOwnerStatus` flag
    ('A' = absentee). No client-side address comparison needed.

    `max_pages` caps API spend per ZIP. Each page = 100 properties
    (default). Pass None to paginate through all results (can be
    100+ pages for large ZIPs).
    """
    if not settings.attom_api_key:
        return

    page = 1
    async with _client() as c:
        while True:
            if max_pages is not None and page > max_pages:
                return
            r = await c.get(
                f"{BASE}/propertyapi/v1.0.0/property/basicprofile",
                params={"postalcode": postal_code, "page": page, "pagesize": page_size},
            )
            if r.status_code != 200:
                log.warning("ATTOM basicprofile %s page %d — %d", postal_code, page, r.status_code)
                return
            data = r.json()
            props = data.get("property") or []
            if not props:
                return

            for p in props:
                lead = _maybe_absentee(p)
                if lead:
                    yield lead

            total = data.get("status", {}).get("total", 0)
            if page * page_size >= total:
                return
            page += 1


def _maybe_absentee(p: dict) -> RawLead | None:
    """Return a RawLead iff this property is absentee-owned.

    ATTOM's `basicprofile` response flags this directly via
    `assessment.owner.absenteeOwnerStatus`:
      O = Owner-occupied   → skip
      A = Absentee         → emit
      anything else        → skip (unknown)
    """
    owner = ((p.get("assessment") or {}).get("owner") or {})
    status = (owner.get("absenteeOwnerStatus") or "").upper().strip()
    if status != "A":
        return None

    prop_addr = (p.get("address") or {})
    mail_oneline = owner.get("mailingAddressOneLine") or ""

    # Parse state out of the owner's mailing one-line (last ", XX" before ZIP)
    import re
    m = re.search(r",\s*([A-Z]{2})\s+\d{5}", mail_oneline)
    mail_state = m.group(1) if m else None

    apn = (p.get("identifier") or {}).get("apn")
    owner_name = (owner.get("owner1") or {}).get("fullName")

    # Lat/lng from ATTOM's location block
    loc = p.get("location") or {}
    try:
        lat = float(loc.get("latitude")) if loc.get("latitude") else None
        lng = float(loc.get("longitude")) if loc.get("longitude") else None
    except (TypeError, ValueError):
        lat = lng = None

    # Property state — ATTOM uses `countrySubd` for the 2-letter state code
    prop_state = (prop_addr.get("countrySubd") or "").upper().strip() or None
    if not prop_state:
        # Fallback: parse from oneLine ("..., CITY, ST 12345")
        ones = prop_addr.get("oneLine") or ""
        sm = re.search(r",\s*([A-Z]{2})\s+\d{5}", ones)
        if sm:
            prop_state = sm.group(1)

    return RawLead(
        source="vacant",                     # our "vacant/absentee" tab covers both
        source_id=f"attom-absentee-{apn or prop_addr.get('oneLine')}",
        parcel_apn=apn,
        raw_address=prop_addr.get("line1") or prop_addr.get("oneLine"),
        city=prop_addr.get("locality"),
        state=prop_state or "WA",            # default only if ATTOM omitted it
        zip=prop_addr.get("postal1"),
        owner_state=mail_state,
        owner_name=owner_name,
        latitude=lat,
        longitude=lng,
        extra={
            "attom_id":     (p.get("identifier") or {}).get("attomId"),
            "prop_addr":    prop_addr.get("oneLine"),
            "mail_addr":    mail_oneline,
            "owner_name":   owner_name,
            "why_absentee": f"ATTOM absentee flag (A); owner mailing {mail_oneline}",
        },
    )


# ---------- 3. Sales comps (for the Sell page valuation) ----------

async def recent_sales(postal_code: str, months_back: int = 24, page_size: int = 50) -> list[dict]:
    """Pull the last `months_back` months of sales in a ZIP. Used by the
    AI home-valuation module on the homepage's sell section to compute
    a price band with real comps."""
    if not settings.attom_api_key:
        return []
    async with _client() as c:
        r = await c.get(
            f"{BASE}/propertyapi/v1.0.0/sale/snapshot",
            params={
                "postalcode": postal_code,
                "pagesize":   page_size,
                "minsalerecdate": _months_ago_iso(months_back),
            },
        )
    if r.status_code != 200:
        log.warning("ATTOM sales %s — %d", postal_code, r.status_code)
        return []
    return r.json().get("property") or []


def _months_ago_iso(months: int) -> str:
    """YYYY-MM-DD for `months` ago — ATTOM's `minsalerecdate` format."""
    from datetime import date, timedelta
    d = date.today() - timedelta(days=30 * months)
    return d.strftime("%Y-%m-%d")
