"""Skip-trace orchestrator.

Public API:

    lookup(parcel_key, address=None, known_owner_name=None, tier="standard")
        → dict with provider, owner_name, phones, emails, mailing_address,
          notes, billing.

Tier dispatch + pricing/margin live in `skip_trace_pricing` and
`skip_trace_providers`. This file is the thin glue layer that:

  1. Picks the tier-appropriate provider (BatchData / TLOxp / mock).
  2. Logs usage so we can bill end-of-period.
  3. Adds a human-readable note + billing block to the response.
"""
from __future__ import annotations

import logging
from typing import Any

from services import skip_trace_pricing as pricing
from services import skip_trace_providers as providers
from services import usage_log

log = logging.getLogger(__name__)


def lookup(
    parcel_key: str,
    address: str | None = None,
    known_owner_name: str | None = None,
    tier: str = "standard",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Resolve owner contact and emit a usage row."""
    if tier not in ("standard", "pro"):
        tier = "standard"
    info = pricing.get(tier)

    try:
        result = providers.lookup(tier, parcel_key, address, known_owner_name)
        success = bool(result.get("phones") or result.get("emails"))
    except Exception as exc:  # pragma: no cover — defensive
        log.error("Skip-trace lookup blew up unexpectedly: %s", exc)
        result = {
            "provider": "error",
            "owner_name": known_owner_name,
            "phones": [],
            "emails": [],
            "mailing_address": None,
        }
        success = False

    using_mock = result.get("provider", "").startswith("mock")
    note = (
        f"Demo data — set "
        f"{'BATCHDATA_API_KEY' if tier == 'standard' else 'TLO_API_KEY'} "
        f"to enable live {info['provider_label']} lookups."
        if using_mock
        else f"Live data via {info['provider_label']} ({info['match_rate_pct']}% match rate)."
    )

    # Append billing + display fields the frontend renders directly.
    result["tier"] = info["tier"]
    result["tier_label"] = info["label"]
    result["billing"] = {
        "tier": info["tier"],
        "provider_label": info["provider_label"],
        "advertised_usd": info["advertised_usd"],
        "markup_pct": info["markup_pct"],
        "billed": not using_mock,
    }
    result["notes"] = note

    # Only bill (and log cost) when the call actually went out.
    if not using_mock:
        usage_log.record(
            parcel_key=parcel_key,
            tier=tier,
            provider=info["provider_id"],
            cost_usd=info["cost_usd"],
            charged_usd=info["advertised_usd"],
            success=success,
            user_id=user_id,
        )

    return result


# Re-export for any legacy callers that imported the pricing helpers from here.
list_tiers = pricing.list_tiers
