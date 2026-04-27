"""
Thurston County Auditor — pre-foreclosure filings (NOD + NOTS).

Thurston publishes recording data through the Auditor's Records
Online portal:
  https://recordsonline.thurstoncountywa.gov/

The search form takes document type + recording-date range and
returns paginated HTML results. Structure is simpler than King's
ASP.NET app — no viewstate — but the server is small, so same
2s throttle and 12h cache apply.

Document type codes:
  NTS  — Notice of Trustee Sale
  NOD  — Notice of Default

Run: `python -m scrapers.thurston_nod`
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


SEARCH_URL = "https://recordsonline.thurstoncountywa.gov/search.aspx"
DOC_TYPES  = ["NTS", "NOD"]


class ThurstonNODScraper(BaseScraper):
    source = "preforeclosure"
    source_name = "Thurston County NOD/NTS filings"
    rate_limit_sec = 2.0

    async def run(self, days_back: int = 14) -> AsyncIterable[RawLead]:
        end = datetime.utcnow().date()
        start = end - timedelta(days=days_back)

        for doc_type in DOC_TYPES:
            async for lead in self._search(doc_type, start, end):
                yield lead

    async def _search(self, doc_type, start, end) -> AsyncIterable[RawLead]:
        params = {
            "docType":     doc_type,
            "fromDate":    start.strftime("%m/%d/%Y"),
            "toDate":      end.strftime("%m/%d/%Y"),
            "pageSize":    "100",
        }
        try:
            html = await self.get(SEARCH_URL, params=params)
        except Exception as e:
            log.warning("Thurston %s search failed: %s", doc_type, e)
            return

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table.results tr, #gvRecordings tr, tr[data-docnum]")

        if not rows:
            # fail-loud if selectors drift
            log.warning(
                "Thurston %s: no result rows parsed — selector change? Inspect %s.",
                doc_type, SEARCH_URL,
            )
            return

        log.info("Thurston %s: %d rows (%s → %s)", doc_type, len(rows), start, end)

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
            source_id=f"thurston-{doc_type}-{doc_num}",
            county="Thurston",
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
    s = ThurstonNODScraper()
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
    log.info("Thurston NOD: %d leads", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
