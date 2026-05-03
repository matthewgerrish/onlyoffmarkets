"""Philadelphia L&I Violations — Carto SQL API.

Different platform than Socrata: Philly's open data lives on Carto's
public SQL API. Same general shape — public read, no auth, paginated
SQL queries. Dataset has every Licenses & Inspections violation
filed citywide, with address + casetype + caseStatus.

Endpoint:
  https://phl.carto.com/api/v2/sql?q=<urlencoded SQL>
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import AsyncIterable
from urllib.parse import quote

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)

CARTO_BASE = "https://phl.carto.com/api/v2/sql"


class PhillyViolationsScraper(BaseScraper):
    source = "vacant"
    source_name = "Philadelphia L&I Violations (Carto SQL)"
    rate_limit_sec = 0.3

    def __init__(self, days_back: int = 30, **kw):
        super().__init__(**kw)
        self.days_back = days_back

    async def run(self) -> AsyncIterable[RawLead]:
        cutoff = (datetime.utcnow() - timedelta(days=self.days_back)).strftime("%Y-%m-%d")
        page_size = 1000
        offset = 0
        max_pages = 10

        for page in range(max_pages):
            sql = (
                "SELECT casenumber, casetype, casestatus, casecreateddate, "
                "       violationnumber, violationdate, violationcode, "
                "       violationcodetitle, address, parcel_id_num, "
                "       ST_X(the_geom) as lng, ST_Y(the_geom) as lat "
                "FROM violations "
                f"WHERE violationdate >= '{cutoff}' "
                "AND casestatus IN ('OPEN','IN VIOLATION') "
                f"ORDER BY violationdate DESC LIMIT {page_size} OFFSET {offset}"
            )
            url = f"{CARTO_BASE}?q={quote(sql)}"
            try:
                text = await self.get(url)
            except Exception as e:
                log.warning("Philly fetch failed: %s", e)
                return
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                return
            rows = payload.get("rows") or []
            if not rows:
                return
            for r in rows:
                lead = self._to_lead(r)
                if lead:
                    yield lead
            if len(rows) < page_size:
                return
            offset += page_size

    @staticmethod
    def _to_lead(r: dict) -> RawLead | None:
        addr = (r.get("address") or "").strip()
        viol = r.get("violationnumber") or r.get("casenumber")
        if not addr or not viol:
            return None
        try:
            issue_date = datetime.fromisoformat(
                str(r["violationdate"]).replace("Z", "+00:00")
            ) if r.get("violationdate") else None
        except Exception:
            issue_date = None
        try:
            lat = float(r["lat"]) if r.get("lat") is not None else None
            lng = float(r["lng"]) if r.get("lng") is not None else None
        except (TypeError, ValueError):
            lat = lng = None
        return RawLead(
            source="vacant",
            source_id=f"phl-li-{viol}",
            raw_address=addr,
            city="Philadelphia",
            county="Philadelphia",
            state="PA",
            parcel_apn=str(r.get("parcel_id_num")) if r.get("parcel_id_num") else None,
            latitude=lat,
            longitude=lng,
            filing_date=issue_date,
            source_url=(
                f"https://www.opendataphilly.org/dataset/licenses-and-inspections-violations?case={r.get('casenumber')}"
            ),
            extra={
                "case_type": r.get("casetype"),
                "case_status": r.get("casestatus"),
                "violation_code": r.get("violationcode"),
                "violation_code_title": r.get("violationcodetitle"),
            },
        )
