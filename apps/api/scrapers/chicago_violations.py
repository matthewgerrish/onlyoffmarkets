"""Chicago Building Violations — Socrata Open Data.

Dataset 22u3-xenr (Building Violations, daily-updated, public).
Schema verified live: id, violation_date, violation_status, address,
latitude, longitude, violation_description, property_group.

Smoke-tested against the live API. ~5k req/hour unauthenticated.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import AsyncIterable

from scrapers.base import BaseScraper
from scrapers.models import RawLead

log = logging.getLogger(__name__)

API_URL = "https://data.cityofchicago.org/resource/22u3-xenr.json"


class ChicagoViolationsScraper(BaseScraper):
    source = "vacant"
    source_name = "Chicago Building Violations (Socrata)"
    rate_limit_sec = 0.3

    def __init__(self, days_back: int = 30, **kw):
        super().__init__(**kw)
        self.days_back = days_back

    async def run(self) -> AsyncIterable[RawLead]:
        cutoff = (datetime.utcnow() - timedelta(days=self.days_back)).strftime("%Y-%m-%d")
        offset = 0
        page_size = 1000
        max_pages = 10

        for page in range(max_pages):
            params = {
                "$where": (
                    f"violation_date >= '{cutoff}T00:00:00' "
                    "AND violation_status = 'OPEN'"
                ),
                "$select": (
                    "id, violation_date, violation_status, address, "
                    "latitude, longitude, violation_description, "
                    "property_group, violation_code"
                ),
                "$limit": str(page_size),
                "$offset": str(offset),
                "$order": "violation_date DESC",
            }
            try:
                text = await self.get(API_URL, params=params)
            except Exception as e:
                log.warning("Chicago fetch failed (page=%d): %s", page, e)
                return
            try:
                rows = json.loads(text)
            except json.JSONDecodeError:
                log.warning("Chicago non-JSON; stop")
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
        addr = (r.get("address") or "").strip()
        if not addr or not r.get("id"):
            return None
        try:
            issue_date = datetime.fromisoformat(r["violation_date"].replace("Z", "+00:00"))
        except Exception:
            issue_date = None
        try:
            lat = float(r.get("latitude")) if r.get("latitude") else None
            lng = float(r.get("longitude")) if r.get("longitude") else None
        except (TypeError, ValueError):
            lat = lng = None
        return RawLead(
            source="vacant",
            source_id=f"chi-bldg-{r['id']}",
            raw_address=addr,
            city="Chicago",
            county="Cook",
            state="IL",
            latitude=lat,
            longitude=lng,
            filing_date=issue_date,
            parcel_apn=str(r.get("property_group")) if r.get("property_group") else None,
            source_url=(
                f"https://data.cityofchicago.org/Buildings/Building-Violations/22u3-xenr/data?id={r['id']}"
            ),
            extra={
                "violation_code": r.get("violation_code"),
                "description": r.get("violation_description"),
                "status": r.get("violation_status"),
            },
        )
