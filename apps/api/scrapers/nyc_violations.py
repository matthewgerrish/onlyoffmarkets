"""NYC Open Data — DOB building violations.

NYC publishes every Department of Buildings violation through their
Socrata Open Data API. Real REST endpoint, no API key required for
public data, ~5k req/hour unauthenticated rate cap.

Dataset:
  https://data.cityofnewyork.us/Housing-Development/DOB-Violations/3h2n-5cm9

We pull the most recent ACTIVE violations (issued in the last N days)
and emit them as `vacant`-tagged RawLeads — building violations are
one of the strongest distress proxies in dense urban markets.

Why this works (unlike the HUD/HomePath scrapers): Socrata is a
permissive open-data platform with stable JSON endpoints. NYC has
been publishing this dataset since 2013 with the same schema.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import AsyncIterable

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)

API_URL = "https://data.cityofnewyork.us/resource/3h2n-5cm9.json"


class NYCViolationsScraper(BaseScraper):
    source = "vacant"             # building violations → distress proxy
    source_name = "NYC DOB Violations (Open Data)"
    rate_limit_sec = 0.3          # NYC OpenData is fast; we're polite

    def __init__(self, days_back: int = 30, **kw):
        super().__init__(**kw)
        self.days_back = days_back

    async def run(self) -> AsyncIterable[RawLead]:
        # NYC stores issue_date as YYYYMMDD strings (no dashes), so the
        # SoQL filter is a string comparison against that exact format.
        cutoff = (datetime.utcnow() - timedelta(days=self.days_back)).strftime("%Y%m%d")

        offset = 0
        page_size = 1000
        max_pages = 20  # 20k records cap per run; keeps memory + DB sane

        for page in range(max_pages):
            params = {
                "$where": (
                    f"issue_date >= '{cutoff}' "
                    "AND violation_category like 'V%ACTIVE%'"
                ),
                "$select": (
                    "isn_dob_bis_viol, issue_date, violation_type, "
                    "house_number, street, boro, block, lot, bin, bbl, "
                    "violation_category, description"
                ),
                "$limit": str(page_size),
                "$offset": str(offset),
                "$order": "issue_date DESC",
            }
            try:
                text = await self.get(API_URL, params=params)
            except PermissionError:
                log.warning("robots.txt blocked NYC scrape")
                return
            except Exception as e:
                log.warning("NYC fetch failed (page=%d): %s", page, e)
                return

            try:
                rows = json.loads(text)
            except json.JSONDecodeError:
                log.warning("NYC returned non-JSON — stopping")
                return

            if not rows:
                log.info("NYC: end of dataset at page %d", page)
                return

            for r in rows:
                lead = self._to_lead(r)
                if lead:
                    yield lead

            if len(rows) < page_size:
                return
            offset += page_size

    @staticmethod
    def _to_lead(r: dict) -> RawLead | None:
        viol_id = r.get("isn_dob_bis_viol")
        if not viol_id:
            return None

        house = (r.get("house_number") or "").strip()
        street = (r.get("street") or "").strip()
        addr = f"{house} {street}".strip()
        if not addr:
            return None

        bbl = r.get("bbl")  # Borough-Block-Lot — NYC's canonical parcel id
        boro = r.get("boro")
        city = _BORO_NAME.get(str(boro), "New York") if boro else "New York"

        # issue_date format is YYYYMMDD (no dashes) — try that first,
        # then ISO as a fallback in case NYC ever updates the schema.
        raw_date = (r.get("issue_date") or "").strip()
        issue_date = None
        for fmt in ("%Y%m%d", "%Y-%m-%d"):
            try:
                issue_date = datetime.strptime(raw_date[:10], fmt)
                break
            except Exception:
                continue

        return RawLead(
            source="vacant",
            source_id=f"nyc-dob-{viol_id}",
            raw_address=addr,
            city=city,
            county=_BORO_COUNTY.get(str(boro)) if boro else None,
            state="NY",
            parcel_apn=str(bbl) if bbl else None,
            filing_date=issue_date,
            source_url=(
                "https://a810-bisweb.nyc.gov/bisweb/"
                f"ECBQueryByLocationServlet?house={house}&street={street.replace(' ', '+')}"
            ),
            extra={
                "violation_type": r.get("violation_type"),
                "violation_category": r.get("violation_category"),
                "description": r.get("description"),
                "bin": r.get("bin"),
                "bbl": bbl,
            },
        )


# NYC's `boro` field uses 1-5 codes; map for human display.
_BORO_NAME = {
    "1": "Manhattan",
    "2": "Bronx",
    "3": "Brooklyn",
    "4": "Queens",
    "5": "Staten Island",
}
_BORO_COUNTY = {
    "1": "New York",
    "2": "Bronx",
    "3": "Kings",
    "4": "Queens",
    "5": "Richmond",
}
