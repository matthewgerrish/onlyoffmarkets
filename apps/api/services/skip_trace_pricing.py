"""Skip-trace pricing config — single source of truth for cost vs. advertised price.

Two tiers exposed to the user:

- standard:  BatchData      cost ~$0.10/lookup → user pays $0.12 (20% markup)
- pro:       TLOxp          cost ~$0.50/lookup → user pays $0.60 (20% markup)

A 20% markup keeps us inside the advertised "15-25%" band, lets us round to
clean two-decimal dollar prices, and still leaves comfortable margin once
volume discounts kick in at the provider level.
"""
from __future__ import annotations

from typing import Literal, TypedDict

Tier = Literal["standard", "pro"]


class TierInfo(TypedDict):
    tier: Tier
    label: str
    provider_label: str
    provider_id: str  # internal: "batchdata" / "tlo" / "mock"
    cost_usd: float          # what the provider charges us
    advertised_usd: float    # what the user pays
    markup_pct: int
    match_rate_pct: int
    description: str


TIER_TABLE: dict[Tier, TierInfo] = {
    "standard": {
        "tier": "standard",
        "label": "Standard",
        "provider_label": "BatchData",
        "provider_id": "batchdata",
        "cost_usd": 0.10,
        "advertised_usd": 0.12,
        "markup_pct": 20,
        "match_rate_pct": 70,
        "description": "Best ROI for solo investors. Mobile + landline + email, ~70% match rate.",
    },
    "pro": {
        "tier": "pro",
        "label": "Pro",
        "provider_label": "TLOxp",
        "provider_id": "tlo",
        "cost_usd": 0.50,
        "advertised_usd": 0.60,
        "markup_pct": 20,
        "match_rate_pct": 92,
        "description": "Top-tier (TransUnion) match rate ~92%. Returns multiple phones, deceased flag, relatives.",
    },
}


def get(tier: Tier | str) -> TierInfo:
    if tier not in TIER_TABLE:
        raise ValueError(f"Unknown tier: {tier}")
    return TIER_TABLE[tier]  # type: ignore[index]


def list_tiers() -> list[TierInfo]:
    return [TIER_TABLE["standard"], TIER_TABLE["pro"]]
