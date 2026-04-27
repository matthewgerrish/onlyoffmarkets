"""
Expired + Canceled MLS scraper (NWMLS via Trestle).

Unlike the other scrapers in this directory, this one does NOT hit a
county recorder, courthouse, or third-party site. It queries the
NWMLS Trestle RESO API for listings whose `StandardStatus` is
`Expired`, `Withdrawn`, or `Canceled` — the three statuses RESO uses
for "this listing didn't sell and the contract is over."

Why these are off-market gold:

  Expired   : Seller listed for the full agreement period (typically 6
              months) and never closed. Almost always a pricing or
              marketing problem; the owner is often relisting later
              with a new agent.

  Withdrawn : Seller pulled the listing mid-agreement — frustrated,
              relocating internally, decided to wait, or fired their
              agent. Highest motivation in the bunch.

  Canceled  : Listing agreement terminated by mutual consent. Mid-way
              between Withdrawn and Expired in seller frustration.

In our taxonomy:
  RESO `Expired`               → source = "expired"
  RESO `Withdrawn` | `Canceled`→ source = "canceled"

Trestle gives us last list price, listing duration, and the listing
key/MLS#. We treat each row as a `RawLead` and let the pipeline
normalize against the canonical property record.

Trestle credentials are required (settings.trestle_client_id). If
not configured, the scraper logs a warning and yields nothing —
safe to leave registered in `pipeline.SCRAPERS`.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import AsyncIterable

from config import settings
from scrapers.base import BaseScraper
from scrapers.models import RawLead
from trestle import trestle

log = logging.getLogger(__name__)


# RESO StandardStatus → our source taxonomy
STATUS_MAP = {
    "Expired":   "expired",
    "Withdrawn": "canceled",
    "Canceled":  "canceled",
}

# Counties we cover. Trestle `CountyOrParish` values follow the
# "<Name> County" or just "<Name>" convention depending on the dataset.
COUNTIES = ("King", "Pierce", "Thurston")

# Rolling 3-month lookback window. Older expired/canceled listings are
# stale — sellers have usually re-listed, sold off-market, or mentally
# moved on, so the conversion rate on direct outreach drops sharply
# past the 90-day mark. Override via env var `MLS_EXPIRED_LOOKBACK_DAYS`
# if you want a wider or narrower funnel.
LOOKBACK_DAYS = int(os.getenv("MLS_EXPIRED_LOOKBACK_DAYS", "90"))


class MLSExpiredCanceledScraper(BaseScraper):
    source = "expired"          # base label; per-lead source is set from status
    source_name = "NWMLS expired/canceled (Trestle)"
    rate_limit_sec = 0.0        # Trestle is OAuth-rate-limited server-side
    cache_ttl = 6 * 60 * 60

    async def run(self) -> AsyncIterable[RawLead]:
        if not settings.trestle_client_id:
            log.warning("Trestle not configured — skipping expired/canceled scraper")
            return

        cutoff = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
        statuses = list(STATUS_MAP.keys())
        # OData `in` operator: StandardStatus in ('Expired','Withdrawn','Canceled')
        status_filter = " or ".join(f"StandardStatus eq '{s}'" for s in statuses)
        county_filter = " or ".join(f"CountyOrParish eq '{c}'" for c in COUNTIES) + \
                        " or " + " or ".join(f"CountyOrParish eq '{c} County'" for c in COUNTIES)
        date_filter = f"StatusChangeTimestamp ge {cutoff}"

        params = {
            "$filter": f"({status_filter}) and ({county_filter}) and {date_filter}",
            "$orderby": "StatusChangeTimestamp desc",
            "$top": 200,
            "$skip": 0,
        }

        total = 0
        while True:
            try:
                rows = await trestle.query("Property", params)
            except Exception as e:
                log.exception("Trestle query failed: %s", e)
                break
            if not rows:
                break

            for row in rows:
                lead = self._to_lead(row)
                if lead:
                    yield lead
                    total += 1

            params["$skip"] += len(rows)
            if len(rows) < params["$top"]:
                break  # last page

        log.info("── NWMLS expired/canceled: %d leads", total)

    def _to_lead(self, row: dict) -> RawLead | None:
        status = row.get("StandardStatus")
        src = STATUS_MAP.get(status)
        if not src:
            return None

        listing_id = row.get("ListingId") or row.get("ListingKey")
        if not listing_id:
            return None

        last_price = row.get("ListPrice") or row.get("OriginalListPrice")
        list_dt    = self._parse_dt(row.get("OnMarketDate") or row.get("ListDate"))
        change_dt  = self._parse_dt(row.get("StatusChangeTimestamp"))

        days_listed = None
        if list_dt and change_dt:
            days_listed = max(0, (change_dt - list_dt).days)

        county = (row.get("CountyOrParish") or "").replace(" County", "").strip() or None
        city   = row.get("City") or None
        addr   = row.get("UnparsedAddress") or self._compose_addr(row)
        apn    = row.get("ParcelNumber") or None

        return RawLead(
            source=src,
            source_id=f"nwmls-{listing_id}",
            scraped_at=datetime.utcnow(),
            raw_address=addr,
            parcel_apn=apn,
            city=city,
            county=county,
            zip=row.get("PostalCode"),
            asking_price=int(last_price) if last_price else None,
            filing_date=change_dt,         # when status flipped to expired/canceled
            source_url=None,                # NWMLS detail URLs require auth
            extra={
                "mls_status":         status,
                "mls_listing_id":     listing_id,
                "mls_listing_key":    row.get("ListingKey"),
                "original_list_price": row.get("OriginalListPrice"),
                "last_list_price":    last_price,
                "days_listed":        days_listed,
                "list_agent":         row.get("ListAgentFullName"),
                "list_office":        row.get("ListOfficeName"),
                "beds":               row.get("BedroomsTotal"),
                "baths":              row.get("BathroomsTotalInteger"),
                "sqft":               row.get("LivingArea"),
                "lot_sqft":           row.get("LotSizeSquareFeet"),
                "year_built":         row.get("YearBuilt"),
                "zoning":             row.get("Zoning"),
            },
        )

    @staticmethod
    def _parse_dt(s: str | None) -> datetime | None:
        if not s:
            return None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None

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
    scraper = MLSExpiredCanceledScraper()
    count = 0
    by_src: dict[str, int] = {}
    try:
        async for lead in scraper.run():
            count += 1
            by_src[lead.source] = by_src.get(lead.source, 0) + 1
            if count <= 5:
                log.info("  → %s | %s | $%s | %s",
                         lead.source,
                         lead.raw_address or "?",
                         f"{lead.asking_price:,}" if lead.asking_price else "?",
                         (lead.extra or {}).get("mls_listing_id"))
    finally:
        await scraper.close()
    log.info("Done. %d leads: %s", count, by_src)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
