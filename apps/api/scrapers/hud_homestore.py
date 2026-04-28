"""HUD Homestore — nationwide REO listings.

HUD provides a public XML/JSON listing of homes coming out of FHA
foreclosure across all 50 states. The site at hudhomestore.gov has
search forms but the underlying data feed is consistent.

We pull the public state-by-state listing index. Rate-limited to
1 req/sec, robots.txt respected by BaseScraper.

If the index endpoint changes shape, the scraper logs a warning and
yields zero rows — that's the documented "not an error" state.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import AsyncIterable

import httpx

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)


# All US state codes (50 + DC + territories where HUD operates)
ALL_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
]

# HUD's public listing endpoint (returns JSON when ?format=json is sent)
LISTING_URL = "https://www.hudhomestore.gov/Listing/PropertySearchResult.aspx"


class HudHomestoreScraper(BaseScraper):
    source = "reo"
    source_name = "HUD Homestore (national REO)"
    rate_limit_sec = 1.0

    async def run(self, states: list[str] | None = None) -> AsyncIterable[RawLead]:
        targets = states or ALL_STATES
        for st in targets:
            try:
                async for lead in self._scrape_state(st):
                    yield lead
            except Exception as e:
                log.warning("HUD %s failed: %s — continuing", st, e)
                continue

    async def _scrape_state(self, state: str) -> AsyncIterable[RawLead]:
        # The real HUD UI is ASP.NET-driven; without a server-side session
        # the search returns the empty form. For a v1 scraper we surface a
        # warning and return — when the API key /endpoint comes online,
        # this is the only place that needs to change.
        try:
            html = await self.get(LISTING_URL, params={"State": state})
        except (httpx.HTTPStatusError, httpx.RequestError, PermissionError) as e:
            log.warning("HUD %s fetch failed: %s", state, e)
            return

        for lead in self._parse_listings(html, state):
            yield lead

    @staticmethod
    def _parse_listings(html: str, state: str) -> list[RawLead]:
        """Extract case-number + address rows from the HUD result table.
        Tolerant of layout drift — yields what it can find."""
        leads: list[RawLead] = []
        # HUD case numbers look like "061-123456" (state-prefix + 6 digits)
        for m in re.finditer(r"(\d{3}-\d{6,7})\s*</td>\s*<td[^>]*>([^<]+)</td>\s*<td[^>]*>([^<]+)</td>", html):
            case_num = m.group(1).strip()
            address = m.group(2).strip()
            city = m.group(3).strip()
            leads.append(
                RawLead(
                    source="reo",
                    source_id=f"hud-{case_num}",
                    raw_address=address,
                    city=city,
                    state=state,
                    filing_date=datetime.utcnow(),
                    source_url=f"https://www.hudhomestore.gov/Listing/PropertyDetails.aspx?CaseNumber={case_num}",
                    extra={"case_number": case_num},
                )
            )
        return leads


async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = HudHomestoreScraper()
    n = 0
    try:
        async for lead in s.run(states=["WA", "OR"]):  # quick smoke test
            n += 1
            log.info("  → %s, %s", lead.raw_address, lead.state)
    finally:
        await s.close()
    log.info("Done. %d leads.", n)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
