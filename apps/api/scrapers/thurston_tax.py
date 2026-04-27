"""
Thurston County Treasurer — annual tax-foreclosure list.

Thurston publishes the upcoming tax-foreclosure sale list at:
  https://www.thurstoncountywa.gov/departments/treasurer/tax-foreclosure

Landing page has the current-year PDF. Volume is small — typically
50–120 parcels/year — but high-signal (Thurston's overall inventory
is smaller, so each tax-foreclosure parcel represents a larger share
of the local market than in King or Pierce).

Run: `python -m scrapers.thurston_tax`
"""
from __future__ import annotations

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.tax_delinquent_base import TaxDelinquentScraperBase, parse_pdf_tables
from scrapers.pierce_tax import _clean

log = logging.getLogger(__name__)


LANDING_URL = "https://www.thurstoncountywa.gov/departments/treasurer/tax-foreclosure"


class ThurstonTaxScraper(TaxDelinquentScraperBase):
    county = "Thurston"
    source_name = "Thurston County Treasurer — Tax Foreclosure"

    async def _source_document_url(self) -> str | None:
        try:
            html = await self.get(LANDING_URL)
        except Exception as e:
            log.warning("Thurston tax landing fetch failed: %s", e)
            return None

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(" ", strip=True).lower()
            if not href.lower().endswith(".pdf"):
                continue
            if "foreclos" in text or "foreclos" in href.lower():
                return urljoin(LANDING_URL, href)

        log.warning(
            "Thurston tax: no .pdf link containing 'foreclos' found at %s.",
            LANDING_URL,
        )
        return None

    def _parse_document(self, content: bytes, content_type: str) -> list[dict]:
        if "pdf" not in content_type and not content[:4] == b"%PDF":
            log.warning("Thurston tax: doc is not a PDF (ctype=%s)", content_type)
            return []

        tables = parse_pdf_tables(content)
        log.info("Thurston tax PDF: %d tables extracted", len(tables))
        parcels: list[dict] = []
        for table in tables:
            parcels.extend(self._parse_table(table))
        return parcels

    COL_SYNONYMS = {
        "apn":              ("parcel", "apn", "pin"),
        "owner":            ("owner", "taxpayer", "name"),
        "address":          ("situs", "address", "property"),
        "lien_amount":      ("total", "owed", "amount", "delinquent", "due"),
        "years_delinquent": ("years", "year"),
        "sale_date":        ("sale", "auction"),
    }

    def _parse_table(self, table: list[list[str]]) -> list[dict]:
        if not table:
            return []
        header = [(c or "").strip().lower() for c in table[0]]
        col_index = {}
        for field, keywords in self.COL_SYNONYMS.items():
            for i, cell in enumerate(header):
                if any(k in cell for k in keywords):
                    col_index[field] = i
                    break
        if "apn" not in col_index:
            return []
        out = []
        for row in table[1:]:
            if not any(row):
                continue
            parcel = {"document_type": "Thurston tax-foreclosure PDF"}
            for field, i in col_index.items():
                if i < len(row):
                    parcel[field] = _clean(row[i])
            if parcel.get("apn"):
                out.append(parcel)
        return out


async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = ThurstonTaxScraper()
    count = 0
    try:
        async for lead in s.run():
            count += 1
            if count <= 5:
                log.info("  → APN %s | %s | owed $%s",
                         lead.parcel_apn or "?",
                         lead.raw_address or "?",
                         f"{lead.lien_amount:,}" if lead.lien_amount else "?")
    finally:
        await s.close()
    log.info("Thurston tax foreclosure: %d parcels", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
