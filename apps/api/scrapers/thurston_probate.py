"""
Thurston County Superior Court — probate filings.

Thurston publishes case data through Court Records Online:
  https://cfr.thurstoncountywa.gov/

Same case-type code as King (`4` = Probate per WA's statewide
case-number schema). Smaller volume than King/Pierce (~20–40
probate filings/month) but higher signal per filing — Thurston
estates are typically larger and more rural (acreage, ADU potential).

Run: `python -m scrapers.thurston_probate`
"""
from __future__ import annotations

import re
from scrapers.probate_base import ProbateScraperBase
from scrapers.models import RawLead


SEARCH_URL = "https://cfr.thurstoncountywa.gov/CaseSearch/CaseSearchByType"


class ThurstonProbateScraper(ProbateScraperBase):
    county = "Thurston"
    source_name = "Thurston County Superior Court — Probate"

    def _search_url(self, start, end) -> tuple[str, dict]:
        return SEARCH_URL, {
            "caseTypeCode": "4",                         # Probate
            "fromDate":     start.strftime("%m/%d/%Y"),
            "toDate":       end.strftime("%m/%d/%Y"),
            "pageSize":     "100",
        }

    def _parse_row(self, row) -> RawLead | None:
        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        case_num  = self._clean(cells[0].get_text())
        file_date = self._parse_date(cells[1].get_text().strip())
        title     = self._clean(cells[2].get_text())
        case_type = self._clean(cells[3].get_text()) if len(cells) > 3 else "Probate"

        if not case_num or not title:
            return None

        return RawLead(
            source="probate",
            source_id=f"thurston-probate-{case_num}",
            county="Thurston",
            raw_address=None,       # caption lacks address — ATTOM enrichment fills this
            filing_date=file_date,
            source_url=f"{SEARCH_URL}?caseNum={case_num}",
            extra={
                "case_number":   case_num,
                "case_title":    title,
                "case_type":     case_type,
                "decedent_name": self._extract_decedent(title),
            },
        )

    @staticmethod
    def _extract_decedent(title: str) -> str | None:
        if not title:
            return None
        m = re.search(r"ESTATE OF\s+(.+?)(?:,|\s+DECEASED|\s+\(|$)", title, re.I)
        if m:
            return m.group(1).strip().title()
        m = re.search(r"GUARDIANSHIP OF\s+(.+?)(?:,|\s+\(|$)", title, re.I)
        if m:
            return m.group(1).strip().title()
        return title.strip().title()


async def main():
    import asyncio, logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = ThurstonProbateScraper(days_back=30)
    count = 0
    try:
        async for lead in s.run():
            count += 1
            if count <= 5:
                logging.info("  → %s | %s | filed %s",
                             (lead.extra or {}).get("case_number"),
                             (lead.extra or {}).get("decedent_name"),
                             lead.filing_date.date() if lead.filing_date else "?")
    finally:
        await s.close()
    logging.info("Thurston probate: %d leads", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
