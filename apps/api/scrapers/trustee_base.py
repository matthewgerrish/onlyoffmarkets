"""
Base class for trustee-sale scrapers.

Trustee companies post upcoming foreclosure auctions as either HTML
tables or PDFs. The schema is consistent across companies — borrower,
property, sale date, opening bid — so we share the RawLead shape and
let subclasses handle the source-specific extraction.

Big WA trustees this module is designed for:
  • Quality Loan Service Corporation (QLS)          — scrapers/quality_loan.py
  • Northwest Trustee Services (NWTS)               — scrapers/nwts.py
  • Bishop, Marshall & Weibel                       — scrapers/bishop_marshall.py
  • Clear Recon Corp                                — scrapers/clear_recon.py
  • MTC Financial (Trustee Corps)                   — scrapers/mtc.py

Common gotchas we handle here:
  - Sale-date parsing across trustee-specific formats
  - Dollar amount normalization ("$125,000.00" → 125000)
  - Sale-location canonicalization (courthouse steps etc. — kept as-is,
    displayed verbatim)
  - PDF tabular extraction via pdfplumber (when source is PDF)
  - Two-pass URL fetch: list → per-sale detail (some trustees paginate,
    others show everything on one page)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import AsyncIterable

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)


class TrusteeSaleScraperBase(BaseScraper):
    source = "auction"
    rate_limit_sec = 3.0          # trustee sites are usually small — be extra polite
    cache_ttl = 6 * 60 * 60       # 6h — new sale notices typically roll in weekly

    # Subclasses override
    trustee_name: str = ""        # "Quality Loan Service Corporation"
    list_url: str = ""            # public URL that lists upcoming sales

    # ---------- abstract ----------

    async def run(self) -> AsyncIterable[RawLead]:
        """Subclass yields RawLead per upcoming sale."""
        raise NotImplementedError
        yield

    # ---------- shared helpers ----------

    def make_lead(
        self,
        *,
        trustee_sale_num: str,
        address: str | None,
        city: str | None,
        county: str | None,
        sale_date: datetime | None,
        opening_bid: int | None,
        borrower: str | None = None,
        lender: str | None = None,
        source_url: str | None = None,
        extra: dict | None = None,
    ) -> RawLead:
        """Build a RawLead with the trustee-sale-specific fields mapped into
        our shared schema. Use this from subclass parsers."""
        return RawLead(
            source="auction",
            source_id=f"{self._slug()}-{trustee_sale_num}",
            county=county,
            city=city,
            raw_address=address,
            sale_date=sale_date,
            opening_bid=opening_bid,
            source_url=source_url or self.list_url,
            extra={
                "trustee":           self.trustee_name,
                "trustee_sale_num":  trustee_sale_num,
                "borrower":          borrower,
                "lender":            lender,
                **(extra or {}),
            },
        )

    def _slug(self) -> str:
        """Stable source-id prefix — lowercased trustee name, no spaces."""
        return re.sub(r"[^a-z0-9]", "", (self.trustee_name or "trustee").lower())

    # ---------- parsing utilities ----------

    @staticmethod
    def parse_dollars(text: str | None) -> int | None:
        """'$1,234.56' → 1234. Ignores the cents."""
        if not text:
            return None
        m = re.search(r"\$?\s*([\d,]+(?:\.\d{2})?)", text)
        if not m:
            return None
        try:
            return int(float(m.group(1).replace(",", "")))
        except ValueError:
            return None

    @staticmethod
    def parse_date(text: str | None) -> datetime | None:
        """Try the date formats trustees commonly use."""
        if not text:
            return None
        text = text.strip()
        for fmt in (
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y-%m-%d",
            "%B %d, %Y",        # "January 15, 2026"
            "%b %d, %Y",        # "Jan 15, 2026"
            "%m/%d/%y",
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def infer_county(city: str | None) -> str | None:
        """Light county mapping for WA cities we know. Extend as needed."""
        if not city:
            return None
        c = city.strip().lower()
        if c in ("tacoma", "gig harbor", "puyallup", "university place", "lakewood",
                 "spanaway", "bonney lake", "sumner", "fife", "milton"):
            return "Pierce"
        if c in ("seattle", "bellevue", "redmond", "kirkland", "federal way",
                 "auburn", "kent", "renton", "sammamish", "issaquah", "burien"):
            return "King"
        if c in ("olympia", "lacey", "tumwater", "yelm", "tenino"):
            return "Thurston"
        return None
