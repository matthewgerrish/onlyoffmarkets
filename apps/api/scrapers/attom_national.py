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


# Curated zip list — anchor zip from each top US metro by population +
# typical investor activity. ~200 zips covering all 50 states.
# Override with ATTOM_NATIONAL_ZIPS env var for ad-hoc runs.
NATIONAL_ZIPS: list[tuple[str, str]] = [
    # ── Northeast ──
    ("10001", "New York, NY"),
    ("10453", "Bronx, NY"),
    ("11201", "Brooklyn, NY"),
    ("11354", "Queens, NY"),
    ("10301", "Staten Island, NY"),
    ("07102", "Newark, NJ"),
    ("07601", "Hackensack, NJ"),
    ("08608", "Trenton, NJ"),
    ("19101", "Philadelphia, PA"),
    ("15201", "Pittsburgh, PA"),
    ("18101", "Allentown, PA"),
    ("17101", "Harrisburg, PA"),
    ("02101", "Boston, MA"),
    ("01101", "Springfield, MA"),
    ("01601", "Worcester, MA"),
    ("06101", "Hartford, CT"),
    ("06510", "New Haven, CT"),
    ("06901", "Stamford, CT"),
    ("02901", "Providence, RI"),
    ("04101", "Portland, ME"),
    ("03101", "Manchester, NH"),
    ("05401", "Burlington, VT"),
    ("12201", "Albany, NY"),
    ("13201", "Syracuse, NY"),
    ("14201", "Buffalo, NY"),
    ("14601", "Rochester, NY"),

    # ── Mid-Atlantic ──
    ("20001", "Washington, DC"),
    ("21201", "Baltimore, MD"),
    ("19801", "Wilmington, DE"),
    ("23501", "Norfolk, VA"),
    ("23220", "Richmond, VA"),
    ("24501", "Lynchburg, VA"),
    ("25301", "Charleston, WV"),

    # ── Southeast ──
    ("30301", "Atlanta, GA"),
    ("31401", "Savannah, GA"),
    ("31201", "Macon, GA"),
    ("33101", "Miami, FL"),
    ("33301", "Fort Lauderdale, FL"),
    ("33401", "West Palm Beach, FL"),
    ("32801", "Orlando, FL"),
    ("33601", "Tampa, FL"),
    ("33701", "St. Petersburg, FL"),
    ("32099", "Jacksonville, FL"),
    ("32501", "Pensacola, FL"),
    ("28201", "Charlotte, NC"),
    ("27601", "Raleigh, NC"),
    ("27401", "Greensboro, NC"),
    ("28301", "Fayetteville, NC"),
    ("29401", "Charleston, SC"),
    ("29201", "Columbia, SC"),
    ("29601", "Greenville, SC"),
    ("37201", "Nashville, TN"),
    ("38101", "Memphis, TN"),
    ("37902", "Knoxville, TN"),
    ("37402", "Chattanooga, TN"),
    ("35201", "Birmingham, AL"),
    ("36101", "Montgomery, AL"),
    ("36601", "Mobile, AL"),
    ("39201", "Jackson, MS"),
    ("39501", "Gulfport, MS"),
    ("70112", "New Orleans, LA"),
    ("70801", "Baton Rouge, LA"),
    ("71101", "Shreveport, LA"),
    ("40201", "Louisville, KY"),
    ("40502", "Lexington, KY"),

    # ── Midwest ──
    ("60601", "Chicago, IL"),
    ("60607", "Chicago Loop, IL"),
    ("60619", "Chicago South Side, IL"),
    ("60625", "Chicago North Side, IL"),
    ("60804", "Cicero, IL"),
    ("62701", "Springfield, IL"),
    ("61601", "Peoria, IL"),
    ("61101", "Rockford, IL"),
    ("46201", "Indianapolis, IN"),
    ("46601", "South Bend, IN"),
    ("47401", "Bloomington, IN"),
    ("46802", "Fort Wayne, IN"),
    ("43201", "Columbus, OH"),
    ("44101", "Cleveland, OH"),
    ("45202", "Cincinnati, OH"),
    ("44301", "Akron, OH"),
    ("44502", "Youngstown, OH"),
    ("43604", "Toledo, OH"),
    ("48201", "Detroit, MI"),
    ("49503", "Grand Rapids, MI"),
    ("48911", "Lansing, MI"),
    ("48104", "Ann Arbor, MI"),
    ("48507", "Flint, MI"),
    ("53201", "Milwaukee, WI"),
    ("53703", "Madison, WI"),
    ("54301", "Green Bay, WI"),
    ("55401", "Minneapolis, MN"),
    ("55101", "Saint Paul, MN"),
    ("55801", "Duluth, MN"),
    ("50301", "Des Moines, IA"),
    ("52401", "Cedar Rapids, IA"),
    ("63101", "St. Louis, MO"),
    ("64101", "Kansas City, MO"),
    ("65101", "Jefferson City, MO"),
    ("65801", "Springfield, MO"),
    ("66101", "Kansas City, KS"),
    ("66601", "Topeka, KS"),
    ("67201", "Wichita, KS"),
    ("68101", "Omaha, NE"),
    ("68501", "Lincoln, NE"),
    ("57104", "Sioux Falls, SD"),
    ("58102", "Fargo, ND"),

    # ── South Central / Texas / Plains ──
    ("75201", "Dallas, TX"),
    ("76101", "Fort Worth, TX"),
    ("75001", "Addison, TX (DFW)"),
    ("77001", "Houston, TX"),
    ("77002", "Houston Downtown, TX"),
    ("77004", "Houston Med Ctr, TX"),
    ("78201", "San Antonio, TX"),
    ("78701", "Austin, TX"),
    ("78704", "South Austin, TX"),
    ("76901", "San Angelo, TX"),
    ("79901", "El Paso, TX"),
    ("79401", "Lubbock, TX"),
    ("78501", "McAllen, TX"),
    ("78401", "Corpus Christi, TX"),
    ("73101", "Oklahoma City, OK"),
    ("74103", "Tulsa, OK"),
    ("72201", "Little Rock, AR"),
    ("72701", "Fayetteville, AR"),

    # ── Mountain / Southwest ──
    ("85001", "Phoenix, AZ"),
    ("85201", "Mesa, AZ"),
    ("85281", "Tempe, AZ"),
    ("85251", "Scottsdale, AZ"),
    ("85701", "Tucson, AZ"),
    ("87101", "Albuquerque, NM"),
    ("88001", "Las Cruces, NM"),
    ("89101", "Las Vegas, NV"),
    ("89509", "Reno, NV"),
    ("84101", "Salt Lake City, UT"),
    ("84601", "Provo, UT"),
    ("80201", "Denver, CO"),
    ("80903", "Colorado Springs, CO"),
    ("80525", "Fort Collins, CO"),
    ("83702", "Boise, ID"),
    ("59101", "Billings, MT"),
    ("82001", "Cheyenne, WY"),

    # ── West Coast ──
    ("90001", "Los Angeles, CA"),
    ("90011", "South LA, CA"),
    ("90015", "LA Downtown, CA"),
    ("90029", "East Hollywood, CA"),
    ("91201", "Glendale, CA"),
    ("91331", "Pacoima, CA"),
    ("91601", "North Hollywood, CA"),
    ("90701", "Artesia, CA"),
    ("90801", "Long Beach, CA"),
    ("92501", "Riverside, CA"),
    ("92401", "San Bernardino, CA"),
    ("92801", "Anaheim, CA"),
    ("92701", "Santa Ana, CA"),
    ("92101", "San Diego, CA"),
    ("92201", "Indio, CA"),
    ("93030", "Oxnard, CA"),
    ("93301", "Bakersfield, CA"),
    ("93701", "Fresno, CA"),
    ("95201", "Stockton, CA"),
    ("95350", "Modesto, CA"),
    ("94601", "Oakland, CA"),
    ("94110", "San Francisco, CA"),
    ("94568", "Dublin, CA (Bay)"),
    ("95110", "San Jose, CA"),
    ("95823", "Sacramento, CA"),
    ("97201", "Portland, OR"),
    ("97301", "Salem, OR"),
    ("97401", "Eugene, OR"),
    ("98101", "Seattle, WA"),
    ("98402", "Tacoma, WA"),
    ("98501", "Olympia, WA"),
    ("98801", "Wenatchee, WA"),
    ("99201", "Spokane, WA"),
    ("99501", "Anchorage, AK"),
    ("96813", "Honolulu, HI"),
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
