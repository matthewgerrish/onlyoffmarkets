"""
Pierce County Superior Court — probate filings.

Pierce uses LINX (Local Information eXchange) for case search at
https://linx.co.pierce.wa.us/. The probate search supports a date
range and returns an HTML results table.

Source URL template:
  https://linx.co.pierce.wa.us/linxweb/Main/CaseSearchByCaseType.aspx
    ?caseType=Probate&fromDate=...&toDate=...

Each row in the results table gives us:
  • Case number (e.g., 25-4-12345-5 — the "4" is the probate classifier)
  • Filing date
  • Case title (usually "Estate of JOHN SMITH (deceased)")
  • Case status

Run: `python -m scrapers.pierce_probate`
"""
from __future__ import annotations

import re
from scrapers.probate_base import ProbateScraperBase
from scrapers.models import RawLead


SEARCH_URL = "https://linx.co.pierce.wa.us/linxweb/Main/CaseSearchByCaseType.aspx"


class PierceProbateScraper(ProbateScraperBase):
    county = "Pierce"
    source_name = "Pierce County Superior Court — Probate"

    def _search_url(self, start, end) -> tuple[str, dict]:
        return SEARCH_URL, {
            "caseType":    "Probate",
            "fromDate":    start.strftime("%m/%d/%Y"),
            "toDate":      end.strftime("%m/%d/%Y"),
            "pageSize":    "100",
        }

    def _parse_row(self, row) -> RawLead | None:
        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        case_num  = self._clean(cells[0].get_text())
        file_date = self._parse_date(cells[1].get_text().strip())
        title     = self._clean(cells[2].get_text())       # "ESTATE OF JOHN SMITH"
        case_type = self._clean(cells[3].get_text()) if len(cells) > 3 else "Probate"

        if not case_num or not title:
            return None

        decedent = self._extract_decedent(title)

        return RawLead(
            source="probate",
            source_id=f"pierce-probate-{case_num}",
            county="Pierce",
            # Probate filings have no address in the case caption —
            # enrichment step will cross-reference decedent name against
            # ATTOM owner database to locate properties.
            raw_address=None,
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
        """'ESTATE OF JOHN SMITH, DECEASED' → 'JOHN SMITH'"""
        if not title:
            return None
        m = re.search(r"ESTATE OF\s+(.+?)(?:,|\s+DECEASED|\s+\(|$)", title, re.I)
        if m:
            return m.group(1).strip().title()
        # Guardianship pattern
        m = re.search(r"GUARDIANSHIP OF\s+(.+?)(?:,|\s+\(|$)", title, re.I)
        if m:
            return m.group(1).strip().title()
        return title.strip().title()


# ---------- standalone ----------

async def main():
    import asyncio, logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)-30s %(message)s")
    s = PierceProbateScraper(days_back=30)
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
    logging.info("Pierce probate: %d leads", count)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
