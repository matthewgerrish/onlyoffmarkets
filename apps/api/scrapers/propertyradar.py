"""PropertyRadar — nationwide multi-signal scraper.

Single API surface gives us six distress signals at once:

  preforeclosure   ForeclosureStage = NOD/NTS
  auction          ForeclosureStage = Auction
  tax-lien         TaxDelinquentYear ≥ 1
  probate          InProbate = 1
  vacant           Vacant = 1
  absentee         OwnerOccupied = 0      (vacant tab also includes these)

Each signal runs as its own scraper class (PreforeclosurePR,
AuctionPR, TaxLienPR, etc.) so the pipeline can show per-signal
health in /admin/scrapers.

PropertyRadar covers all 50 states. Rate limiting is enforced by
their backend (429 with `Retry-After`); our base-class respects it.

Set PROPERTYRADAR_API_KEY on Fly to activate. Without the key every
scraper in this module yields zero leads.
"""
from __future__ import annotations

import logging
from typing import AsyncIterable

from scrapers.base import BaseScraper
from scrapers.models import RawLead
from services import propertyradar_client as pr

log = logging.getLogger(__name__)


# 50-state coverage in one shot. PropertyRadar caps payload size, so
# we batch state requests to avoid 413s on the big states.
ALL_US_STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL",
    "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE",
    "NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD",
    "TN","TX","UT","VT","VA","WA","WV","WI","WY",
]

DEFAULT_BATCH_STATES = 10   # 5 batches of 10 states = 50
DEFAULT_LIMIT_PER_STATE_BATCH = 1000


def _to_lead(p: dict, source_tag: str) -> RawLead | None:
    """Normalize a PropertyRadar property record into a RawLead.

    PropertyRadar's exact field names vary slightly between endpoints
    and account tiers; we accept both camelCase and snake_case using
    lookup helpers so the scraper survives small response-shape drift.
    """
    def f(*names):
        for n in names:
            v = p.get(n)
            if v not in (None, "", []):
                return v
        return None

    apn      = f("APN", "apn", "ParcelNumber", "parcel_number")
    address  = f("SiteAddress", "address", "PropertyAddress", "site_address")
    city     = f("SiteCity", "city")
    state    = f("SiteState", "state")
    zip_     = f("SiteZip", "zip", "PostalCode")
    county   = f("County", "county")

    if not apn and not address:
        return None

    lat = f("Latitude", "lat", "latitude")
    lng = f("Longitude", "lng", "longitude")

    avm           = f("AVM", "avm", "EstimatedValue", "estimated_value")
    assessed      = f("AssessedValue", "assessed_value", "TotalAssessedValue")
    loan_balance  = f("EstimatedMortgageBalance", "loan_balance", "OutstandingBalance")
    default_amt   = f("DefaultAmount", "default_amount")
    auction_bid   = f("OpeningBid", "opening_bid")
    sale_dt       = f("AuctionDate", "auction_date", "TrusteeSaleDate")
    yrs_delinq    = f("TaxDelinquentYears", "years_delinquent")
    owner_state   = f("OwnerState", "owner_state", "MailingState")
    owner_name    = f("OwnerName", "owner_name", "OwnerFullName")

    bedrooms      = f("Bedrooms", "bedrooms", "Beds")
    bathrooms     = f("Bathrooms", "bathrooms", "Baths")
    sqft          = f("LivingArea", "sqft", "BuildingSqFt")
    lot_sqft      = f("LotArea", "lot_sqft", "LotSqFt")
    year_built    = f("YearBuilt", "year_built")
    prop_type     = f("PropertyType", "property_type", "PropertyUse")

    return RawLead(
        source=source_tag,                  # type: ignore[arg-type]
        source_id=f"pr-{apn or address}",
        raw_address=str(address or ""),
        parcel_apn=str(apn) if apn else None,
        city=str(city) if city else None,
        county=str(county) if county else None,
        state=str(state) if state else "WA",
        zip=str(zip_) if zip_ else None,
        latitude=float(lat) if lat else None,
        longitude=float(lng) if lng else None,
        sale_date=sale_dt if sale_dt else None,
        default_amount=int(default_amt) if default_amt else None,
        opening_bid=int(auction_bid) if auction_bid else None,
        years_delinquent=int(yrs_delinq) if yrs_delinq else None,
        owner_state=str(owner_state) if owner_state else None,
        owner_name=str(owner_name) if owner_name else None,
        estimated_value=int(avm) if avm else None,
        assessed_value=int(assessed) if assessed else None,
        loan_balance=int(loan_balance) if loan_balance else None,
        bedrooms=int(bedrooms) if bedrooms else None,
        bathrooms=float(bathrooms) if bathrooms else None,
        sqft=int(sqft) if sqft else None,
        lot_sqft=int(lot_sqft) if lot_sqft else None,
        year_built=int(year_built) if year_built else None,
        property_type=_normalize_prop_type(prop_type),
        source_url=f"https://www.propertyradar.com/property/{apn}" if apn else None,
        extra={"propertyradar": {k: p.get(k) for k in list(p.keys())[:30]}},
    )


def _normalize_prop_type(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).lower()
    if "single" in s or "sfr" in s:        return "single_family"
    if "condo" in s:                       return "condo"
    if "town" in s:                        return "townhome"
    if "multi" in s or "duplex" in s or "triplex" in s: return "multi_family"
    if "land" in s or "vacant lot" in s:   return "land"
    if "commercial" in s:                  return "commercial"
    if "manufactur" in s or "mobile" in s: return "manufactured"
    return "other"


class _PropertyRadarBase(BaseScraper):
    """Shared driver — subclasses set source/source_name + criteria."""
    source: str = "vacant"             # default; override in subclass
    source_name: str = "PropertyRadar"
    criteria: list[dict] = []
    limit_per_batch: int = DEFAULT_LIMIT_PER_STATE_BATCH
    batch_size: int = DEFAULT_BATCH_STATES

    async def run(self) -> AsyncIterable[RawLead]:
        if not pr.is_live():
            log.warning("%s skipped — PROPERTYRADAR_API_KEY not set", self.source_name)
            return
        for i in range(0, len(ALL_US_STATES), self.batch_size):
            batch = ALL_US_STATES[i:i + self.batch_size]
            log.info("%s batch %s", self.source_name, batch)
            results = await pr.search_properties(
                self.criteria,
                states=batch,
                limit=self.limit_per_batch,
            )
            for p in results:
                lead = _to_lead(p, self.source)
                if lead:
                    yield lead


class PreforeclosurePR(_PropertyRadarBase):
    source = "preforeclosure"
    source_name = "PropertyRadar — preforeclosure (NOD/NTS)"
    criteria = pr.CRITERIA_PREFORECLOSURE


class AuctionPR(_PropertyRadarBase):
    source = "auction"
    source_name = "PropertyRadar — auction (trustee sales)"
    criteria = pr.CRITERIA_AUCTION


class TaxLienPR(_PropertyRadarBase):
    source = "tax-lien"
    source_name = "PropertyRadar — tax-default"
    criteria = pr.CRITERIA_TAX_DEFAULT


class ProbatePR(_PropertyRadarBase):
    source = "probate"
    source_name = "PropertyRadar — probate"
    criteria = pr.CRITERIA_PROBATE


class VacantPR(_PropertyRadarBase):
    source = "vacant"
    source_name = "PropertyRadar — vacant"
    criteria = pr.CRITERIA_VACANT


class AbsenteePR(_PropertyRadarBase):
    source = "vacant"            # we surface absentee under the vacant tag
    source_name = "PropertyRadar — absentee owner"
    criteria = pr.CRITERIA_ABSENTEE


class HighEquityPR(_PropertyRadarBase):
    # No matching site tag — store under "motivated_seller" since high-
    # equity owners on a long hold are top mailer candidates.
    source = "motivated_seller"
    source_name = "PropertyRadar — high equity, long hold"
    criteria = pr.CRITERIA_HIGH_EQUITY
