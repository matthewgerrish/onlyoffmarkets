"""
Scraper orchestration.

Runs every registered scraper, streams RawLeads through the address
matcher, and persists them via `storage.off_market_db`. Each scraper
runs sequentially (not in parallel) so we stay polite to county
servers — total runtime is measured in minutes, not hours, and we
only run nightly.

Register new scrapers in `SCRAPERS` below. A scraper is just a class
with a `source` attr and an async `run()` that yields RawLead.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import time
from typing import Type

from scrapers.base import BaseScraper
from scrapers.pierce_nod import PierceNODScraper
from scrapers.pierce_probate import PierceProbateScraper
from scrapers.king_nod import KingNODScraper
from scrapers.king_probate import KingProbateScraper
from scrapers.thurston_nod import ThurstonNODScraper
from scrapers.thurston_probate import ThurstonProbateScraper
from scrapers.attom import AttomScraper
from scrapers.attom_absentee import AttomAbsenteeScraper
from scrapers.craigslist_fsbo import CraigslistFSBOScraper
from scrapers.mls_expired import MLSExpiredCanceledScraper
from scrapers.motivated_seller import MotivatedSellerScraper
from scrapers.wholesale_investorlift import WholesaleInvestorLiftScraper
from scrapers.quality_loan import QualityLoanScraper
from scrapers.nwts import NWTSScraper
from scrapers.clear_recon import ClearReconScraper
from scrapers.pierce_tax import PierceTaxScraper
from scrapers.king_tax import KingTaxScraper
from scrapers.thurston_tax import ThurstonTaxScraper

from storage.off_market_db import upsert

log = logging.getLogger(__name__)


# Registration order: free + local-source scrapers first, commercial APIs
# layered on top (they upgrade/dedupe records via shared parcel keys).
SCRAPERS: dict[str, Type[BaseScraper]] = {
    "pierce-nod":       PierceNODScraper,
    "pierce-probate":   PierceProbateScraper,
    "king-nod":         KingNODScraper,
    "king-probate":     KingProbateScraper,
    "thurston-nod":     ThurstonNODScraper,
    "thurston-probate": ThurstonProbateScraper,
    "craigslist-fsbo":  CraigslistFSBOScraper,  # RSS-based, free, highest-volume FSBO
    "trustee-qls":        QualityLoanScraper,    # Quality Loan Service auctions
    "trustee-nwts":       NWTSScraper,           # Northwest Trustee Services auctions
    "trustee-clearrecon": ClearReconScraper,     # Clear Recon Corp auctions
    "pierce-tax":         PierceTaxScraper,      # annual Pierce tax-foreclosure list
    "king-tax":           KingTaxScraper,        # annual King tax-foreclosure list
    "thurston-tax":       ThurstonTaxScraper,    # annual Thurston tax-foreclosure list
    "attom-absentee":   AttomAbsenteeScraper,   # Property+Sales bundle — active today
    "attom":            AttomScraper,           # Foreclosure bundle — active once added
    "mls-expired-canceled": MLSExpiredCanceledScraper,  # Trestle status filter (Expired/Withdrawn/Canceled)
    "motivated-seller":     MotivatedSellerScraper,     # Active listings ≤ tax-assessed, DOM > 30
    "wholesale-il":         WholesaleInvestorLiftScraper,  # InvestorLift wholesaler marketplace API
}


async def run_one(slug: str, cls: Type[BaseScraper]) -> dict:
    """Run a single scraper, persist results, return a run summary."""
    scraper = cls()
    started = time.monotonic()
    count = 0
    persisted = 0
    errors = 0
    try:
        async for lead in scraper.run():
            count += 1
            try:
                key = upsert(lead)
                if key:
                    persisted += 1
            except Exception as e:
                errors += 1
                log.exception("Persist failed for %s/%s: %s", lead.source, lead.source_id, e)
    finally:
        await scraper.close()

    return {
        "slug":     slug,
        "source":   scraper.source,
        "scraped":  count,
        "persisted": persisted,
        "errors":   errors,
        "elapsed_s": round(time.monotonic() - started, 1),
    }


async def run_all(only: list[str] | None = None) -> list[dict]:
    """Run every registered scraper (or a filtered subset) sequentially."""
    results = []
    for slug, cls in SCRAPERS.items():
        if only and slug not in only:
            continue
        log.info("── Running %s ──", slug)
        try:
            r = await run_one(slug, cls)
            results.append(r)
            log.info("  ✓ %s: %d scraped, %d persisted, %d errors (%.1fs)",
                     r["slug"], r["scraped"], r["persisted"], r["errors"], r["elapsed_s"])
        except Exception as e:
            log.exception("Scraper %s crashed: %s", slug, e)
            results.append({"slug": slug, "error": str(e)})
    return results


def main():
    p = argparse.ArgumentParser(description="Run off-market scrapers.")
    p.add_argument("--source", nargs="+", default=None,
                   help="One or more scraper slugs. Default: all. "
                        f"Available: {', '.join(SCRAPERS.keys())}")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)-32s %(message)s",
    )
    results = asyncio.run(run_all(only=args.source))

    print("\n═══ Pipeline summary ═══")
    for r in results:
        print(f"  {r}")


if __name__ == "__main__":
    main()
