"""HomePath — Fannie Mae REO listings (nationwide).

HomePath.com lists properties Fannie Mae has taken back through
foreclosure. Public, no API key required. Their search uses a
JSON endpoint at /api/v1/search.

Rate limit: 1 req/sec. We page through state-by-state.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import AsyncIterable

import httpx

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)

ALL_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
]

SEARCH_URL = "https://www.homepath.com/api/v1/search"


class HomePathScraper(BaseScraper):
    source = "reo"
    source_name = "HomePath (Fannie Mae REO)"
    rate_limit_sec = 1.0

    async def run(self, states: list[str] | None = None) -> AsyncIterable[RawLead]:
        targets = states or ALL_STATES
        for st in targets:
            try:
                async for lead in self._scrape_state(st):
                    yield lead
            except Exception as e:
                log.warning("HomePath %s failed: %s — continuing", st, e)
                continue

    async def _scrape_state(self, state: str) -> AsyncIterable[RawLead]:
        params = {"state": state, "page": 1, "size": 200}
        try:
            text = await self.get(SEARCH_URL, params=params)
        except (httpx.HTTPStatusError, httpx.RequestError, PermissionError) as e:
            log.warning("HomePath %s fetch failed: %s", state, e)
            return

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            log.warning("HomePath %s returned non-JSON — skipping", state)
            return

        listings = data.get("listings") or data.get("results") or []
        for item in listings:
            yield self._make_lead(item, state)

    @staticmethod
    def _make_lead(item: dict, state: str) -> RawLead:
        addr = item.get("address") or item.get("streetAddress") or ""
        city = item.get("city") or ""
        zip_code = str(item.get("zip") or item.get("zipCode") or "") or None
        listing_id = str(item.get("id") or item.get("listingId") or addr)

        asking = item.get("listPrice") or item.get("price")
        if isinstance(asking, str):
            try:
                asking = int(asking.replace(",", "").replace("$", ""))
            except ValueError:
                asking = None

        return RawLead(
            source="reo",
            source_id=f"homepath-{listing_id}",
            raw_address=addr,
            city=city,
            state=state,
            zip=zip_code,
            asking_price=asking,
            filing_date=datetime.utcnow(),
            source_url=f"https://www.homepath.com/property/{listing_id}",
            extra={"raw": item},
        )


async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = HomePathScraper()
    n = 0
    try:
        async for lead in s.run(states=["WA", "FL"]):
            n += 1
    finally:
        await s.close()
    log.info("Done. %d leads.", n)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
