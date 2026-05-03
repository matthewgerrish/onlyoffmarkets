"""BatchData — nationwide property-search scrapers.

Mirrors the PropertyRadar set: one scraper per signal so /admin/scrapers
shows per-signal health. Cheaper marginal cost since we already pay
BatchData for skip-trace; same key powers both endpoints.

Each scraper paginates state-by-state to avoid hitting payload caps,
then yields RawLeads with all the fields BatchData returns.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterable

from scrapers.base import BaseScraper
from scrapers.models import RawLead
from services import batchdata_client as bd

log = logging.getLogger(__name__)

ALL_US_STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL",
    "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE",
    "NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD",
    "TN","TX","UT","VT","VA","WA","WV","WI","WY",
]


def _to_lead(p: dict[str, Any], source_tag: str) -> RawLead | None:
    """Map BatchData property → RawLead. Field names match BatchData's
    documented schema; defensive `dict.get` chains keep us alive when
    they rename anything."""
    addr = p.get("address") or {}
    owner = p.get("owner") or {}
    val   = p.get("valuation") or {}
    mort  = p.get("mortgage") or {}
    fc    = p.get("foreclosure") or {}
    geo   = (addr.get("location") or {}) if isinstance(addr, dict) else {}
    bldg  = p.get("building") or {}

    apn = p.get("apn") or addr.get("parcelNumber")
    raw_address = (addr.get("street") or addr.get("line1") or "") if isinstance(addr, dict) else ""
    if not apn and not raw_address:
        return None

    sale_date = fc.get("saleDate") or fc.get("auctionDate")
    return RawLead(
        source=source_tag,                        # type: ignore[arg-type]
        source_id=f"bd-{apn or raw_address}",
        raw_address=str(raw_address) if raw_address else None,
        parcel_apn=str(apn) if apn else None,
        city=str(addr.get("city") or "") or None,
        county=str(addr.get("county") or "") or None,
        state=str(addr.get("state") or "WA"),
        zip=str(addr.get("zip") or "") or None,
        latitude=float(geo.get("lat") or geo.get("latitude") or 0) or None,
        longitude=float(geo.get("lng") or geo.get("longitude") or 0) or None,
        sale_date=sale_date,
        default_amount=int(fc.get("defaultAmount") or 0) or None,
        opening_bid=int(fc.get("openingBid") or 0) or None,
        years_delinquent=int(p.get("taxDelinquentYears") or 0) or None,
        owner_state=str((owner.get("mailingAddress") or {}).get("state") or "") or None,
        owner_name=(
            owner.get("fullName")
            or " ".join(filter(None, [owner.get("firstName"), owner.get("lastName")]))
        ) or None,
        estimated_value=int(val.get("estimatedValue") or val.get("avm") or 0) or None,
        assessed_value=int(val.get("assessedValue") or 0) or None,
        loan_balance=int(mort.get("balance") or mort.get("estimatedBalance") or 0) or None,
        bedrooms=int(bldg.get("bedrooms") or 0) or None,
        bathrooms=float(bldg.get("bathrooms") or 0) or None,
        sqft=int(bldg.get("livingArea") or 0) or None,
        lot_sqft=int(bldg.get("lotSize") or 0) or None,
        year_built=int(bldg.get("yearBuilt") or 0) or None,
        property_type=_normalize_type(bldg.get("propertyType")),
        source_url=None,
        extra={"batchdata": {"foreclosure": fc, "raw": {k: p.get(k) for k in list(p.keys())[:20]}}},
    )


def _normalize_type(s: str | None) -> str | None:
    if not s:
        return None
    t = str(s).lower()
    if "single" in t:                       return "single_family"
    if "condo" in t:                        return "condo"
    if "town" in t:                         return "townhome"
    if "multi" in t or "duplex" in t:       return "multi_family"
    if "land" in t or "vacant lot" in t:    return "land"
    if "commercial" in t:                   return "commercial"
    if "manufactur" in t or "mobile" in t:  return "manufactured"
    return "other"


class _BatchDataBase(BaseScraper):
    source: str = "vacant"
    source_name: str = "BatchData"
    filter_block: dict = {}
    take_per_page: int = 1000
    max_pages_per_state: int = 3   # 3,000 records / state cap

    async def run(self) -> AsyncIterable[RawLead]:
        if not bd.is_live():
            log.warning("%s skipped — BATCHDATA_API_KEY not set", self.source_name)
            return
        for state in ALL_US_STATES:
            for page in range(1, self.max_pages_per_state + 1):
                results = await bd.search(
                    self.filter_block,
                    states=[state],
                    page=page,
                    take=self.take_per_page,
                )
                if not results:
                    break
                for p in results:
                    lead = _to_lead(p, self.source)
                    if lead:
                        yield lead
                if len(results) < self.take_per_page:
                    break


class PreforeclosureBD(_BatchDataBase):
    source = "preforeclosure"
    source_name = "BatchData — preforeclosure"
    filter_block = bd.FILTER_PREFORECLOSURE


class AuctionBD(_BatchDataBase):
    source = "auction"
    source_name = "BatchData — auction"
    filter_block = bd.FILTER_AUCTION


class TaxLienBD(_BatchDataBase):
    source = "tax-lien"
    source_name = "BatchData — tax-default"
    filter_block = bd.FILTER_TAX_DEFAULT


class VacantBD(_BatchDataBase):
    source = "vacant"
    source_name = "BatchData — vacant"
    filter_block = bd.FILTER_VACANT


class AbsenteeBD(_BatchDataBase):
    source = "vacant"
    source_name = "BatchData — absentee"
    filter_block = bd.FILTER_ABSENTEE


class HighEquityBD(_BatchDataBase):
    source = "motivated_seller"
    source_name = "BatchData — high equity, long hold"
    filter_block = bd.FILTER_HIGH_EQUITY
