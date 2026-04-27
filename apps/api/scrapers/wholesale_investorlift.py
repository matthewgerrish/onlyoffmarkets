"""
Wholesale deals scraper — InvestorLift partner API.

Pulls assignment-of-contract deals from InvestorLift's wholesaler
marketplace into our `wholesale` source category. These are properties
already under contract by a wholesaler who is now looking to assign
that contract to a cash buyer at a discount, typically requiring a
7–14 day cash close and a non-refundable earnest money deposit.

This integration is GATED on credentials. Until you have:

  1. A paid InvestorLift partner account
  2. An API key issued under your account
  3. Confirmation that the API endpoint paths and JSON shape below
     match your account's contract (InvestorLift's docs are partner-
     gated, so the field names below are placeholders you will
     verify against your account)

…the scraper will detect the missing API key, log a single warning,
and yield nothing — exactly the same pattern as `mls_expired.py` when
Trestle creds are absent. Safe to leave registered in the pipeline.

Configuration (server/.env):

  INVESTORLIFT_API_KEY=<your key>
  INVESTORLIFT_BASE_URL=https://api.investorlift.com/v1   # confirm exact path
  INVESTORLIFT_MARKET_FILTER=WA                            # state, city, or zip list

If InvestorLift access is hard to come by, alternative wholesale-deal
feeds we can swap in with minimal code change:

  - DealMachine API
  - PropStream wholesale list export
  - BatchData / BatchLeads
  - Manual entry via Follow Up Boss custom fields

The interface is identical — yield `RawLead`s with source="wholesale".
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import AsyncIterable

import httpx

from config import settings
from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)


# Pagination chunk size. InvestorLift docs typically allow 50–100 per page.
PAGE_SIZE = int(os.getenv("INVESTORLIFT_PAGE_SIZE", "50"))

# Soft cap to keep one nightly run bounded. Override via env.
MAX_PER_RUN = int(os.getenv("INVESTORLIFT_MAX_PER_RUN", "500"))


class WholesaleInvestorLiftScraper(BaseScraper):
    source = "wholesale"
    source_name = "InvestorLift wholesaler marketplace"
    rate_limit_sec = 1.0       # gentle — partner API, no need to hammer
    cache_ttl = 4 * 60 * 60    # 4 hour cache; deals turn over fast

    async def run(self) -> AsyncIterable[RawLead]:
        if not settings.investorlift_api_key:
            log.warning(
                "InvestorLift not configured (INVESTORLIFT_API_KEY missing) — "
                "skipping wholesale scraper. Add credentials to enable."
            )
            return

        base = settings.investorlift_base_url.rstrip("/")
        market = settings.investorlift_market_filter
        headers = {
            "Authorization": f"Bearer {settings.investorlift_api_key}",
            "Accept": "application/json",
            "User-Agent": "PRP-buyer-site/1.0 (matthew@contactprp.com)",
        }

        page = 1
        total = 0
        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            while total < MAX_PER_RUN:
                params = {
                    "market":   market,            # confirm exact param name in your IL docs
                    "page":     page,
                    "per_page": PAGE_SIZE,
                    "status":   "active",          # only available, not-yet-assigned deals
                }
                try:
                    r = await client.get(f"{base}/properties", params=params)
                    r.raise_for_status()
                    payload = r.json()
                except httpx.HTTPStatusError as e:
                    log.error("InvestorLift HTTP %s: %s", e.response.status_code, e.response.text[:200])
                    return
                except Exception as e:
                    log.exception("InvestorLift fetch failed: %s", e)
                    return

                # Field name `properties` is a placeholder — verify in IL docs.
                # Common conventions: `data`, `results`, `deals`, `items`.
                rows = payload.get("properties") or payload.get("data") or []
                if not rows:
                    break

                for row in rows:
                    lead = self._to_lead(row)
                    if lead:
                        yield lead
                        total += 1
                        if total >= MAX_PER_RUN:
                            break

                # Stop on incomplete page (last page reached).
                if len(rows) < PAGE_SIZE:
                    break
                page += 1

        log.info("── InvestorLift wholesale: %d deals", total)

    def _to_lead(self, row: dict) -> RawLead | None:
        """Map an InvestorLift deal record → RawLead.

        Field names below are educated guesses based on industry-standard
        wholesaler-platform JSON schemas. Reconcile against your actual
        InvestorLift API response and adjust this mapper accordingly.
        """
        deal_id = row.get("id") or row.get("deal_id") or row.get("property_id")
        if not deal_id:
            return None

        addr   = row.get("address") or row.get("street_address")
        city   = row.get("city")
        state  = row.get("state") or "WA"
        zip_   = row.get("zip") or row.get("postal_code")
        county = row.get("county")

        # Wholesale-specific economics
        asking_price   = self._int(row.get("asking_price") or row.get("price"))
        arv            = self._int(row.get("arv") or row.get("after_repair_value"))
        rehab_estimate = self._int(row.get("rehab") or row.get("rehab_estimate"))
        assignment_fee = self._int(row.get("assignment_fee"))
        emd            = self._int(row.get("emd") or row.get("earnest_money"))

        spread_pct = None
        if asking_price and arv and arv > 0:
            spread_pct = round(100 * (arv - asking_price) / arv, 1)

        return RawLead(
            source="wholesale",
            source_id=f"il-{deal_id}",
            scraped_at=datetime.utcnow(),
            raw_address=addr,
            parcel_apn=row.get("parcel_apn") or row.get("apn"),
            city=city,
            state=state,
            zip=zip_,
            county=county,
            asking_price=asking_price,
            source_url=row.get("url") or row.get("listing_url"),
            extra={
                "wholesaler_name":   row.get("wholesaler") or row.get("seller"),
                "wholesaler_phone":  row.get("wholesaler_phone"),
                "asking_price":      asking_price,
                "arv":               arv,
                "rehab_estimate":    rehab_estimate,
                "assignment_fee":    assignment_fee,
                "emd_required":      emd,
                "spread_pct":        spread_pct,    # (ARV - asking) / ARV
                "close_days":        row.get("close_days") or row.get("days_to_close"),
                "cash_only":         row.get("cash_only", True),
                "beds":              row.get("beds"),
                "baths":             row.get("baths"),
                "sqft":              row.get("sqft"),
                "year_built":        row.get("year_built"),
                "condition":         row.get("condition"),
                "photo_count":       len(row.get("photos") or []),
            },
        )

    @staticmethod
    def _int(v) -> int | None:
        if v is None or v == "":
            return None
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None


# ---------- standalone entrypoint ----------

async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    scraper = WholesaleInvestorLiftScraper()
    count = 0
    try:
        async for lead in scraper.run():
            count += 1
            if count <= 5:
                e = lead.extra or {}
                log.info(
                    "  → %s | $%s asking | ARV $%s | %.1f%% spread | wholesaler: %s",
                    lead.raw_address or "?",
                    f"{lead.asking_price:,}" if lead.asking_price else "?",
                    f"{e.get('arv'):,}" if e.get("arv") else "?",
                    e.get("spread_pct") or 0,
                    e.get("wholesaler_name") or "?",
                )
    finally:
        await scraper.close()
    log.info("Done. %d wholesale deals", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
