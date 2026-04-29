"""Token wallet pricing — single source of truth.

Tokens are the universal credit unit. One token = $0.20 retail.
Volume discounts shave the per-token cost on bigger bundles.

Per-action token cost:
  standard skip-trace lookup    1 token  ($0.20)   provider cost ~$0.10
  pro skip-trace lookup         3 tokens ($0.60)   provider cost ~$0.50
  mailer postcard               4 tokens ($0.80)   provider cost ~$0.55-0.85

Margins land between 25-100% depending on action — comfortable buffer
for processing, dunning, and free-tier usage.
"""
from __future__ import annotations

from typing import TypedDict


TOKEN_USD = 0.20


class Action(TypedDict):
    key: str
    label: str
    tokens: int


ACTION_COSTS: dict[str, Action] = {
    "skip_trace_standard": {"key": "skip_trace_standard", "label": "Standard owner lookup", "tokens": 1},
    "skip_trace_pro":      {"key": "skip_trace_pro",      "label": "Pro owner lookup",      "tokens": 3},
    "mailer_postcard":     {"key": "mailer_postcard",     "label": "Postcard (Lob)",        "tokens": 4},
}


def cost_tokens(key: str) -> int:
    return ACTION_COSTS[key]["tokens"]


class Package(TypedDict):
    id: str
    label: str
    tokens: int
    price_usd: float
    per_token_usd: float
    discount_pct: int
    badge: str | None


PACKAGES: list[Package] = [
    {
        "id": "starter",
        "label": "Starter",
        "tokens": 25,
        "price_usd": 5.00,
        "per_token_usd": 0.20,
        "discount_pct": 0,
        "badge": None,
    },
    {
        "id": "builder",
        "label": "Builder",
        "tokens": 100,
        "price_usd": 19.00,
        "per_token_usd": 0.19,
        "discount_pct": 5,
        "badge": "Most popular",
    },
    {
        "id": "pro",
        "label": "Pro",
        "tokens": 500,
        "price_usd": 89.00,
        "per_token_usd": 0.178,
        "discount_pct": 11,
        "badge": "Best value",
    },
    {
        "id": "scale",
        "label": "Scale",
        "tokens": 2000,
        "price_usd": 329.00,
        "per_token_usd": 0.1645,
        "discount_pct": 18,
        "badge": None,
    },
]


def get_package(pkg_id: str) -> Package:
    for p in PACKAGES:
        if p["id"] == pkg_id:
            return p
    raise ValueError(f"Unknown package: {pkg_id}")
