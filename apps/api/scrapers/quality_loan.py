"""
Quality Loan Service Corporation (QLS) — upcoming trustee sales scraper.

QLS publishes upcoming Washington trustee sales at:
  https://www.qualityloan.com/sale-information/washington-sales/

The page renders an HTML table with columns (typical layout):
  TS Number | Sale Date | Opening Bid | Property Address | City | County | Borrower

Each row is one scheduled auction. We filter to King, Pierce, and
Thurston counties during parsing — other counties are ignored.

If QLS shifts the page structure, the scraper emits a loud warning
log identifying the URL and zero rows — 10-minute fix to update the
table selector.

Run: `python -m scrapers.quality_loan`
"""
from __future__ import annotations

import logging
import re
from typing import AsyncIterable

from bs4 import BeautifulSoup

from scrapers.trustee_base import TrusteeSaleScraperBase
from scrapers.models import RawLead

log = logging.getLogger(__name__)


TARGET_COUNTIES = {"King", "Pierce", "Thurston"}


class QualityLoanScraper(TrusteeSaleScraperBase):
    trustee_name = "Quality Loan Service Corporation"
    list_url = "https://www.qualityloan.com/sale-information/washington-sales/"
    source_name = "Quality Loan Service (WA trustee sales)"

    async def run(self) -> AsyncIterable[RawLead]:
        try:
            html = await self.get(self.list_url)
        except Exception as e:
            log.warning("QLS fetch failed: %s", e)
            return

        soup = BeautifulSoup(html, "html.parser")

        # Primary: table under the sales listing. Fallback selectors if QLS changes.
        rows = soup.select("table.sales-list tr, table.trustee-sales tr, table#salesTable tr")
        if not rows:
            rows = soup.select("table tr")   # last-resort — any table

        rows = [r for r in rows if r.find_all("td")]    # drop header-only rows
        log.info("QLS: %d total sale rows on page", len(rows))

        if not rows:
            log.warning(
                "QLS: no sale rows found — selector change? Inspect %s and update "
                "`rows = soup.select(...)` in the scraper.", self.list_url
            )
            return

        count = 0
        for row in rows:
            lead = self._parse_row(row)
            if lead and lead.county in TARGET_COUNTIES:
                count += 1
                yield lead
        log.info("QLS: %d WA sales yielded (King + Pierce + Thurston)", count)

    def _parse_row(self, row) -> RawLead | None:
        cells = row.find_all("td")
        if len(cells) < 5:
            return None

        ts_num     = self._clean(cells[0].get_text())
        sale_date  = self.parse_date(cells[1].get_text())
        bid_text   = cells[2].get_text()
        address    = self._clean(cells[3].get_text())
        city       = self._clean(cells[4].get_text()) if len(cells) > 4 else None
        county     = self._clean(cells[5].get_text()) if len(cells) > 5 else None
        borrower   = self._clean(cells[6].get_text()) if len(cells) > 6 else None

        # Normalize county — QLS sometimes writes "Pierce County" vs "Pierce"
        if county:
            county = county.replace("County", "").strip()
        # Fall back to city-based inference if county missing
        county = county or self.infer_county(city)

        if not ts_num or not sale_date:
            return None

        return self.make_lead(
            trustee_sale_num=ts_num,
            address=address,
            city=city,
            county=county,
            sale_date=sale_date,
            opening_bid=self.parse_dollars(bid_text),
            borrower=borrower,
            source_url=self.list_url,
            extra={
                "raw_county_text": cells[5].get_text(strip=True) if len(cells) > 5 else None,
            },
        )

    @staticmethod
    def _clean(text: str | None) -> str | None:
        return re.sub(r"\s+", " ", text.strip()) if text else None


# ---------- standalone ----------

async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = QualityLoanScraper()
    count = 0
    try:
        async for lead in s.run():
            count += 1
            if count <= 5:
                log.info("  → %s | %s | sale %s | bid $%s",
                         (lead.extra or {}).get("trustee_sale_num", "?"),
                         f"{lead.raw_address or '?'}, {lead.city or '?'}",
                         lead.sale_date.date() if lead.sale_date else "?",
                         f"{lead.opening_bid:,}" if lead.opening_bid else "?")
    finally:
        await s.close()
    log.info("QLS trustee sales: %d leads", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
