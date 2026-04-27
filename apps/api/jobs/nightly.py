"""
Nightly scraping job — intended to be invoked by cron at ~2am local.

  cron entry (crontab -e):
  0 2 * * *  cd /srv/buyer-site/server && .venv/bin/python -m jobs.nightly >> logs/nightly.log 2>&1

The job:
  1. Runs every scraper in `scrapers/pipeline.py`
  2. After persistence, invalidates the `off-market:*` cache prefix so
     the API serves fresh data on next request
  3. Emits a summary line that fits in one log entry
  4. Exits non-zero if any scraper errored — cron catches the mail

That's it. No queueing, no sharding. Nightly is plenty for the volumes
involved here (~300-500 new filings/week across all three counties).
"""
from __future__ import annotations

import asyncio
import logging
import sys

from scrapers.pipeline import run_all
from cache import cache


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)-32s %(message)s",
    )
    log = logging.getLogger("nightly")
    log.info("── Nightly off-market pipeline starting ──")

    results = await run_all()
    errored = sum(1 for r in results if r.get("error") or r.get("errors", 0) > 0)
    persisted = sum(r.get("persisted", 0) for r in results)
    scraped = sum(r.get("scraped", 0) for r in results)

    # Invalidate cached API responses so the next hit sees the new data.
    await cache.invalidate_prefix("off-market:")

    log.info(
        "── Nightly complete: %d scraped, %d persisted across %d scrapers (%d errored) ──",
        scraped, persisted, len(results), errored,
    )

    return 0 if errored == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
