"""San Francisco Building Permits — Socrata Open Data.

Dataset i98e-djp9. Stalled / withdrawn permits are a strong distress
proxy: someone started a project on the property, then ran out of
money, time, or motivation. We filter to permits with status
"withdrawn", "cancelled", "expired", or filed >180 days ago and still
"filed" (= never moved forward).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import AsyncIterable

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)

API_URL = "https://data.sfgov.org/resource/i98e-djp9.json"


class SFPermitsScraper(BaseScraper):
    source = "vacant"
    source_name = "San Francisco stalled permits (Socrata)"
    rate_limit_sec = 0.3

    def __init__(self, stalled_days: int = 180, **kw):
        super().__init__(**kw)
        self.stalled_days = stalled_days

    async def run(self) -> AsyncIterable[RawLead]:
        cutoff_old = (datetime.utcnow() - timedelta(days=self.stalled_days)).strftime("%Y-%m-%d")
        offset = 0
        page_size = 1000
        max_pages = 10

        for page in range(max_pages):
            params = {
                "$where": (
                    f"(status in ('withdrawn','cancelled','expired')) "
                    f"OR (status = 'filed' AND filed_date < '{cutoff_old}T00:00:00')"
                ),
                "$select": (
                    "permit_number, permit_type_definition, filed_date, "
                    "issued_date, status, status_date, block, lot, "
                    "street_number, street_name, street_suffix, description, zipcode"
                ),
                "$limit": str(page_size),
                "$offset": str(offset),
                "$order": "filed_date DESC",
            }
            try:
                text = await self.get(API_URL, params=params)
            except Exception as e:
                log.warning("SF fetch failed: %s", e)
                return
            try:
                rows = json.loads(text)
            except json.JSONDecodeError:
                return
            if not isinstance(rows, list) or not rows:
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
        num = (r.get("street_number") or "").strip()
        name = (r.get("street_name") or "").strip()
        suffix = (r.get("street_suffix") or "").strip()
        addr = " ".join(p for p in (num, name, suffix) if p).strip()
        permit = r.get("permit_number")
        if not addr or not permit:
            return None
        block = r.get("block") or ""
        lot = r.get("lot") or ""
        apn = f"{block}/{lot}" if block and lot else None
        try:
            filed = datetime.fromisoformat(r["filed_date"].replace("Z", "+00:00")) if r.get("filed_date") else None
        except Exception:
            filed = None
        return RawLead(
            source="vacant",
            source_id=f"sf-permit-{permit}",
            raw_address=addr,
            city="San Francisco",
            county="San Francisco",
            state="CA",
            zip=str(r.get("zipcode") or "") or None,
            parcel_apn=apn,
            filing_date=filed,
            source_url=(
                f"https://data.sfgov.org/Housing-and-Buildings/Building-Permits/i98e-djp9/data?permit_number={permit}"
            ),
            extra={
                "permit_type": r.get("permit_type_definition"),
                "status": r.get("status"),
                "description": r.get("description"),
            },
        )
