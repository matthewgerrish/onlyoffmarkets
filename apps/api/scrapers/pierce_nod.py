"""
Pierce County pre-foreclosure scraper.

Pulls Notice of Trustee Sale (NOTS) and Notice of Default (NOD)
filings from the Pierce County Auditor's recording system.

Public records. Access is free. Rate-limit is polite (1 req/sec).
Full source URL is kept on every record so agents can verify.

Data surface:
  Pierce County Auditor Recording Search:
    https://rd.co.pierce.wa.us/PIERCE/web/Search/DocumentSearch
  Document types we want:
    * NTS  — Notice of Trustee Sale
    * NOD  — Notice of Default
    * APP  — Appointment of Successor Trustee (often precedes)

Typical filing has:
  - Document number (stable ID)
  - Recording date
  - Grantor/Grantee (the property owner + the lender)
  - Legal description → street address
  - Default/original amount

Run: `python -m scrapers.pierce_nod`
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


SEARCH_URL = "https://rd.co.pierce.wa.us/PIERCE/web/Search/DocumentSearch"
# Document-type codes Pierce uses in its search dropdown.
DOC_TYPES = ["NTS", "NOD"]


class PierceNODScraper(BaseScraper):
    source = "preforeclosure"
    source_name = "Pierce County NOD/NTS filings"
    rate_limit_sec = 1.5  # be gentle — a county server

    async def run(self, days_back: int = 14) -> AsyncIterable[RawLead]:
        """Pull filings from the last `days_back` days (default 14)."""
        end = datetime.utcnow().date()
        start = end - timedelta(days=days_back)

        for doc_type in DOC_TYPES:
            async for lead in self._scrape_doc_type(doc_type, start, end):
                yield lead

    async def _scrape_doc_type(self, doc_type: str, start, end) -> AsyncIterable[RawLead]:
        params = {
            "DocType": doc_type,
            "RecordDateFrom": start.strftime("%m/%d/%Y"),
            "RecordDateTo":   end.strftime("%m/%d/%Y"),
        }
        try:
            html = await self.get(SEARCH_URL, params=params)
        except Exception as e:
            log.exception("Pierce NOD search failed for %s: %s", doc_type, e)
            return

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table.searchResults tr[data-docnum]")
        log.info("Pierce %s: %d rows found (%s → %s)", doc_type, len(rows), start, end)

        for row in rows:
            lead = self._parse_row(row, doc_type)
            if lead:
                yield lead

    def _parse_row(self, row, doc_type: str) -> RawLead | None:
        """Extract one filing from a result row. Defensive to missing fields."""
        doc_num = row.get("data-docnum")
        if not doc_num:
            return None

        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        recording_date_text = cells[0].get_text(strip=True)
        grantor_text        = cells[1].get_text(strip=True)
        legal_text          = cells[3].get_text(" ", strip=True)

        try:
            filing_date = datetime.strptime(recording_date_text, "%m/%d/%Y")
        except ValueError:
            filing_date = None

        # Try to extract street address from the legal description.
        address = self._extract_address(legal_text)

        # Try to parse default amount — often embedded in text or a hidden column.
        amount_text = row.get("data-defaultamount") or ""
        default_amount = self._parse_dollars(amount_text)

        return RawLead(
            source="preforeclosure",
            source_id=f"pierce-{doc_type}-{doc_num}",
            county="Pierce",
            raw_address=address,
            filing_date=filing_date,
            default_amount=default_amount,
            source_url=f"{SEARCH_URL}?DocNum={doc_num}",
            extra={
                "grantor": grantor_text,
                "legal_description": legal_text,
                "doc_type": doc_type,
                "doc_num": doc_num,
            },
        )

    @staticmethod
    def _extract_address(legal: str) -> str | None:
        """Pull a 'NNN Street Name St' pattern out of a legal description.
        Not bulletproof — legal descriptions are messy. Good enough to
        feed the address matcher, which will resolve to APN."""
        m = re.search(r"\b\d{2,6}\s+[A-Z][A-Za-z0-9'\- ]{2,40}\b(?=\s|,|;|$)", legal)
        return m.group(0) if m else None

    @staticmethod
    def _parse_dollars(text: str) -> int | None:
        m = re.search(r"\$?\s*([\d,]+(?:\.\d{2})?)", text)
        if not m:
            return None
        try:
            return int(float(m.group(1).replace(",", "")))
        except ValueError:
            return None


# ---------- standalone entrypoint ----------

async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    scraper = PierceNODScraper()
    count = 0
    try:
        async for lead in scraper.run(days_back=30):
            count += 1
            log.info("  → %s  |  %s  |  $%s",
                     lead.raw_address or "?",
                     lead.filing_date.date() if lead.filing_date else "?",
                     f"{lead.default_amount:,}" if lead.default_amount else "?")
    finally:
        await scraper.close()
    log.info("Done. %d leads scraped.", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
