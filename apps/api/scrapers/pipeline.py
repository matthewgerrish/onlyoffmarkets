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
from scrapers.wholesale_investorlift import WholesaleInvestorLiftScraper
from scrapers.quality_loan import QualityLoanScraper
from scrapers.nwts import NWTSScraper
from scrapers.clear_recon import ClearReconScraper
from scrapers.pierce_tax import PierceTaxScraper
from scrapers.king_tax import KingTaxScraper
from scrapers.thurston_tax import ThurstonTaxScraper

# Nationwide public-source scrapers (no API key required)
from scrapers.hud_homestore import HudHomestoreScraper
from scrapers.homepath import HomePathScraper
from scrapers.auction_com import AuctionComScraper

from storage.off_market_db import upsert

log = logging.getLogger(__name__)


# Registration order: free + local-source scrapers first, commercial APIs
# layered on top (they upgrade/dedupe records via shared parcel keys).
SCRAPERS: dict[str, Type[BaseScraper]] = {
    # ---- NATIONWIDE (free + public) ----
    "hud-homestore":   HudHomestoreScraper,    # HUD REO listings
    "homepath":        HomePathScraper,         # Fannie Mae REO
    "auction-com":     AuctionComScraper,       # Auction.com search feed
    "craigslist-fsbo": CraigslistFSBOScraper,  # RSS-based FSBO

    # ---- LICENSED APIs (set API keys to enable) ----
    "attom":           AttomScraper,            # ATTOM foreclosure bundle (national)
    "attom-absentee":  AttomAbsenteeScraper,    # ATTOM property+sales (absentee)
    "wholesale-il":    WholesaleInvestorLiftScraper,  # InvestorLift wholesaler marketplace

    # ---- WA COUNTY (free + public) ----
    "pierce-nod":       PierceNODScraper,
    "pierce-probate":   PierceProbateScraper,
    "pierce-tax":       PierceTaxScraper,
    "king-nod":         KingNODScraper,
    "king-probate":     KingProbateScraper,
    "king-tax":         KingTaxScraper,
    "thurston-nod":     ThurstonNODScraper,
    "thurston-probate": ThurstonProbateScraper,
    "thurston-tax":     ThurstonTaxScraper,

    # ---- TRUSTEE / AUCTION SERVICES (national, public sale lists) ----
    "trustee-qls":        QualityLoanScraper,
    "trustee-nwts":       NWTSScraper,
    "trustee-clearrecon": ClearReconScraper,
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
