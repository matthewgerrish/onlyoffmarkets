"""Owner contact lookup endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from services import skip_trace, skip_trace_pricing
from storage.off_market_db import get_one

router = APIRouter(prefix="/owner", tags=["owner"])


@router.get("/_/pricing")
async def pricing() -> dict:
    """Return advertised tier pricing so the frontend stays in sync."""
    return {
        "tiers": [
            {
                "tier": t["tier"],
                "label": t["label"],
                "provider_label": t["provider_label"],
                "advertised_usd": t["advertised_usd"],
                "markup_pct": t["markup_pct"],
                "match_rate_pct": t["match_rate_pct"],
                "description": t["description"],
            }
            for t in skip_trace_pricing.list_tiers()
        ]
    }


@router.get("/{parcel_key}")
async def lookup_owner(
    parcel_key: str,
    tier: str = Query("standard", pattern="^(standard|pro)$"),
) -> dict:
    rec = get_one(parcel_key)
    if not rec:
        raise HTTPException(status_code=404, detail="Property not found")
    return skip_trace.lookup(
        parcel_key,
        rec.get("address"),
        known_owner_name=rec.get("owner_name"),
        tier=tier,
    )
