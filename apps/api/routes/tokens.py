"""Token wallet endpoints.

User identity for the MVP comes from the `X-User-Id` header — the
frontend stores a UUID in localStorage on first visit. Once real auth
ships we'll swap this for a JWT-derived id without changing the schema.

Purchases here are MOCK — no Stripe yet. POST /tokens/purchase credits
the wallet immediately so we can test the spend flow end-to-end. Wire
real billing by replacing `_mock_charge()` with a Stripe PaymentIntent
confirmation.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from services import tokens_pricing
from storage import tokens_db

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
    """Mock purchase — credits the wallet immediately. Replace with Stripe."""
    user_id = _resolve_user_id(x_user_id)
    try:
        pkg = tokens_pricing.get_package(body.package_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown package")

    # _mock_charge() would call Stripe in production. For now, succeed instantly.
    new_balance = tokens_db.credit(
        user_id,
        pkg["tokens"],
        kind="purchase",
        package_id=pkg["id"],
        note=f"Purchased {pkg['label']} pack — ${pkg['price_usd']:.2f}",
    )
    return {
        "success": True,
        "package_id": pkg["id"],
        "tokens_credited": pkg["tokens"],
        "balance": new_balance,
        "billed_usd": pkg["price_usd"],
        "note": "Mock purchase — wire Stripe to charge the user.",
    }
