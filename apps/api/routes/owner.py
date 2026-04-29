"""Owner contact lookup endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from services import identity, skip_trace, skip_trace_pricing, tokens_pricing
from services.rate_limit import limiter
from storage import tokens_db
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
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None),
) -> dict:
    rec = get_one(parcel_key)
    if not rec:
        raise HTTPException(status_code=404, detail="Property not found")

    action_key = f"skip_trace_{tier}"
    cost = tokens_pricing.cost_tokens(action_key)
    user_id = identity.optional_user_id(authorization, x_user_id) or ""

    # 30 lookups/min per user is well above any human pace; throttles
    # script abuse trying to drain a user's wallet.
    limiter.check("owner_lookup", user_id or "_anon", max=30, per_seconds=60)

    # Charge tokens before calling the provider — refund on hard failure.
    debited = False
    if user_id:
        ok, current_bal = tokens_db.debit(
            user_id,
            cost,
            action_key=action_key,
            parcel_key=parcel_key,
            note=f"Owner lookup ({tier})",
        )
        if not ok:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "insufficient_tokens",
                    "required": cost,
                    "balance": current_bal,
                    "action": action_key,
                },
            )
        debited = True

    try:
        result = skip_trace.lookup(
            parcel_key,
            rec.get("address"),
            known_owner_name=rec.get("owner_name"),
            tier=tier,
            user_id=user_id or None,
        )
    except Exception:
        if debited:
            tokens_db.refund(user_id, cost, action_key=action_key, note="Provider error")
        raise

    # Surface the token cost + new balance so the UI can update the wallet.
    result["tokens"] = {
        "spent": cost,
        "balance": tokens_db.balance(user_id) if user_id else None,
        "action": action_key,
    }
    return result
