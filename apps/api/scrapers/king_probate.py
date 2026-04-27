"""
King County Superior Court — probate filings.

King runs case search through the Department of Judicial Administration
(DJA) eClerk system:
  https://dja-prd-ecexapp.kingcounty.gov/

Key case-type code for probate filings: `4` (the middle digit of the
WA case-number schema "YY-4-NNNNN-K"). The search form takes:

  • caseTypeCode = 4       (Probate)
  • fromDate / toDate      (mm/dd/yyyy)
  • page / pageSize

Same caveats as king_nod.py — ASP.NET-ish server, 2s throttle,
selectors may drift over time. Base probate class handles filtering,
pagination, and the probate-keyword sanity check.

Run: `python -m scrapers.king_probate`
"""
from __future__ import annotations

import re
from scrapers.probate_base import ProbateScraperBase
from scrapers.models import RawLead


SEARCH_URL = "https://dja-prd-ecexapp.kingcounty.gov/CaseAccess/Search/CaseByType"


class KingProbateScraper(ProbateScraperBase):
    county = "King"
    source_name = "King County Superior Court — Probate"

    def _search_url(self, start, end) -> tuple[str, dict]:
        return SEARCH_URL, {
            "caseTypeCode": "4",                        # Probate
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

        decedent = self._extract_decedent(title)

        return RawLead(
            source="probate",
            source_id=f"king-probate-{case_num}",
            county="King",
            raw_address=None,       # caption lacks address — ATTOM enrichment fills this
            filing_date=file_date,
            source_url=f"{SEARCH_URL}?caseNum={case_num}",
            extra={
                "case_number":   case_num,
                "case_title":    title,
                "case_type":     case_type,
                "decedent_name": decedent,
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
    s = KingProbateScraper(days_back=30)
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
    logging.info("King probate: %d leads", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
