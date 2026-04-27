"""
King County Recorder — pre-foreclosure filings (NOD + NOTS).

King uses an ASP.NET-driven instrument search at:
  https://recording.kingcounty.gov/Search/instruments.aspx

Two things that make King harder than Pierce:

  1. ASP.NET __VIEWSTATE  — the form requires a viewstate/eventvalidation
     token pulled from the landing page before you can POST a search.
     We do the GET once to harvest tokens, then POST for each page.
  2. Document-type codes differ slightly — King uses `NTS` for Notice of
     Trustee Sale and `NOD` for Notice of Default.

Rate limit is deliberately slow (2s) — the King County servers are
small, get cranky under load, and have been known to return blanket
500s to anyone hitting them more than ~1 req/sec.

Because selectors on ASP.NET forms shift over time, this file is
designed to fail loud rather than silently: if the landing page
doesn't yield a viewstate token, we bail with a clear log line so a
human can look at the HTML and fix the selector. Cheaper than
silently emitting zero leads every night.

Run: `python -m scrapers.king_nod`
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import AsyncIterable

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)


SEARCH_URL = "https://recording.kingcounty.gov/Search/instruments.aspx"
DOC_TYPES  = ["NTS", "NOD"]


class KingNODScraper(BaseScraper):
    source = "preforeclosure"
    source_name = "King County NOD/NTS filings"
    rate_limit_sec = 2.0

    async def run(self, days_back: int = 14) -> AsyncIterable[RawLead]:
        end = datetime.utcnow().date()
        start = end - timedelta(days=days_back)

        # Step 1: GET landing to pick up __VIEWSTATE + __EVENTVALIDATION
        try:
            landing = await self.get(SEARCH_URL, use_cache=False)
        except Exception as e:
            log.warning("King landing fetch failed: %s — aborting.", e)
            return

        soup = BeautifulSoup(landing, "html.parser")
        viewstate = self._hidden(soup, "__VIEWSTATE")
        eventval  = self._hidden(soup, "__EVENTVALIDATION")
        if not viewstate:
            log.error(
                "King Recorder: no __VIEWSTATE on landing page — selector change? "
                "Inspect %s and update `_hidden()`.", SEARCH_URL,
            )
            return

        # Step 2: for each doc type, POST the search and parse results
        for doc_type in DOC_TYPES:
            async for lead in self._search(doc_type, start, end, viewstate, eventval):
                yield lead

    async def _search(self, doc_type, start, end, viewstate, eventval) -> AsyncIterable[RawLead]:
        # ASP.NET form field names on King's search — may drift; verify against live HTML
        form = {
            "__VIEWSTATE":        viewstate,
            "__EVENTVALIDATION":  eventval or "",
            "ctl00$MainContent$ddlDocumentType":   doc_type,
            "ctl00$MainContent$txtRecordDateFrom": start.strftime("%m/%d/%Y"),
            "ctl00$MainContent$txtRecordDateTo":   end.strftime("%m/%d/%Y"),
            "ctl00$MainContent$btnSearch":         "Search",
        }
        # The base-class `get()` caches — for POST we use raw client.
        await self._throttle()
        try:
            r = await self._client.post(SEARCH_URL, data=form)
            r.raise_for_status()
            html = r.text
        except Exception as e:
            log.warning("King %s search failed: %s", doc_type, e)
            return

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table.searchResults tr, #gvResults tr")
        log.info("King %s: %d rows (%s → %s)", doc_type, len(rows), start, end)

        for row in rows:
            lead = self._parse_row(row, doc_type)
            if lead:
                yield lead

    def _parse_row(self, row, doc_type: str) -> RawLead | None:
        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        doc_num  = self._clean(cells[0].get_text())
        rec_date = self._parse_date(cells[1].get_text().strip())
        grantor  = self._clean(cells[2].get_text())
        legal    = self._clean(cells[3].get_text())

        if not doc_num or not rec_date:
            return None

        return RawLead(
            source="preforeclosure",
            source_id=f"king-{doc_type}-{doc_num}",
            county="King",
            raw_address=self._extract_address(legal),
            filing_date=rec_date,
            source_url=f"{SEARCH_URL}?docNum={doc_num}",
            extra={
                "doc_type":          doc_type,
                "doc_num":           doc_num,
                "grantor":           grantor,
                "legal_description": legal,
            },
        )

    # ---------- helpers ----------

    @staticmethod
    def _hidden(soup: BeautifulSoup, name: str) -> str | None:
        el = soup.find("input", {"name": name})
        return el.get("value") if el else None

    @staticmethod
    def _clean(text: str | None) -> str | None:
        return re.sub(r"\s+", " ", text.strip()) if text else None

    @staticmethod
    def _parse_date(text: str) -> datetime | None:
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except (ValueError, TypeError):
                continue
        return None

    @staticmethod
    def _extract_address(legal: str | None) -> str | None:
        if not legal:
            return None
        m = re.search(r"\b\d{2,6}\s+[A-Z][A-Za-z0-9'\- ]{2,40}\b(?=\s|,|;|$)", legal)
        return m.group(0) if m else None


async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = KingNODScraper()
    count = 0
    try:
        async for lead in s.run(days_back=30):
            count += 1
            if count <= 5:
                log.info("  → %s | %s | filed %s",
                         lead.raw_address or "?",
                         (lead.extra or {}).get("grantor", "?"),
                         lead.filing_date.date() if lead.filing_date else "?")
    finally:
        await s.close()
    log.info("King NOD: %d leads", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
