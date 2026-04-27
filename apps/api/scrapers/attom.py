"""
ATTOM Data Solutions — commercial off-market feed.

This sits in `scrapers/` alongside the county scrapers even though it's
an API, not HTML scraping. From the pipeline's perspective it's just
another source of `RawLead`s.

What ATTOM covers (single API key, three tabs on our frontend):
  • preforeclosure  — NOD/NTS filings, aggregated from all US counties
  • auction         — trustee/sheriff sale calendar (includes Auction.com
                      inventory since ATTOM owns that feed)
  • reo             — bank-owned inventory post-auction

Two endpoints do all the work:

  foreclosure/snapshot                List of properties in foreclosure for
                                      a geography, paginated. One call per
                                      county per day.
  property/expandedprofile            Detailed enrichment on a single ATTOM
                                      property ID — lot size, zoning, owner.
                                      Called on demand for records we want
                                      to surface in the deal stream.

Budget: ~290 calls/day at defaults (snapshot + enrichment for new records
only). Sits comfortably inside ATTOM's entry tier.

Config:
  ATTOM_API_KEY       — paid credential
  ATTOM_BASE_URL      — defaults to https://api.gateway.attomdata.com
  ATTOM_DAILY_CAP     — max calls per pipeline run (safety valve)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import AsyncIterable

import httpx

from scrapers.base import BaseScraper, DEFAULT_USER_AGENT
from scrapers.models import RawLead

log = logging.getLogger(__name__)


# FIPS codes — ATTOM's geography keys
COUNTY_FIPS = {
    "King":     "53033",
    "Pierce":   "53053",
    "Thurston": "53067",
}

# ATTOM's `foreclosurestatus` → our internal source taxonomy
STATUS_TO_SOURCE = {
    "PRE_FORECLOSURE":  "preforeclosure",
    "AUCTION":          "auction",
    "REO":              "reo",
    "BANK_OWNED":       "reo",
}


class AttomScraper(BaseScraper):
    """Pulls foreclosure + auction + REO inventory from ATTOM daily.

    Emits one `RawLead` per property, tagged with the right source based on
    ATTOM's reported foreclosure status. Enrichment is optional — control
    with `enrich_new_records=True` (default on).
    """

    source = "attom"         # high-level tag; individual leads re-tag per record
    source_name = "ATTOM Data Solutions"
    rate_limit_sec = 0.5     # ATTOM allows 10 req/sec on most tiers — stay polite

    # Calls per pipeline run, safety valve against runaway bugs.
    daily_cap: int = int(os.getenv("ATTOM_DAILY_CAP", "2000"))

    def __init__(self, enrich_new_records: bool = True, **kw):
        super().__init__(**kw)
        self.enrich = enrich_new_records
        self.api_key = os.getenv("ATTOM_API_KEY", "")
        self.base = os.getenv("ATTOM_BASE_URL", "https://api.gateway.attomdata.com")
        self._calls_made = 0
        self._auth_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "apikey": self.api_key,
                "Accept": "application/json",
                "User-Agent": DEFAULT_USER_AGENT,
            },
        )

    async def run(self) -> AsyncIterable[RawLead]:
        if not self.api_key:
            log.warning("ATTOM_API_KEY not set — ATTOM scraper is a no-op.")
            return

        # One preflight call to detect whether the Foreclosure bundle is on
        # this key. If not, skip the snapshot loop entirely and return zero
        # leads — we still use ATTOM elsewhere for enrichment (see attom_enrich.py).
        if not await self._has_foreclosure_bundle():
            log.warning(
                "ATTOM Foreclosure bundle is NOT included in this subscription. "
                "Skipping snapshot. "
                "Contact ATTOM sales to add the Foreclosure product, or use "
                "attom_enrich.py to layer Property+Sales data onto county-scraped leads."
            )
            return

        for county, fips in COUNTY_FIPS.items():
            log.info("ATTOM %s County (fips=%s) …", county, fips)
            async for lead in self._scrape_county(county, fips):
                yield lead

    async def _has_foreclosure_bundle(self) -> bool:
        """One-shot check: does this key have access to the Foreclosure endpoint?
        Returns True on 200, False on 404 (= bundle not subscribed)."""
        data = await self._get("/propertyapi/v1.0.0/foreclosure/snapshot", {
            "geoIdV4":  f"COUNTY_{COUNTY_FIPS['Pierce']}",
            "pagesize": 1,
        })
        # `_get` returns None on 404 / auth / rate-limit issues.
        # Any structured response (dict with `status`) means access is granted.
        return isinstance(data, dict) and "status" in data

    async def _scrape_county(self, county: str, fips: str) -> AsyncIterable[RawLead]:
        page = 1
        page_size = 100
        while True:
            if self._calls_made >= self.daily_cap:
                log.warning("Hit ATTOM daily cap (%d) — stopping.", self.daily_cap)
                return

            data = await self._get("/propertyapi/v1.0.0/foreclosure/snapshot", {
                "geoIdV4":      f"COUNTY_{fips}",
                "page":         page,
                "pagesize":     page_size,
                "orderby":      "DateAddedToSystem+DESC",
            })
            if not data:
                return

            items = (data.get("property") or [])
            log.info("  page %d: %d results", page, len(items))

            for row in items:
                yield self._to_lead(row, county)

            total = data.get("status", {}).get("total", 0)
            if page * page_size >= total:
                return
            page += 1

    def _to_lead(self, row: dict, county: str) -> RawLead:
        """Map one ATTOM foreclosure record into our `RawLead` DTO."""
        status_code = (row.get("foreclosure", {}).get("foreclosureStatus") or "").upper()
        source_tag  = STATUS_TO_SOURCE.get(status_code, "preforeclosure")

        # Normalize address
        addr = row.get("address", {})
        street  = addr.get("line1") or addr.get("oneLine")
        city    = addr.get("locality")
        zipcode = addr.get("postal1")

        identifier = row.get("identifier", {})
        attom_id   = str(identifier.get("attomId") or identifier.get("Id") or "")
        apn        = identifier.get("apn")

        fc = row.get("foreclosure", {}) or {}

        return RawLead(
            source=source_tag,
            source_id=f"attom-{attom_id}" if attom_id else f"attom-{apn}-{source_tag}",
            parcel_apn=apn,
            raw_address=street,
            city=city,
            county=county,
            zip=zipcode,
            filing_date=_parse_date(fc.get("recordingDate")),
            sale_date=_parse_date(fc.get("auctionDate")),
            default_amount=_parse_int(fc.get("defaultAmount")),
            opening_bid=_parse_int(fc.get("openingBid")),
            source_url=f"https://api.attomdata.com/property/{attom_id}"
                       if attom_id else None,
            extra={
                "attom_id":   attom_id,
                "status":     status_code,
                "lender":     fc.get("lenderName"),
                "trustee":    fc.get("trusteeName"),
                "raw":        {k: v for k, v in row.items() if k not in ("address", "identifier")},
            },
        )

    async def _get(self, path: str, params: dict) -> dict | None:
        """Low-level ATTOM call with counting, polite retries, and graceful 404."""
        if self._calls_made >= self.daily_cap:
            return None
        await self._throttle()
        self._calls_made += 1
        try:
            r = await self._auth_client.get(f"{self.base}{path}", params=params)
        except httpx.RequestError as e:
            log.warning("ATTOM request failed (%s): %s", path, e)
            return None

        # ATTOM returns 200 with an empty status for "no results" — not 404
        if r.status_code == 404:
            return None
        if r.status_code == 401:
            log.error("ATTOM 401 — check ATTOM_API_KEY")
            return None
        if r.status_code == 429:
            log.warning("ATTOM 429 rate-limit — backing off")
            return None
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.warning("ATTOM %d on %s: %s", r.status_code, path, e)
            return None

        return r.json()

    async def close(self):
        await super().close()
        await self._auth_client.aclose()
        log.info("ATTOM run complete: %d calls made.", self._calls_made)


# ---------- helpers ----------

def _parse_date(s: str | None) -> datetime | None:
    """ATTOM uses multiple date shapes; try the common ones."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_int(v) -> int | None:
    if v in (None, "", 0):
        return None
    try:
        return int(float(str(v).replace(",", "").replace("$", "")))
    except (ValueError, TypeError):
        return None


# ---------- standalone entrypoint ----------

async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    scraper = AttomScraper()
    count = 0
    by_tag: dict[str, int] = {}
    try:
        async for lead in scraper.run():
            count += 1
            by_tag[lead.source] = by_tag.get(lead.source, 0) + 1
    finally:
        await scraper.close()
    log.info("Done. %d leads scraped from ATTOM: %s", count, by_tag)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
