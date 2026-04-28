"""ATTOM nationwide absentee — top-50 US metros.

Same plumbing as `attom_absentee` (uses `/property/basicprofile`, identifies
out-of-state-owner parcels), but iterates a curated nationwide zip list
covering the top 50 metros by investor activity.

Override the zip list with `ATTOM_NATIONAL_ZIPS=zip1,zip2,...` to scope
a single run.

Scale at defaults: 5 pages × 200 zips = 1000 calls/day, well inside
the 30-day free trial's request budget if you run weekly.
"""
from __future__ import annotations

import logging
import os
from typing import AsyncIterable

from scrapers.base import BaseScraper
from scrapers.models import RawLead
from scrapers.attom_enrich import find_absentee_by_zip

log = logging.getLogger(__name__)


# Curated zip list — anchor zip from each top-50 metro by population +
# typical investor activity. Not exhaustive; expand by metro over time.
NATIONAL_ZIPS: list[tuple[str, str]] = [
    # zip, city/state hint (for logging only)
    ("10001", "New York, NY"),
    ("90001", "Los Angeles, CA"),
    ("60601", "Chicago, IL"),
    ("75201", "Dallas, TX"),
    ("77001", "Houston, TX"),
    ("85001", "Phoenix, AZ"),
    ("19101", "Philadelphia, PA"),
    ("78201", "San Antonio, TX"),
    ("92101", "San Diego, CA"),
    ("75001", "Addison TX (DFW)"),
    ("95201", "Stockton, CA"),
    ("78701", "Austin, TX"),
    ("32099", "Jacksonville, FL"),
    ("76101", "Fort Worth, TX"),
    ("43201", "Columbus, OH"),
    ("28201", "Charlotte, NC"),
    ("46201", "Indianapolis, IN"),
    ("98101", "Seattle, WA"),
    ("80201", "Denver, CO"),
    ("20001", "Washington, DC"),
    ("02101", "Boston, MA"),
    ("37201", "Nashville, TN"),
    ("21201", "Baltimore, MD"),
    ("97201", "Portland, OR"),
    ("89101", "Las Vegas, NV"),
    ("04101", "Portland, ME"),  # smaller
    ("63101", "St. Louis, MO"),
    ("41001", "Northern KY"),
    ("70112", "New Orleans, LA"),
    ("48201", "Detroit, MI"),
    ("55401", "Minneapolis, MN"),
    ("33101", "Miami, FL"),
    ("30301", "Atlanta, GA"),
    ("23501", "Norfolk, VA"),
    ("40201", "Louisville, KY"),
    ("53201", "Milwaukee, WI"),
    ("87101", "Albuquerque, NM"),
    ("85701", "Tucson, AZ"),
    ("93701", "Fresno, CA"),
    ("94601", "Oakland, CA"),
    ("88001", "Las Cruces, NM"),
    ("64101", "Kansas City, MO"),
    ("50301", "Des Moines, IA"),
    ("68101", "Omaha, NE"),
    ("33401", "West Palm Beach, FL"),
    ("32801", "Orlando, FL"),
    ("44101", "Cleveland, OH"),
    ("84101", "Salt Lake City, UT"),
    ("36601", "Mobile, AL"),
    ("18101", "Allentown, PA"),
]


def _zip_list() -> list[str]:
    override = os.getenv("ATTOM_NATIONAL_ZIPS", "").strip()
    if override:
        return [z.strip() for z in override.split(",") if z.strip()]
    return [z for z, _ in NATIONAL_ZIPS]


class AttomNationalScraper(BaseScraper):
    """Top-50 metro absentee scraper. Persists into the same table as `attom-absentee`."""

    source = "vacant"
    source_name = "ATTOM nationwide absentee owners"
    rate_limit_sec = 0.6

    def __init__(self, max_pages_per_zip: int | None = None, **kw):
        super().__init__(**kw)
        self.max_pages = int(
            max_pages_per_zip
            or os.getenv("ATTOM_NATIONAL_MAX_PAGES_ZIP", "5")
        )

    async def run(self) -> AsyncIterable[RawLead]:
        if not os.getenv("ATTOM_API_KEY", "").strip():
            log.warning("ATTOM_API_KEY not set — national scraper is a no-op.")
            return

        total = 0
        for zipcode in _zip_list():
            zip_count = 0
            try:
                async for lead in find_absentee_by_zip(
                    zipcode,
                    page_size=100,
                    max_pages=self.max_pages,
                ):
                    yield lead
                    zip_count += 1
                    total += 1
            except Exception as e:
                log.warning("ATTOM national zip %s failed: %s", zipcode, e)
            log.info("  %s: %d absentee", zipcode, zip_count)

        log.info("ATTOM national: %d total absentee leads across %d ZIPs",
                 total, len(_zip_list()))


async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = AttomNationalScraper()
    n = 0
    try:
        async for _ in s.run():
            n += 1
    finally:
        await s.close()
    log.info("Done. %d leads.", n)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
