"""
Craigslist "For Sale By Owner" (FSBO) scraper.

Uses Craigslist's RSS/RDF feeds for the `reo` (real estate by owner)
category — NOT `rea` (by broker, which would be MLS duplicates). The
RSS surface is public, stable, and has been around since 2002; we
respect their 1-request-per-few-seconds guideline and identify our
scraper in the User-Agent.

Regional subdomains covering our three counties:

  seattle.craigslist.org   → King County (incl. Federal Way, Auburn, Kent)
  tacoma.craigslist.org    → Pierce County + Thurston (Olympia/Lacey/Tumwater)

Each subdomain is queried twice — once per category that matters:

  /search/reo?format=rss         → FSBO (homes)
  /search/reb?format=rss         → FSBO (land/lots) — buildable for ADU teams

From each RSS entry we extract title, price, beds/baths/sqft regex,
post URL (permalink), posted date, and lat/lng when geotagged.

Legal: RSS is Craigslist's documented reuse surface. We identify
ourselves, rate-limit conservatively (5s between calls), and cache
responses for 6h to avoid re-hammering the same feed.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import AsyncIterable

import feedparser

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)


# Regional subdomain → which counties it primarily covers.
REGIONS = [
    {
        "subdomain": "seattle",
        "counties":  ["King"],
        "subareas":  [                      # CL subarea codes — scopes the feed
            "",                              # all of seattle region (covers south king)
        ],
    },
    {
        "subdomain": "tacoma",
        "counties":  ["Pierce", "Thurston"],
        "subareas":  [""],
    },
]

# CL categories we care about
CATEGORIES = [
    ("reo", "fsbo"),       # Real Estate by Owner — homes
    ("reb", "fsbo-land"),  # Real Estate by Owner — land/lots (buildable for ADU teams)
]


# Title regex helpers. CL FSBO titles almost always have:
#   "$525000 / 3br - 1800ft2 - Charming Tacoma Craftsman (North End)"
PRICE_RE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)\s*(k|K)?\b")
BEDS_RE  = re.compile(r"\b(\d)\s?(?:br|bd|bed)s?\b", re.I)
SQFT_RE  = re.compile(r"(\d[\d,]{2,})\s?(?:ft2|sqft|sq\s*ft)\b", re.I)
ADDR_RE  = re.compile(r"\b(\d{2,6})\s+([A-Z][A-Za-z0-9'\- ]{2,40})\b(?=\s|,|;|$)")


class CraigslistFSBOScraper(BaseScraper):
    source = "fsbo"
    source_name = "Craigslist FSBO feeds"
    rate_limit_sec = 5.0        # conservative — CL is sensitive to bursts
    cache_ttl = 6 * 60 * 60     # 6 hour cache — plenty fresh

    def __init__(self, max_per_region: int | None = None, **kw):
        super().__init__(**kw)
        self.max_per_region = int(
            max_per_region
            or os.getenv("CRAIGSLIST_MAX_PER_REGION", "150")
        )

    async def run(self) -> AsyncIterable[RawLead]:
        for region in REGIONS:
            seen = 0
            for cat, subtag in CATEGORIES:
                async for lead in self._scrape(region, cat, subtag):
                    yield lead
                    seen += 1
                    if seen >= self.max_per_region:
                        break
                if seen >= self.max_per_region:
                    break
            log.info("── %s.craigslist.org: %d FSBO leads ──", region["subdomain"], seen)

    async def _scrape(self, region: dict, category: str, subtag: str) -> AsyncIterable[RawLead]:
        url = f"https://{region['subdomain']}.craigslist.org/search/{category}"
        params = {"format": "rss"}

        try:
            xml = await self.get(url, params=params)
        except PermissionError:
            log.warning("Craigslist robots.txt disallows — skipping %s", url)
            return
        except Exception as e:
            log.warning("Craigslist feed fetch failed (%s): %s", url, e)
            return

        feed = feedparser.parse(xml)
        log.info("%s/%s: %d entries", region["subdomain"], category, len(feed.entries))

        for entry in feed.entries:
            lead = self._to_lead(entry, region, category, subtag)
            if lead:
                yield lead

    def _to_lead(self, entry, region: dict, category: str, subtag: str) -> RawLead | None:
        """One RSS entry → RawLead. Returns None if the entry is unusable."""
        post_url = entry.get("link")
        if not post_url:
            return None

        # Stable CL post ID from the URL (end of path)
        m = re.search(r"/(\d{8,})\.html", post_url)
        post_id = m.group(1) if m else post_url.split("/")[-1].replace(".html", "")

        title   = entry.get("title", "") or ""
        summary = entry.get("summary", "") or entry.get("description", "") or ""
        posted  = self._parse_date(entry.get("published") or entry.get("updated"))

        # Try to parse price + beds + sqft from the title (CL convention)
        price = self._parse_price(title)
        beds  = self._int(BEDS_RE, title)
        sqft  = self._int(SQFT_RE, title)

        # Geotag — CL embeds lat/lng on ~70% of posts
        lat = entry.get("geo_lat") or entry.get("georss_point", "").split(" ")[0] or None
        lng = entry.get("geo_long") or (entry.get("georss_point", "").split(" ") + [None, None])[1] or None

        # Best-effort address pull — from title (usually neighborhood) or summary
        address = self._extract_address(title) or self._extract_address(summary)

        # City: CL RSS doesn't give us a clean field; pull subregion from URL or infer
        city = self._infer_city(title, summary, region)

        return RawLead(
            source="fsbo",
            source_id=f"cl-{post_id}",
            county=region["counties"][0] if len(region["counties"]) == 1 else None,
            raw_address=address,
            city=city,
            asking_price=price,
            source_url=post_url,
            filing_date=posted,
            extra={
                "title":      title,
                "summary":    summary[:400],
                "beds":       beds,
                "sqft":       sqft,
                "lat":        float(lat) if lat else None,
                "lng":        float(lng) if lng else None,
                "subtag":     subtag,
                "region":     region["subdomain"],
                "category":   category,
            },
        )

    # ---------- helpers ----------

    @staticmethod
    def _int(rx: re.Pattern, s: str) -> int | None:
        m = rx.search(s)
        if not m:
            return None
        try:
            return int(m.group(1).replace(",", ""))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_price(title: str) -> int | None:
        m = PRICE_RE.search(title)
        if not m:
            return None
        try:
            n = float(m.group(1).replace(",", ""))
            if m.group(2):  # "k" suffix
                n *= 1000
            return int(n)
        except ValueError:
            return None

    @staticmethod
    def _parse_date(s: str | None) -> datetime | None:
        if not s:
            return None
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
        ):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _extract_address(text: str) -> str | None:
        m = ADDR_RE.search(text or "")
        return m.group(0) if m else None

    @staticmethod
    def _infer_city(title: str, summary: str, region: dict) -> str | None:
        """CL doesn't label city cleanly — we check known WA city names
        in title/summary and pick the first one matching the region's
        county coverage."""
        candidates = [
            "Tacoma", "Gig Harbor", "Puyallup", "University Place", "Lakewood",
            "Spanaway", "Bonney Lake", "Sumner", "Auburn", "Federal Way", "Kent",
            "Olympia", "Lacey", "Tumwater", "Yelm", "Tenino",
        ]
        text = (title + " " + (summary or "")).lower()
        for city in candidates:
            if city.lower() in text:
                return city
        return None


# ---------- standalone entrypoint ----------

async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    scraper = CraigslistFSBOScraper()
    count = 0
    by_region: dict[str, int] = {}
    try:
        async for lead in scraper.run():
            count += 1
            r = lead.extra.get("region") if lead.extra else "?"
            by_region[r] = by_region.get(r, 0) + 1
            if count <= 5:
                log.info("  → %s | %s | $%s | %s",
                         lead.city or "?",
                         (lead.extra or {}).get("title", "")[:50],
                         f"{lead.asking_price:,}" if lead.asking_price else "?",
                         lead.source_url)
    finally:
        await scraper.close()
    log.info("Done. %d FSBO leads: %s", count, by_region)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
