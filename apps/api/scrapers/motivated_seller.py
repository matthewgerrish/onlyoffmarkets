"""
Motivated Seller scraper (NWMLS via Trestle, with cross-checked tax data).

A "motivated seller" in our taxonomy is an ACTIVE MLS listing that
satisfies BOTH conditions:

  1. List price ≤ county tax-assessed value
  2. Days on market > 30

The first signal flags a seller pricing into-or-below the assessor's
opinion of value — which agents almost never do voluntarily unless
the property has a problem or the owner is hurting. The second signal
filters out the natural early-listing churn (most homes sell in <14 days
in this market when priced right).

Why this isn't an iHomefinder IDX feed:
  IDX consumer feeds give us active listings + DOM, but they DO NOT
  include `TaxAssessedValue` or any field we'd need to compute the
  "≤ assessed" half of this signal. RESO Trestle exposes the tax
  fields directly on the Property resource — so we go straight to
  the source.

For listings missing TaxAssessedValue in Trestle, we fall back to
ATTOM enrichment downstream (the `attom.py` scraper already pulls
assessed values for the same parcels we touch).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import AsyncIterable

from config import settings
from scrapers.base import BaseScraper
from scrapers.models import RawLead
from trestle import trestle

log = logging.getLogger(__name__)


# Counties we cover. Trestle uses both "<Name>" and "<Name> County" — we OR both.
COUNTIES = ("King", "Pierce", "Thurston")

# Days-on-market floor. 30 is the conventional "not selling" threshold
# in a market where median DOM hovers in the low-to-mid teens. Override
# via env if you want hotter or staler leads.
DOM_THRESHOLD = int(os.getenv("MOTIVATED_DOM_THRESHOLD", "30"))

# Price-to-assessed ratio ceiling. 1.00 = at-or-below assessed.
# Bump above 1.0 for a softer net (e.g., 1.05 = within 5% above assessed).
PRICE_RATIO_MAX = float(os.getenv("MOTIVATED_PRICE_RATIO", "1.00"))


class MotivatedSellerScraper(BaseScraper):
    source = "motivated_seller"
    source_name = "Active MLS — motivated seller (DOM>30, ≤ assessed)"
    rate_limit_sec = 0.0          # Trestle is OAuth-rate-limited server-side
    cache_ttl = 6 * 60 * 60

    async def run(self) -> AsyncIterable[RawLead]:
        if not settings.trestle_client_id:
            log.warning("Trestle not configured — skipping motivated_seller scraper")
            return

        county_filter = " or ".join(f"CountyOrParish eq '{c}'" for c in COUNTIES) + \
                        " or " + " or ".join(f"CountyOrParish eq '{c} County'" for c in COUNTIES)

        params = {
            "$filter": (
                f"StandardStatus eq 'Active' "
                f"and DaysOnMarket gt {DOM_THRESHOLD} "
                f"and ({county_filter})"
            ),
            "$orderby": "DaysOnMarket desc",
            "$top": 200,
            "$skip": 0,
        }

        total_seen = 0
        total_qualified = 0

        while True:
            try:
                rows = await trestle.query("Property", params)
            except Exception as e:
                log.exception("Trestle query failed: %s", e)
                break
            if not rows:
                break

            for row in rows:
                total_seen += 1
                if not self._qualifies(row):
                    continue
                lead = self._to_lead(row)
                if lead:
                    yield lead
                    total_qualified += 1

            params["$skip"] += len(rows)
            if len(rows) < params["$top"]:
                break

        log.info(
            "── motivated-seller: %d active >30 DOM, %d priced ≤ assessed",
            total_seen, total_qualified,
        )

    @staticmethod
    def _qualifies(row: dict) -> bool:
        list_price = row.get("ListPrice")
        assessed   = row.get("TaxAssessedValue")
        if not (list_price and assessed):
            # No assessed value available in this row — skip. The merge
            # step downstream will pick up ATTOM-sourced assessed values
            # and re-tag if they qualify on the next pass.
            return False
        try:
            ratio = float(list_price) / float(assessed)
        except (ValueError, ZeroDivisionError):
            return False
        return ratio <= PRICE_RATIO_MAX

    def _to_lead(self, row: dict) -> RawLead | None:
        listing_id = row.get("ListingId") or row.get("ListingKey")
        if not listing_id:
            return None

        list_price = int(row.get("ListPrice") or 0) or None
        assessed   = int(row.get("TaxAssessedValue") or 0) or None
        dom        = row.get("DaysOnMarket")
        county = (row.get("CountyOrParish") or "").replace(" County", "").strip() or None

        ratio_pct = None
        if list_price and assessed:
            ratio_pct = round(100 * (1 - list_price / assessed), 1)

        return RawLead(
            source="motivated_seller",
            source_id=f"nwmls-active-{listing_id}",
            scraped_at=datetime.utcnow(),
            raw_address=row.get("UnparsedAddress") or self._compose_addr(row),
            parcel_apn=row.get("ParcelNumber") or None,
            city=row.get("City"),
            county=county,
            zip=row.get("PostalCode"),
            asking_price=list_price,
            source_url=None,
            extra={
                "mls_status":         "Active",
                "mls_listing_id":     listing_id,
                "mls_listing_key":    row.get("ListingKey"),
                "list_price":         list_price,
                "tax_assessed_value": assessed,
                "below_assessed_pct": ratio_pct,    # positive = below assessed
                "days_on_market":     dom,
                "list_agent":         row.get("ListAgentFullName"),
                "list_office":        row.get("ListOfficeName"),
                "beds":               row.get("BedroomsTotal"),
                "baths":              row.get("BathroomsTotalInteger"),
                "sqft":               row.get("LivingArea"),
                "lot_sqft":           row.get("LotSizeSquareFeet"),
                "year_built":         row.get("YearBuilt"),
                "zoning":             row.get("Zoning"),
                "original_list_price": row.get("OriginalListPrice"),
                "previous_list_price": row.get("PreviousListPrice"),
            },
        )

    @staticmethod
    def _compose_addr(row: dict) -> str | None:
        parts = [
            str(row.get("StreetNumber") or "").strip(),
            row.get("StreetName") or "",
            row.get("StreetSuffix") or "",
        ]
        out = " ".join(p for p in parts if p).strip()
        return out or None


# ---------- standalone entrypoint ----------

async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    scraper = MotivatedSellerScraper()
    count = 0
    try:
        async for lead in scraper.run():
            count += 1
            if count <= 5:
                pct = (lead.extra or {}).get("below_assessed_pct")
                dom = (lead.extra or {}).get("days_on_market")
                log.info("  → %s | $%s | %s%% below assessed | %s DOM",
                         lead.raw_address or "?",
                         f"{lead.asking_price:,}" if lead.asking_price else "?",
                         pct, dom)
    finally:
        await scraper.close()
    log.info("Done. %d motivated-seller leads", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
