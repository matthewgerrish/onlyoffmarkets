"""
Probate-scraper base class.

WA Superior Courts don't expose a unified JSON API for case search —
each county runs its own HTML-form-based portal. So we build one
county-agnostic base that handles:

  • date-window search submission
  • result-list pagination
  • common field extraction (case number, filing date, decedent name,
    case type, case status)
  • polite rate-limiting (court servers are small, ancient, and will
    block you fast — 2s default between requests)
  • graceful no-op if the court site is down

Concrete county scrapers override `_search_url()`, `_parse_row()`,
and optionally `_next_page()`.

A probate filing rarely includes the decedent's property address in
the case caption — that requires pulling the actual case documents,
which are usually paywalled or PDF-trapped. For v1 we emit the
filing as a `RawLead` with the decedent's name and case metadata; a
follow-up enrichment pass cross-references the decedent name against
the ATTOM owner database to locate their properties.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import AsyncIterable, Iterable

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)


# Probate case-type codes across WA (varies by county's case-management system).
# We match on substrings — covers "Estate," "Probate," "Guardianship," "TEDRA," etc.
PROBATE_KEYWORDS = (
    "probate",
    "estate",
    "tedra",         # Trust and Estate Dispute Resolution Act
    "guardianship",
    "decedent",
)


class ProbateScraperBase(BaseScraper):
    source = "probate"
    rate_limit_sec = 2.0       # courts are slow + sensitive
    cache_ttl = 12 * 60 * 60   # 12h — probate filings don't churn hourly

    # Subclasses must set these
    county: str = ""                  # "Pierce" | "King" | "Thurston"
    source_name: str = ""

    def __init__(self, days_back: int = 30, **kw):
        super().__init__(**kw)
        self.days_back = days_back

    # ---------- abstract methods ----------

    def _search_url(self, start, end) -> tuple[str, dict]:
        """Return (url, params) for a probate search query for the date range."""
        raise NotImplementedError

    def _parse_row(self, row_element) -> RawLead | None:
        """Turn one result-table row into a RawLead. Return None to skip."""
        raise NotImplementedError

    def _result_rows(self, soup: BeautifulSoup) -> Iterable:
        """Pick the result rows out of the landing page HTML.
        Default: every `<tr>` inside a `.results` or `#searchResults` block.
        Override per-county."""
        return soup.select(".results tr, #searchResults tr, table.results tr")

    def _next_page_url(self, soup: BeautifulSoup, current: str) -> str | None:
        """Pagination hook — return next page URL or None to stop."""
        next_link = soup.select_one('a[rel="next"], a.next, a:-soup-contains("Next")')
        if next_link and next_link.get("href"):
            from urllib.parse import urljoin
            return urljoin(current, next_link["href"])
        return None

    # ---------- driver ----------

    async def run(self) -> AsyncIterable[RawLead]:
        end = datetime.utcnow().date()
        start = end - timedelta(days=self.days_back)
        url, params = self._search_url(start, end)

        log.info("%s Superior Court — probate filings %s → %s", self.county, start, end)
        pages = 0
        while url and pages < 10:   # safety cap
            pages += 1
            try:
                html = await self.get(url, params=params)
            except PermissionError:
                log.warning("robots.txt forbids %s — skipping", url)
                return
            except Exception as e:
                log.warning("Court fetch failed (%s): %s", url, e)
                return

            soup = BeautifulSoup(html, "html.parser")
            rows = list(self._result_rows(soup))
            log.info("  page %d: %d rows", pages, len(rows))

            for row in rows:
                try:
                    lead = self._parse_row(row)
                except Exception as e:
                    log.debug("row parse failed: %s", e)
                    continue
                if lead and self._is_probate(lead):
                    lead.county = self.county
                    yield lead

            next_url = self._next_page_url(soup, url)
            if not next_url or next_url == url:
                return
            url, params = next_url, {}

    # ---------- helpers ----------

    @staticmethod
    def _is_probate(lead: RawLead) -> bool:
        """Skip rows that aren't actually probate — some courts return mixed
        civil cases on the same search page."""
        case_type = (lead.extra or {}).get("case_type", "").lower()
        if not case_type:
            return True  # can't tell — keep it, the tag will sort it out downstream
        return any(k in case_type for k in PROBATE_KEYWORDS)

    @staticmethod
    def _parse_date(text: str | None, fmts: tuple[str, ...] = ("%m/%d/%Y", "%Y-%m-%d")) -> datetime | None:
        if not text:
            return None
        text = text.strip()
        for fmt in fmts:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _clean(text: str | None) -> str | None:
        return re.sub(r"\s+", " ", text.strip()) if text else None
