"""
Base class for tax-delinquent scrapers.

Each WA county treasurer publishes an annual **tax foreclosure list** —
the parcels scheduled to hit the courthouse steps for unpaid taxes.
This is the highest-signal tax-lien lead type. A separate, much larger
**general delinquency list** exists (owners who owe anything at all) —
we deliberately don't chase that here; the signal-to-noise ratio is
worse and it's the same lead source we already surface via absentee +
pre-foreclosure scrapers.

Publication cadence and format:
  • List published once a year (typically Aug–Oct, sale in Nov–Dec)
  • Monthly revisions remove paid-off parcels
  • Format varies by county — some publish PDFs, others XLSX/CSV

Per-parcel fields in the list (schema is consistent across counties):
  • APN / tax parcel number
  • Street address
  • Owner of record
  • Years delinquent
  • Total lien amount
  • Minimum opening bid (if auction scheduled)

Subclasses implement `_source_document_url()` + `_parse_document()`.
The base class handles the PDF-or-HTML branching and the standard
RawLead wrapping.
"""
from __future__ import annotations

import io
import logging
import re
from datetime import datetime
from typing import AsyncIterable

import httpx

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)


class TaxDelinquentScraperBase(BaseScraper):
    source = "tax-lien"
    rate_limit_sec = 3.0
    cache_ttl = 24 * 60 * 60     # 24h — lists change daily-ish during sale prep

    # Subclasses override
    county: str = ""
    source_name: str = ""

    # ---------- abstract ----------

    async def _source_document_url(self) -> str | None:
        """Resolve and return the current-year tax-foreclosure document URL.
        Most treasurer sites change URLs each year — typically the URL
        itself is predictable (contains the year), or there's a landing
        page that links to the current doc."""
        raise NotImplementedError

    def _parse_document(self, content: bytes, content_type: str) -> list[dict]:
        """Parse the raw document bytes → a list of parcel dicts.

        Each dict should have (all optional, use what the doc provides):
          apn, address, owner, years_delinquent, lien_amount,
          opening_bid, sale_date (str or datetime).
        """
        raise NotImplementedError

    # ---------- driver ----------

    async def run(self) -> AsyncIterable[RawLead]:
        doc_url = await self._source_document_url()
        if not doc_url:
            log.warning(
                "%s: could not resolve tax-foreclosure document URL — treasurer "
                "page layout may have changed. Check `_source_document_url()`.",
                self.county,
            )
            return

        try:
            content, ctype = await self._fetch_document(doc_url)
        except Exception as e:
            log.warning("%s: failed to fetch %s — %s", self.county, doc_url, e)
            return

        log.info("%s: parsing %d-byte %s document …", self.county, len(content), ctype)

        try:
            parcels = self._parse_document(content, ctype)
        except Exception as e:
            log.exception("%s: parse failed — %s", self.county, e)
            return

        log.info("%s: %d tax-foreclosure parcels parsed", self.county, len(parcels))

        for p in parcels:
            yield self._to_lead(p, doc_url)

    # ---------- helpers ----------

    async def _fetch_document(self, url: str) -> tuple[bytes, str]:
        """Fetch raw bytes (not through the cached HTML helper — PDFs are binary).
        Returns (content, content-type)."""
        await self._throttle()
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True,
                                     headers=self._client.headers) as c:
            r = await c.get(url)
            r.raise_for_status()
            return r.content, (r.headers.get("content-type") or "").lower()

    def _to_lead(self, parcel: dict, source_url: str) -> RawLead:
        """Wrap a parsed parcel dict in the canonical RawLead shape."""
        sale_date = parcel.get("sale_date")
        if isinstance(sale_date, str):
            sale_date = _parse_date(sale_date)

        apn = parcel.get("apn") or ""
        return RawLead(
            source="tax-lien",
            source_id=f"{self.county.lower()}-tax-{apn}",
            county=self.county,
            raw_address=parcel.get("address"),
            parcel_apn=apn or None,
            sale_date=sale_date,
            lien_amount=_int(parcel.get("lien_amount")),
            opening_bid=_int(parcel.get("opening_bid")),
            years_delinquent=_int(parcel.get("years_delinquent")),
            source_url=source_url,
            extra={
                "owner":          parcel.get("owner"),
                "document_type":  parcel.get("document_type"),
                "raw":            {k: v for k, v in parcel.items()
                                   if k not in ("apn", "address", "owner",
                                                "years_delinquent", "lien_amount",
                                                "opening_bid", "sale_date")},
            },
        )


# ---------- parse helpers ----------

def _int(v) -> int | None:
    if v in (None, "", 0):
        return None
    try:
        return int(float(str(v).replace(",", "").replace("$", "")))
    except (ValueError, TypeError):
        return None


def _parse_date(text: str) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


# ---------- PDF parsing utility (shared across county scrapers) ----------

def parse_pdf_tables(content: bytes) -> list[list[list[str]]]:
    """Extract all tables from a PDF, one list-of-rows per table.
    Wrapper around pdfplumber so county scrapers don't need to import it."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber not installed — run `pip install pdfplumber`")

    tables = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for t in page.extract_tables() or []:
                if t:
                    tables.append(t)
    return tables


def parse_pdf_text(content: bytes) -> str:
    """Full text of a PDF as a single string. Useful when the document
    uses visual layout rather than proper tables."""
    import pdfplumber
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)
