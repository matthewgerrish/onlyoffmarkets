"""Membership plan config — Free / Standard / Premium.

Three tiers. Token wallet is independent (pay-as-you-go) — membership
unlocks features and applies a permanent discount on every purchase.

  Free        $0       — preview, masked addresses, 1 metro
  Standard    $9.95/mo — full data, 1 metro saved, alerts, exports
  Premium     $29.95/mo — nationwide, 5% bonus on every pack, bulk tools

Stripe wires up to two recurring price ids (one per paid plan) plus
inline price_data for one-off token packs. Until STRIPE_SECRET_KEY
is set the routes fall back to a mock checkout that instant-grants
the plan / tokens — keeps dev frictionless.
"""
from __future__ import annotations

from typing import Literal, TypedDict

PlanId = Literal["free", "standard", "premium"]


class PlanFeature(TypedDict):
    label: str
    free: bool
    standard: bool
    premium: bool


class Plan(TypedDict):
    id: PlanId
    label: str
    price_usd: float
    interval: str  # "month" | "free"
    badge: str | None
    blurb: str
    cta: str
    token_bonus_pct: int   # extra tokens credited on every purchase
    monthly_token_grant: int
    features: list[str]


PLANS: dict[PlanId, Plan] = {
    "free": {
        "id": "free",
        "label": "Free",
        "price_usd": 0.0,
        "interval": "free",
        "badge": None,
        "blurb": "Preview the feed.",
        "cta": "Start free",
        "token_bonus_pct": 0,
        "monthly_token_grant": 0,
        "features": [
            "Map & deal-meter previews",
            "Truncated property addresses",
            "1 metro area",
            "View 25 properties / day",
            "Public-record source list",
        ],
    },
    "standard": {
        "id": "standard",
        "label": "Standard",
        "price_usd": 9.95,
        "interval": "month",
        "badge": "Most investors start here",
        "blurb": "Full addresses, alerts, exports.",
        "cta": "Subscribe — $9.95/mo",
        "token_bonus_pct": 0,
        "monthly_token_grant": 5,
        "features": [
            "Everything in Free",
            "Full property addresses",
            "1 saved metro + unlimited daily views",
            "Email & instant alerts",
            "CSV exports up to 250 leads/mo",
            "Save up to 50 properties",
            "Standard skip-trace lookups (per-token)",
            "5 free Standard lookups every month",
        ],
    },
    "premium": {
        "id": "premium",
        "label": "Premium",
        "price_usd": 29.95,
        "interval": "month",
        "badge": "Best value",
        "blurb": "Nationwide search, 5% bonus tokens, bulk tools.",
        "cta": "Go Premium — $29.95/mo",
        "token_bonus_pct": 5,
        "monthly_token_grant": 25,
        "features": [
            "Everything in Standard",
            "Nationwide search — no metro lock",
            "5% bonus tokens on every pack you buy",
            "25 free Standard lookups every month",
            "Unlimited saved properties",
            "Unlimited CSV exports",
            "Polygon / draw-on-map search",
            "Bulk skip-trace before mailers",
            "Priority data refresh — fresher leads first",
            "Comp generator (3-mile radius sales)",
            "ROI / equity heatmap layer",
            "Investor team — 1 seat included",
            "API access (read-only)",
            "White-glove CSV import — match by address",
            "Early access to new data sources",
        ],
    },
}


def get(plan_id: str) -> Plan:
    if plan_id not in PLANS:
        return PLANS["free"]
    return PLANS[plan_id]  # type: ignore[index]


def list_plans() -> list[Plan]:
    return [PLANS["free"], PLANS["standard"], PLANS["premium"]]


def token_bonus_pct(plan_id: str) -> int:
    """Return the bonus % applied at credit time for premium subscribers."""
    return get(plan_id).get("token_bonus_pct", 0)


def can_search_nationwide(plan_id: str) -> bool:
    return plan_id == "premium"


def can_export_csv(plan_id: str, count_this_month: int = 0) -> bool:
    if plan_id == "premium":
        return True
    if plan_id == "standard":
        return count_this_month < 250
    return False


def can_use_alerts(plan_id: str) -> bool:
    return plan_id in ("standard", "premium")
