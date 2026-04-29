"""Token wallet endpoints (read-only).

Purchases now go through `/billing/checkout/tokens` (Stripe Checkout)
instead of the legacy mock /tokens/purchase. We keep that endpoint
as a dev-only shortcut when STRIPE_SECRET_KEY is unset.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from services import memberships, tokens_pricing
from storage import memberships_db, tokens_db

router = APIRouter(prefix="/tokens", tags=["tokens"])


def _resolve_user_id(x_user_id: str | None) -> str:
    if not x_user_id or len(x_user_id) < 6:
        raise HTTPException(status_code=400, detail="X-User-Id header required")
    return x_user_id.strip()[:64]


@router.get("/packages")
async def list_packages() -> dict:
    return {
        "token_usd": tokens_pricing.TOKEN_USD,
        "packages": tokens_pricing.PACKAGES,
        "actions": list(tokens_pricing.ACTION_COSTS.values()),
    }


@router.get("/balance")
async def get_balance(x_user_id: str | None = Header(default=None)) -> dict:
    user_id = _resolve_user_id(x_user_id)
    return tokens_db.summary(user_id)


@router.get("/transactions")
async def list_transactions(
    x_user_id: str | None = Header(default=None),
    limit: int = 50,
) -> dict:
    user_id = _resolve_user_id(x_user_id)
    return {"results": tokens_db.transactions(user_id, limit=min(int(limit), 200))}


class PurchaseIn(BaseModel):
    package_id: str


@router.post("/purchase")
async def purchase(
    body: PurchaseIn,
    x_user_id: str | None = Header(default=None),
) -> dict:
    """Dev-only mock purchase. Disabled when STRIPE_SECRET_KEY is set —
    use `/billing/checkout/tokens` instead."""
    if os.environ.get("STRIPE_SECRET_KEY"):
        raise HTTPException(
            status_code=410,
            detail="Use /billing/checkout/tokens — mock purchase disabled in production",
        )
    user_id = _resolve_user_id(x_user_id)
    try:
        pkg = tokens_pricing.get_package(body.package_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown package")

    plan = memberships_db.get(user_id).get("plan", "free")
    bonus_pct = memberships.token_bonus_pct(plan)
    bonus_tokens = pkg["tokens"] * bonus_pct // 100
    total = pkg["tokens"] + bonus_tokens

    new_balance = tokens_db.credit(
        user_id,
        total,
        kind="purchase",
        package_id=pkg["id"],
        note=(
            f"Mock purchase — {pkg['label']} pack"
            + (f" (+{bonus_tokens} Premium bonus)" if bonus_tokens else "")
        ),
    )
    return {
        "success": True,
        "package_id": pkg["id"],
        "tokens_credited": total,
        "bonus_tokens": bonus_tokens,
        "balance": new_balance,
        "billed_usd": pkg["price_usd"],
        "note": "Mock purchase — wire STRIPE_SECRET_KEY for real Checkout.",
    }
