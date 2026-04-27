"""
Clear Recon Corp — upcoming WA trustee sales.

Clear Recon publishes sales at:
  https://www.clearreconcorp.com/washington-sales/

Typical column layout (looks similar to QLS / NWTS but order varies):
  TS Number | Sale Date | Borrower | Property Address | Opening Bid

We parse the sales table, filter to King + Pierce + Thurston. Same
fail-loud pattern on selector drift.

Run: `python -m scrapers.clear_recon`
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


class ClearReconScraper(TrusteeSaleScraperBase):
    trustee_name = "Clear Recon Corp"
    list_url = "https://www.clearreconcorp.com/washington-sales/"
    source_name = "Clear Recon (WA trustee sales)"

    async def run(self) -> AsyncIterable[RawLead]:
        try:
            html = await self.get(self.list_url)
        except Exception as e:
            log.warning("Clear Recon fetch failed: %s", e)
            return

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table.sales tr, table.trustee-sales tr, table.wp-block-table tr")
        if not rows:
            rows = soup.select("table tr")
        rows = [r for r in rows if r.find_all("td")]

        log.info("Clear Recon: %d total rows", len(rows))
        if not rows:
            log.warning(
                "Clear Recon: no rows parsed — selector drift? Inspect %s",
                self.list_url,
            )
            return

        count = 0
        for row in rows:
            lead = self._parse_row(row)
            if lead and lead.county in TARGET_COUNTIES:
                count += 1
                yield lead
        log.info("Clear Recon: %d WA sales yielded", count)

    def _parse_row(self, row) -> RawLead | None:
        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        ts_num    = self._clean(cells[0].get_text())
        sale_date = self.parse_date(cells[1].get_text())
        borrower  = self._clean(cells[2].get_text()) if len(cells) > 2 else None
        address   = self._clean(cells[3].get_text())
        bid_text  = cells[4].get_text() if len(cells) > 4 else ""

        if not ts_num or not sale_date:
            return None

        city = None
        if address and "," in address:
            parts = [p.strip() for p in address.split(",")]
            if len(parts) >= 2:
                city = parts[-1]
        county = self.infer_county(city)

        return self.make_lead(
            trustee_sale_num=ts_num,
            address=address,
            city=city,
            county=county,
            sale_date=sale_date,
            opening_bid=self.parse_dollars(bid_text),
            borrower=borrower,
        )

    @staticmethod
    def _clean(text: str | None) -> str | None:
        return re.sub(r"\s+", " ", text.strip()) if text else None


async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = ClearReconScraper()
    count = 0
    try:
        async for lead in s.run():
            count += 1
            if count <= 5:
                log.info("  → %s | %s | sale %s | bid $%s",
                         (lead.extra or {}).get("trustee_sale_num", "?"),
                         lead.raw_address or "?",
                         lead.sale_date.date() if lead.sale_date else "?",
                         f"{lead.opening_bid:,}" if lead.opening_bid else "?")
    finally:
        await s.close()
    log.info("Clear Recon: %d leads", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
