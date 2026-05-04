"""ADU potential scoring — Washington & California only.

State law landscape (as of 2026):

WASHINGTON
  HB 1337 (2023, in force 2024-) — all cities >25k must allow 2 ADUs
  per single-family lot. Detached ADU up to 1000 sqft, by-right.
  Owner-occupancy requirements eliminated. Reduced parking near
  transit corridors.

CALIFORNIA
  AB 68 + AB 881 + AB 1033 (2020-2023) — every single-family lot
  permits at minimum: 1 main house + 1 ADU (up to 1200 sqft) +
  1 JADU (≤500 sqft inside main). SB 9 (2022) allows lot-split +
  duplex on most SFR lots → up to 4 dwelling units total.
  Lot size minimums largely eliminated. 4 ft setbacks.

We score 0-100 using only fields we already have on a property
record (lot_sqft, sqft, year_built, property_type, state). No
zoning lookups — those would need a per-jurisdiction GIS layer
we'd license separately.

Output: {
  score:          int 0-100
  band:           'none' | 'limited' | 'good' | 'excellent'
  units_possible: int   (1-4)
  eligible:       bool
  breakdown:      [ { key, label, points, detail? } ]
  notes:          [str]   — caveats / advice
}
"""
from __future__ import annotations

from typing import Any

ELIGIBLE_STATES = {"WA", "CA"}
ELIGIBLE_TYPES = {"single_family", "townhome", "multi_family"}


def score_adu(
    state: str | None,
    property_type: str | None,
    lot_sqft: int | None,
    sqft: int | None,
    year_built: int | None,
) -> dict[str, Any]:
    state_u = (state or "").upper()
    pt = (property_type or "").lower()
    notes: list[str] = []
    breakdown: list[dict[str, Any]] = []

    if state_u not in ELIGIBLE_STATES:
        return {
            "score": 0,
            "band": "none",
            "units_possible": 1,
            "eligible": False,
            "breakdown": [],
            "notes": [
                f"OnlyOffMarkets only scores ADU potential in WA + CA. "
                f"State '{state_u or 'unknown'}' has no statewide ADU rule "
                f"we can apply confidently."
            ],
        }

    if pt and pt not in ELIGIBLE_TYPES:
        return {
            "score": 0,
            "band": "none",
            "units_possible": 1,
            "eligible": False,
            "breakdown": [],
            "notes": [
                f"Property type '{pt}' isn't typically ADU-eligible "
                f"(condos / land / commercial usually excluded)."
            ],
        }

    score = 0

    # 1. Statutory base eligibility — both WA and CA permit ADUs by-right
    base = 35
    breakdown.append({
        "key": "base",
        "label": (
            f"{state_u} statewide by-right ADU"
            f"{'s (HB 1337)' if state_u == 'WA' else ' (AB 68 / SB 9)'}"
        ),
        "points": base,
        "detail": "single-family use eligible without rezoning",
    })
    score += base

    # 2. Lot size — direct driver of detached-ADU feasibility
    if lot_sqft and lot_sqft > 0:
        if lot_sqft >= 7500:
            pts = 25
            label = "Large lot (≥7,500 sqft)"
            detail = "room for detached ADU + driveway access"
        elif lot_sqft >= 5000:
            pts = 18
            label = f"Good lot ({lot_sqft:,} sqft)"
            detail = "fits detached + setbacks comfortably"
        elif lot_sqft >= 3500:
            pts = 10
            label = f"Compact lot ({lot_sqft:,} sqft)"
            detail = "attached / interior ADU likely; detached tight"
        else:
            pts = 3
            label = f"Small lot ({lot_sqft:,} sqft)"
            detail = "JADU / interior conversion only"
        breakdown.append({"key": "lot", "label": label, "points": pts, "detail": detail})
        score += pts
    else:
        notes.append("Lot size unknown — pull parcel data for confident scoring.")

    # 3. Building-to-lot coverage — low coverage = room to add
    if lot_sqft and sqft and lot_sqft > 0 and sqft > 0:
        coverage = sqft / lot_sqft
        if coverage <= 0.20:
            pts = 15
            label = f"Low coverage ({int(coverage * 100)}%)"
            detail = "lots of unbuilt yard area"
        elif coverage <= 0.35:
            pts = 10
            label = f"Moderate coverage ({int(coverage * 100)}%)"
            detail = "fits standard detached ADU"
        elif coverage <= 0.50:
            pts = 5
            label = f"High coverage ({int(coverage * 100)}%)"
            detail = "tight; consider attached / garage conversion"
        else:
            pts = 0
            label = f"Saturated lot ({int(coverage * 100)}%)"
            detail = "very little buildable area left"
        breakdown.append({"key": "coverage", "label": label, "points": pts, "detail": detail})
        score += pts

    # 4. Year built — older homes often have garages/sheds that convert
    if year_built and year_built > 0:
        if year_built <= 1970:
            pts = 8
            label = f"Pre-1970 build ({year_built})"
            detail = "detached garage often present → conversion candidate"
        elif year_built <= 1995:
            pts = 5
            label = f"Mid-era build ({year_built})"
            detail = "typical lot/setback layout"
        else:
            pts = 2
            label = f"Newer build ({year_built})"
            detail = "modern footprints often max-set lot"
        breakdown.append({"key": "era", "label": label, "points": pts, "detail": detail})
        score += pts

    # 5. CA SB 9 lot-split bonus — duplex + lot split → 4 units possible
    if state_u == "CA" and lot_sqft and lot_sqft >= 2400:
        pts = 7
        breakdown.append({
            "key": "sb9",
            "label": "SB 9 lot-split eligible",
            "points": pts,
            "detail": "split into 2 lots × 2 units = up to 4 dwellings",
        })
        score += pts
        notes.append(
            "CA SB 9: lots ≥ 2,400 sqft can be split into two and each "
            "carries a duplex by-right. Confirm local ordinance compliance."
        )

    # 6. WA transit-proximity bonus would go here if we had transit data
    #    For now, conservative.
    if state_u == "WA":
        notes.append(
            "WA HB 1337: 2 ADUs per lot in cities >25k. Detached ADU up to 1,000 sqft "
            "by-right. No owner-occupancy mandate."
        )

    score = max(0, min(100, int(round(score))))

    band: str
    if score >= 80:
        band = "excellent"
    elif score >= 60:
        band = "good"
    elif score >= 35:
        band = "limited"
    else:
        band = "none"

    # Units-possible projection
    if state_u == "CA" and score >= 60:
        units = 4 if (lot_sqft and lot_sqft >= 4800) else 3
    elif state_u == "CA":
        units = 2
    elif state_u == "WA" and score >= 60:
        units = 3        # main + 2 ADUs
    elif state_u == "WA":
        units = 2
    else:
        units = 1

    return {
        "score": score,
        "band": band,
        "units_possible": units,
        "eligible": score >= 35,
        "breakdown": breakdown,
        "notes": notes,
        "state": state_u,
    }
