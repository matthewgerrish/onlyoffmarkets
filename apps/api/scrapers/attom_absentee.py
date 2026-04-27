"""
ATTOM absentee-owner scraper.

Uses ATTOM's `/property/basicprofile` endpoint (which your current
subscription covers — no Foreclosure bundle needed) to surface parcels
where the owner's mailing address is in a different city or ZIP than
the property itself. These are the classic off-market targets: the
owner doesn't live there, often rents it or sits on it, and direct-mail
response rates are 3–5× higher than for owner-occupied.

How it works:
  1. We iterate through a curated list of target ZIPs in King, Pierce,
     and Thurston counties (the ones PRP actually works).
  2. For each ZIP we paginate ATTOM's basicprofile (100 properties/page,
     capped at `max_pages_per_zip` pages — default 5 = 500 props/ZIP).
  3. Every property with `assessment.mailingAddress.locality` different
     from `address.locality` becomes a `RawLead` with `source="vacant"`
     (our absentee/vacant tab on the frontend).
  4. Pipeline upserts into `off_market_listings`; when the same APN
     surfaces again in a future run (or from a county scraper), tags
     merge rather than duplicating.

Cost at defaults: ~5 pages × 30 ZIPs = 150 calls/day. Well inside tier.

Config:
  ATTOM_API_KEY                — required
  ATTOM_ABSENTEE_MAX_PAGES_ZIP — override default 5

Run standalone:
  python -m scrapers.attom_absentee
"""
from __future__ import annotations

import logging
import os
from typing import AsyncIterable

from scrapers.base import BaseScraper
from scrapers.models import RawLead
from scrapers.attom_enrich import find_absentee_by_zip
from config import settings

log = logging.getLogger(__name__)


# The ZIPs PRP actively works. Ordered county → micro-market for reviewability.
# Trim or extend as coverage evolves; the scraper iterates in order.
TARGET_ZIPS = {
    # --- Pierce County ---
    "Pierce": [
        "98402", "98403", "98404", "98405", "98406", "98407", "98408", "98409",
        "98422", "98424",  # Tacoma
        "98443", "98444", "98445", "98446",  # East Tacoma
        "98465", "98466", "98467",  # University Place
        "98335",  # Gig Harbor
        "98371", "98372", "98373", "98374", "98375",  # Puyallup
        "98387",  # Spanaway
        "98391",  # Bonney Lake
        "98390",  # Sumner
    ],
    # --- South King County ---
    "King": [
        "98003", "98023",          # Federal Way
        "98002", "98092",          # Auburn
        "98030", "98031", "98042", # Kent / Covington
    ],
    # --- Thurston County ---
    "Thurston": [
        "98501", "98502", "98506",  # Olympia
        "98503", "98516",           # Lacey
        "98512",                    # Tumwater
        "98597",                    # Yelm
        "98589",                    # Tenino
    ],
}


class AttomAbsenteeScraper(BaseScraper):
    """Iterates target ZIPs, emits absentee leads via ATTOM enrichment."""

    source = "vacant"               # the "Vacant / Absentee Owner" tab
    source_name = "ATTOM absentee owners"
    rate_limit_sec = 0.6            # base-class throttle not used (enrichment has its own client)

    def __init__(self, max_pages_per_zip: int | None = None, **kw):
        super().__init__(**kw)
        self.max_pages = int(
            max_pages_per_zip
            or os.getenv("ATTOM_ABSENTEE_MAX_PAGES_ZIP", "5")
        )

    async def run(self) -> AsyncIterable[RawLead]:
        if not settings.attom_api_key:
            log.warning("ATTOM_API_KEY not set — absentee scraper is a no-op.")
            return

        total = 0
        for county, zips in TARGET_ZIPS.items():
            county_count = 0
            for zipcode in zips:
                zip_count = 0
                try:
                    async for lead in find_absentee_by_zip(
                        zipcode,
                        page_size=100,
                        max_pages=self.max_pages,  # hard cap inside the generator
                    ):
                        lead.county = county
                        yield lead
                        zip_count += 1
                        county_count += 1
                        total += 1
                except Exception as e:
                    log.warning("ATTOM absentee %s failed: %s", zipcode, e)
                log.info("  %s (%s): %d absentee", zipcode, county, zip_count)
            log.info("── %s County: %d absentee leads ──", county, county_count)

        log.info("ATTOM absentee: %d total leads across %d ZIPs",
                 total, sum(len(z) for z in TARGET_ZIPS.values()))


# ---------- standalone entrypoint ----------

async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    scraper = AttomAbsenteeScraper()
    count = 0
    by_county: dict[str, int] = {}
    try:
        async for lead in scraper.run():
            count += 1
            by_county[lead.county or "?"] = by_county.get(lead.county or "?", 0) + 1
    finally:
        await scraper.close()
    log.info("Done. %d absentee leads: %s", count, by_county)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
