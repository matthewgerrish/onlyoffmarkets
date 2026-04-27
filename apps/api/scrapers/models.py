"""
Shared data models for the scraping pipeline.

Every source scraper emits `RawLead` records. The normalizer in
`pipeline.py` upgrades them to `OffMarketListing`s that match the
buyer-site's canonical DTO.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


# The off-market source categories, identical to the site's taxonomy.
# `canceled` = MLS Withdrawn before expiration (seller pulled it).
# `expired`  = MLS reached expiration without selling.
# Both signal a motivated seller whose first listing didn't work — and
# whose agent may have moved on. We pull them from Trestle status fields.
SourceType = Literal[
    "preforeclosure", "auction", "fsbo", "tax-lien",
    "probate", "vacant", "reo", "canceled", "expired",
    "motivated_seller", "wholesale", "network", "mls",
]


class RawLead(BaseModel):
    """Unnormalized output from one scraper run.

    The only required fields are `source`, `source_id`, and some way to
    locate the property (either `raw_address` or `parcel_apn`). Every
    other field is progressively enriched downstream.
    """

    source:    SourceType
    source_id: str = Field(..., description="Stable ID from the source (filing #, listing ID, etc.)")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    # Property identity — at least one required
    raw_address: str | None = None
    parcel_apn:  str | None = None

    # Optional enrichment captured during scrape
    city:        str | None = None
    county:      str | None = None
    state:       str = "WA"
    zip:         str | None = None

    # Source-specific signal
    filing_date:      datetime | None = None
    sale_date:        datetime | None = None       # auction/trustee sale
    default_amount:   int | None = None            # pre-foreclosure
    opening_bid:      int | None = None            # auction
    asking_price:     int | None = None            # fsbo
    lien_amount:      int | None = None            # tax-lien
    years_delinquent: int | None = None
    vacancy_duration_months: int | None = None
    owner_state:      str | None = None            # for absentee detection

    # Valuation enrichment (ATTOM AVM, county assessor, recorded mortgage)
    estimated_value:  int | None = None            # current market AVM
    assessed_value:   int | None = None            # county tax-assessed
    loan_balance:     int | None = None            # outstanding mortgage principal

    # Full source document URL for auditability
    source_url: str | None = None

    # Anything not otherwise modeled — keep raw text, map later
    extra: dict = {}


class OffMarketListing(BaseModel):
    """Normalized record that lands in the database and gets served to the UI.

    Multiple `RawLead`s can collapse into one of these when they
    reference the same parcel — their sources combine as tags.
    """

    parcel_apn:  str
    address:     str
    city:        str
    county:      str
    state:       str = "WA"
    zip:         str | None = None

    # All sources that touched this property. A hot probate+vacant+pre-foreclosure
    # property is a gold lead — that's why we flatten into one record.
    source_tags: list[SourceType] = []

    # Best-available snapshot from each feed
    default_amount:   int | None = None
    sale_date:        datetime | None = None
    asking_price:     int | None = None
    lien_amount:      int | None = None
    years_delinquent: int | None = None
    vacancy_months:   int | None = None
    owner_state:      str | None = None

    # Derived
    estimated_value:   int | None = None
    estimated_equity:  int | None = None
    spread_pct:        float | None = None   # (value - owed) / value

    # ADU screen (reused from adu.py)
    adu_ready: bool = False
    adu_score: int = 0

    # Audit
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen:  datetime = Field(default_factory=datetime.utcnow)
    sources: list[dict] = []          # [{source, source_id, source_url, scraped_at}]
