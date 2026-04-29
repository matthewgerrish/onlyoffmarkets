"""Stripe Checkout + webhook wrapper.

Lazy-imports the `stripe` SDK so dev installs don't need it. When
STRIPE_SECRET_KEY is unset we run in MOCK mode — the routes still
return a Checkout URL shape but the URL points back to our own
`/billing/mock-confirm` endpoint that grants the entitlement
immediately. That keeps the UI flow identical between dev and prod.
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
PUBLIC_WEB_URL = os.environ.get("PUBLIC_WEB_URL", "https://onlyoffmarkets.com").rstrip("/")
PUBLIC_API_URL = os.environ.get("PUBLIC_API_URL", "https://onlyoffmarkets-api.fly.dev").rstrip("/")

# Optional pre-created Stripe price ids — recommended for memberships
# so dashboard analytics work cleanly. Falls back to inline price_data
# when unset.
PRICE_ID_STANDARD = os.environ.get("STRIPE_PRICE_ID_STANDARD")
PRICE_ID_PREMIUM = os.environ.get("STRIPE_PRICE_ID_PREMIUM")


def is_live() -> bool:
    return bool(STRIPE_SECRET)


def _stripe():
    import stripe  # type: ignore[import-untyped]

    stripe.api_key = STRIPE_SECRET
    return stripe


# ---------- Checkout: token packs (one-off) ------------------------------------

def checkout_token_pack(
    user_id: str,
    pack_id: str,
    pack_label: str,
    tokens: int,
    price_usd: float,
    bonus_pct: int = 0,
) -> dict:
    """Return {url, session_id, mock} for a token-pack checkout."""
    if not is_live():
        return {
            "url": f"{PUBLIC_API_URL}/billing/mock-confirm?type=tokens&pack={pack_id}&user={user_id}",
            "session_id": f"mock_pack_{pack_id}",
            "mock": True,
        }
    stripe = _stripe()
    desc = f"{tokens:,} tokens"
    if bonus_pct:
        desc += f" + {bonus_pct}% bonus (Premium)"
    session = stripe.checkout.Session.create(
        mode="payment",
        client_reference_id=user_id,
        success_url=f"{PUBLIC_WEB_URL}/tokens?status=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{PUBLIC_WEB_URL}/tokens?status=cancelled",
        line_items=[
            {
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(round(price_usd * 100)),
                    "product_data": {
                        "name": f"OnlyOffMarkets — {pack_label} pack",
                        "description": desc,
                    },
                },
            }
        ],
        metadata={
            "kind": "tokens",
            "pack_id": pack_id,
            "tokens": str(tokens),
            "bonus_pct": str(bonus_pct),
            "user_id": user_id,
        },
    )
    return {"url": session.url, "session_id": session.id, "mock": False}


# ---------- Checkout: membership subscription ----------------------------------

def checkout_membership(
    user_id: str,
    plan: str,
    plan_label: str,
    monthly_usd: float,
    pre_built_price_id: str | None = None,
) -> dict:
    """Return {url, session_id, mock} for a recurring subscription checkout."""
    if not is_live():
        return {
            "url": f"{PUBLIC_API_URL}/billing/mock-confirm?type=membership&plan={plan}&user={user_id}",
            "session_id": f"mock_sub_{plan}",
            "mock": True,
        }
    stripe = _stripe()
    if pre_built_price_id:
        line_items = [{"quantity": 1, "price": pre_built_price_id}]
    else:
        line_items = [
            {
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(round(monthly_usd * 100)),
                    "recurring": {"interval": "month"},
                    "product_data": {
                        "name": f"OnlyOffMarkets — {plan_label}",
                    },
                },
            }
        ]
    session = stripe.checkout.Session.create(
        mode="subscription",
        client_reference_id=user_id,
        success_url=f"{PUBLIC_WEB_URL}/membership?status=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{PUBLIC_WEB_URL}/membership?status=cancelled",
        line_items=line_items,
        metadata={"kind": "membership", "plan": plan, "user_id": user_id},
        subscription_data={"metadata": {"plan": plan, "user_id": user_id}},
    )
    return {"url": session.url, "session_id": session.id, "mock": False}


# ---------- Customer portal (manage subscription / cancel) ---------------------

def customer_portal(stripe_customer_id: str) -> dict:
    if not is_live():
        return {
            "url": f"{PUBLIC_WEB_URL}/membership?status=portal_unavailable",
            "mock": True,
        }
    stripe = _stripe()
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=f"{PUBLIC_WEB_URL}/membership",
    )
    return {"url": session.url, "mock": False}


# ---------- Webhook verification ----------------------------------------------

def verify_webhook(payload: bytes, signature: str) -> Any:
    """Verify + parse a Stripe webhook event. Raises on bad signature."""
    if not STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET not set")
    stripe = _stripe()
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=STRIPE_WEBHOOK_SECRET,
    )
