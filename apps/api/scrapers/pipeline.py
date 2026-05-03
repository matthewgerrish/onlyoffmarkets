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
from datetime import datetime, timezone
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
from scrapers.attom_national import AttomNationalScraper
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

# Commercial nationwide APIs (PROPERTYRADAR_API_KEY / BATCHDATA_API_KEY)
from scrapers.propertyradar import (
    PreforeclosurePR, AuctionPR, TaxLienPR, ProbatePR,
    VacantPR, AbsenteePR, HighEquityPR,
)
from scrapers.batchdata import (
    PreforeclosureBD, AuctionBD, TaxLienBD,
    VacantBD, AbsenteeBD, HighEquityBD,
)
from scrapers.nyc_violations import NYCViolationsScraper
from scrapers.chicago_violations import ChicagoViolationsScraper
from scrapers.sf_permits import SFPermitsScraper
from scrapers.philly_violations import PhillyViolationsScraper

from storage.off_market_db import upsert
from storage import scraper_runs_db

log = logging.getLogger(__name__)


# Registration order: free + local-source scrapers first, commercial APIs
# layered on top (they upgrade/dedupe records via shared parcel keys).
SCRAPERS: dict[str, Type[BaseScraper]] = {
    # ---- COMMERCIAL — NATIONWIDE (paid APIs, set keys to activate) ----
    # PropertyRadar — single best ROI for nationwide distress data.
    "pr-preforeclosure": PreforeclosurePR,
    "pr-auction":        AuctionPR,
    "pr-tax-lien":       TaxLienPR,
    "pr-probate":        ProbatePR,
    "pr-vacant":         VacantPR,
    "pr-absentee":       AbsenteePR,
    "pr-high-equity":    HighEquityPR,

    # BatchData — same key as skip-trace, double-duty.
    "bd-preforeclosure": PreforeclosureBD,
    "bd-auction":        AuctionBD,
    "bd-tax-lien":       TaxLienBD,
    "bd-vacant":         VacantBD,
    "bd-absentee":       AbsenteeBD,
    "bd-high-equity":    HighEquityBD,

    # ATTOM — already integrated; can stay layered for cross-validation.
    "attom":             AttomScraper,
    "attom-absentee":    AttomAbsenteeScraper,
    "attom-national":    AttomNationalScraper,

    # ---- CITY (free + public, no API key required) ----
    # Top-4 metro distress-signal scrapers using each city's open-data
    # platform (Socrata for NYC/Chicago/SF, Carto for Philly).
    "nyc-violations":     NYCViolationsScraper,        # NYC DOB violations
    "chicago-violations": ChicagoViolationsScraper,    # Chicago building violations
    "sf-permits":         SFPermitsScraper,            # SF stalled permits
    "philly-violations":  PhillyViolationsScraper,     # Philadelphia L&I violations

    # The four below need browser-rendered scraping — they hit ASP.NET /
    # JS-driven endpoints and yield ~0 with pure HTTP. Kept registered so
    # /admin/scrapers shows their (deserved) red status. Replace with
    # paid PropertyRadar / BatchData equivalents.
    "hud-homestore":   HudHomestoreScraper,
    "homepath":        HomePathScraper,
    "auction-com":     AuctionComScraper,
    "craigslist-fsbo": CraigslistFSBOScraper,

    # ---- LICENSED APIs (other) ----
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
    """Run a single scraper, persist results, return a run summary.

    Logs every attempt to scraper_runs for /admin/scrapers visibility,
    even when the scraper crashes mid-run.
    """
    scraper = cls()
    started_dt = datetime.now(timezone.utc)
    started = time.monotonic()
    count = 0
    persisted = 0
    errors = 0
    crash_note: str | None = None
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
    except Exception as e:
        crash_note = f"{type(e).__name__}: {e}"
        log.exception("Scraper %s crashed mid-run: %s", slug, e)
    finally:
        try:
            await scraper.close()
        except Exception:
            pass

    elapsed = round(time.monotonic() - started, 1)
    status = "error" if crash_note else ("empty" if count == 0 else "ok")

    # Best-effort telemetry. Won't take down the run if the table is missing.
    try:
        scraper_runs_db.record_run(
            slug,
            source=scraper.source,
            started_at=started_dt,
            finished_at=datetime.now(timezone.utc),
            scraped=count,
            persisted=persisted,
            errors=errors,
            elapsed_s=elapsed,
            status=status,
            note=crash_note,
        )
    except Exception as exc:
        log.warning("scraper_runs.record_run failed for %s: %s", slug, exc)

    return {
        "slug":     slug,
        "source":   scraper.source,
        "scraped":  count,
        "persisted": persisted,
        "errors":   errors,
        "elapsed_s": elapsed,
        "status":   status,
        "note":     crash_note,
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
