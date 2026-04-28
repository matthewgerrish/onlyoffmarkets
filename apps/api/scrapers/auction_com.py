"""Auction.com — nationwide trustee + REO auction listings.

Auction.com lists properties going to trustee or sheriff sale plus
bank-owned auction inventory. Their search page exposes the listing
data inline as a JSON blob (`__NEXT_DATA__`).

We hit the per-state search URL and parse the embedded data.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import AsyncIterable

import httpx

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)

ALL_STATES = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new-hampshire", "new-jersey", "new-mexico", "new-york",
    "north-carolina", "north-dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode-island", "south-carolina", "south-dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west-virginia", "wisconsin", "wyoming",
]

# Mapping for state codes
STATE_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new-hampshire": "NH", "new-jersey": "NJ", "new-mexico": "NM", "new-york": "NY",
    "north-carolina": "NC", "north-dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode-island": "RI",
    "south-carolina": "SC", "south-dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west-virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}


class AuctionComScraper(BaseScraper):
    source = "auction"
    source_name = "Auction.com (national)"
    rate_limit_sec = 1.5

    async def run(self, states: list[str] | None = None) -> AsyncIterable[RawLead]:
        targets = states or ALL_STATES
        for slug in targets:
            try:
                async for lead in self._scrape_state(slug):
                    yield lead
            except Exception as e:
                log.warning("Auction.com %s failed: %s — continuing", slug, e)
                continue

    async def _scrape_state(self, slug: str) -> AsyncIterable[RawLead]:
        url = f"https://www.auction.com/residential/{slug}"
        try:
            html = await self.get(url)
        except (httpx.HTTPStatusError, httpx.RequestError, PermissionError) as e:
            log.warning("auction.com %s fetch failed: %s", slug, e)
            return

        # The site embeds search results in a __NEXT_DATA__ script tag
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html, re.S)
        if not m:
            log.debug("auction.com %s: no __NEXT_DATA__ block", slug)
            return

        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return

        listings = (
            data.get("props", {}).get("pageProps", {}).get("listings")
            or data.get("props", {}).get("pageProps", {}).get("results")
            or []
        )
        state_code = STATE_ABBR.get(slug, "")
        for item in listings:
            yield self._make_lead(item, state_code)

    @staticmethod
    def _make_lead(item: dict, state: str) -> RawLead:
        addr = item.get("address") or item.get("street") or ""
        city = item.get("city") or ""
        zip_code = str(item.get("zip") or item.get("zipCode") or "") or None
        listing_id = str(item.get("globalPropertyId") or item.get("id") or addr)

        opening_bid = item.get("startingBid") or item.get("currentBid") or item.get("listPrice")
        if isinstance(opening_bid, str):
            try:
                opening_bid = int(opening_bid.replace(",", "").replace("$", ""))
            except ValueError:
                opening_bid = None

        sale_date_raw = item.get("auctionStartDate") or item.get("saleDate")
        sale_date = None
        if sale_date_raw:
            try:
                sale_date = datetime.fromisoformat(sale_date_raw.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        return RawLead(
            source="auction",
            source_id=f"auctioncom-{listing_id}",
            raw_address=addr,
            city=city,
            state=state,
            zip=zip_code,
            opening_bid=opening_bid,
            sale_date=sale_date,
            source_url=f"https://www.auction.com/details/{listing_id}",
            extra={"raw": item},
        )


async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = AuctionComScraper()
    n = 0
    try:
        async for lead in s.run(states=["washington", "florida"]):
            n += 1
    finally:
        await s.close()
    log.info("Done. %d leads.", n)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
