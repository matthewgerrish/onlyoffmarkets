"""
Pierce County Treasurer — annual tax-foreclosure list.

Pierce publishes the upcoming tax-foreclosure sale list on the
treasurer's tax-foreclosure page:
  https://www.piercecountywa.gov/6048/Tax-Foreclosure

The page links to the current-year foreclosure PDF (filename
typically contains the year). We resolve that link dynamically —
rather than hardcoding the file path — so the scraper keeps working
across year rollovers without code changes.

The PDF has a standard tabular layout:
  Parcel # | Owner | Address | Total Owed | Years | Sale Date

Pierce typically holds the tax sale in mid-November with the list
published in August. Volumes: 200–400 parcels per year.

Run: `python -m scrapers.pierce_tax`
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.tax_delinquent_base import TaxDelinquentScraperBase, parse_pdf_tables

log = logging.getLogger(__name__)


LANDING_URL = "https://www.piercecountywa.gov/6048/Tax-Foreclosure"


class PierceTaxScraper(TaxDelinquentScraperBase):
    county = "Pierce"
    source_name = "Pierce County Treasurer — Tax Foreclosure"

    async def _source_document_url(self) -> str | None:
        """Scrape the landing page for a link to the current PDF.
        Heuristic: first <a> whose href or text contains 'foreclosure' + 'list'
        and whose URL ends in .pdf."""
        try:
            html = await self.get(LANDING_URL)
        except Exception as e:
            log.warning("Pierce tax landing fetch failed: %s", e)
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
            "Pierce tax: no .pdf link containing 'foreclos' found at %s — "
            "check the landing page for the current-year file name.",
            LANDING_URL,
        )
        return None

    def _parse_document(self, content: bytes, content_type: str) -> list[dict]:
        if "pdf" not in content_type and not content[:4] == b"%PDF":
            log.warning("Pierce tax: doc is not a PDF (content-type=%s).", content_type)
            return []

        tables = parse_pdf_tables(content)
        log.info("Pierce tax PDF: %d tables extracted", len(tables))

        parcels: list[dict] = []
        for table in tables:
            parcels.extend(self._parse_table(table))
        return parcels

    # ---------- table parsing ----------

    # Expected column order on Pierce's foreclosure PDF. The header often looks
    # something like: ["Parcel #", "Owner", "Address", "Total Owed", "Years",
    # "Sale Date"]. We find the header row and then map subsequent rows.
    COL_SYNONYMS = {
        "apn":              ("parcel", "apn", "pin"),
        "owner":            ("owner", "taxpayer"),
        "address":          ("situs", "address", "property"),
        "lien_amount":      ("total", "owed", "amount", "delinquent"),
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
            log.debug("Pierce tax table skipped — no APN column in header: %s", header)
            return []

        out: list[dict] = []
        for row in table[1:]:
            if not any(row):
                continue
            parcel = {"document_type": "Pierce tax-foreclosure PDF"}
            for field, i in col_index.items():
                if i < len(row):
                    parcel[field] = _clean(row[i])
            if parcel.get("apn"):
                out.append(parcel)
        return out


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    return re.sub(r"\s+", " ", str(text).strip()) or None


# ---------- standalone ----------

async def main():
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = PierceTaxScraper()
    count = 0
    try:
        async for lead in s.run():
            count += 1
            if count <= 5:
                log.info("  → APN %s | %s | owed $%s | %s yrs",
                         lead.parcel_apn or "?",
                         lead.raw_address or "?",
                         f"{lead.lien_amount:,}" if lead.lien_amount else "?",
                         lead.years_delinquent or "?")
    finally:
        await s.close()
    log.info("Pierce tax foreclosure: %d parcels", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
