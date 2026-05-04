"""Canonical deal-score formula — server-side.

Replaces the duplicate of `lib/score.ts` and the inline formula in
`pages/DealAnalyzer.tsx`. The backend owns the math; the frontend
just renders.

Inputs are the same shape the analyzer collects (a flat dict pulled
from our DB or PropertyRadar / BatchData). Optional fields drive
extra factors when present — when only the basic distress tags are
known we fall back to the original 9-factor scoring.

Output:
  {
    total:       int 0-100
    band:        cold | warming | warm | hot | top
    breakdown:   [{key, label, points, detail?}]
    confidence:  int 0-100   # how much of the formula could fire
    recommendation: str       # next action copy
  }
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# Per-source heat. The exact same weights as lib/score.ts so frontend
# fallback rendering produces identical output for legacy callers.
SOURCE_WEIGHTS: dict[str, int] = {
    "auction":          25,
    "preforeclosure":   22,
    "tax-lien":         18,
    "probate":          16,
    "vacant":           14,
    "reo":              12,
    "fsbo":             10,
    "motivated_seller": 12,
    "expired":           8,
    "canceled":          8,
    "wholesale":         6,
    "network":           4,
}


def _band(total: int) -> str:
    if total >= 85: return "top"
    if total >= 70: return "hot"
    if total >= 50: return "warm"
    if total >= 30: return "warming"
    return "cold"


def _days_until(s: Any) -> int | None:
    if not s: return None
    try:
        d = s if isinstance(s, datetime) else datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return int((d - datetime.now(timezone.utc)).total_seconds() // 86_400)
    except Exception:
        return None


def _years_since(s: Any) -> int | None:
    if not s: return None
    try:
        d = s if isinstance(s, datetime) else datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return int((datetime.now(timezone.utc) - d).total_seconds() // (365.25 * 86_400))
    except Exception:
        return None


def score_deal(p: dict[str, Any]) -> dict[str, Any]:
    """Compute the deal score from a flat property dict.

    Recognized fields (all optional):
      source_tags          list[str]
      years_delinquent     int
      vacancy_months       int
      owner_state          str          # for absentee detection
      state                str          # property state
      sale_date            datetime|str # auction date
      default_amount       int
      lien_amount          int
      estimated_value      int          # AVM
      assessed_value       int          # county
      loan_balance         int
      mortgage_count       int
      asking_price         int
      last_seen            datetime|str

      # Paid-source enrichment (PropertyRadar / BatchData)
      foreclosure_stage    str          # 'NOD' | 'NTS' | 'Auction'
      equity_pct           float        # 0.0-1.0 (preferred over loan/value)
      years_owned          int          # since last sale
      last_sale_date       datetime|str
      hoa_delinquent       bool
      mortgage_orig_year   int          # high-rate post-2022 = trapped owners
      vacancy_months       int

    Returns: { total, band, breakdown, confidence, recommendation }
    """
    breakdown: list[dict[str, Any]] = []
    total = 0
    confidence = 0
    factors_seen = 0
    factors_possible = 14   # number of independent factors we check

    tags = list(p.get("source_tags") or [])

    # 1) Foreclosure stage (override the source-tag base for preforeclosure /
    #    auction when we know the exact stage from a paid source).
    fc_stage = (p.get("foreclosure_stage") or "").upper()
    fc_days = _days_until(p.get("sale_date"))
    used_stage = False
    if fc_stage in ("NOD", "NTS", "AUCTION"):
        used_stage = True
        factors_seen += 1
        if fc_stage == "AUCTION" and fc_days is not None and fc_days >= 0:
            if fc_days <= 7:
                pts, label = 30, f"Auction in {fc_days} day{'s' if fc_days != 1 else ''}"
            elif fc_days <= 30:
                pts, label = 25, f"Auction in {fc_days} days"
            elif fc_days <= 90:
                pts, label = 18, f"Auction in {fc_days} days"
            else:
                pts, label = 14, f"Auction set ({fc_days} days out)"
        elif fc_stage == "NTS":
            pts, label = 25, "Notice of Trustee Sale (NTS)"
        else:  # NOD
            pts, label = 22, "Notice of Default (NOD)"
        breakdown.append({
            "key": "fc_stage",
            "label": label,
            "points": pts,
            "detail": "active foreclosure timeline",
        })
        total += pts

    # 2) If no stage info, fall back to highest-weight source tag
    if not used_stage and tags:
        factors_seen += 1
        top, top_tag = 0, None
        for t in tags:
            w = SOURCE_WEIGHTS.get(t, 0)
            if w > top:
                top, top_tag = w, t
        if top_tag:
            breakdown.append({
                "key": "primary",
                "label": f"{top_tag.replace('_', ' ')} signal",
                "points": top,
                "detail": "highest-weight active source",
            })
            total += top

    # 3) Diversity bonus — multiple distress sources stack
    extras = max(0, len(tags) - 1)
    if extras > 0:
        factors_seen += 1
        pts = min(extras * 6, 18)
        breakdown.append({
            "key": "stack",
            "label": f"{extras} additional source{'' if extras == 1 else 's'}",
            "points": pts,
            "detail": "multiple distress signals on one parcel",
        })
        total += pts

    # 4) Tax delinquency depth
    yd = p.get("years_delinquent")
    if isinstance(yd, (int, float)) and yd > 0:
        factors_seen += 1
        if yd >= 3:
            pts, label = 16, f"{int(yd)} years tax-delinquent"
        elif yd >= 2:
            pts, label = 12, f"{int(yd)} years tax-delinquent"
        else:
            pts, label = 6, "1 year tax-delinquent"
        breakdown.append({"key": "delinq", "label": label, "points": pts})
        total += pts

    # 5) Vacancy duration
    vm = p.get("vacancy_months")
    if isinstance(vm, (int, float)) and vm > 0:
        factors_seen += 1
        if vm >= 12:
            pts, label = 16, f"{int(vm)} months vacant"
        elif vm >= 6:
            pts, label = 12, f"{int(vm)} months vacant"
        else:
            pts, label = 6, f"{int(vm)} months vacant"
        breakdown.append({"key": "vacant", "label": label, "points": pts})
        total += pts

    # 6) Absentee owner — mailing state ≠ property state
    own_state = (p.get("owner_state") or "").upper()
    prop_state = (p.get("state") or "").upper()
    if own_state and prop_state and own_state != prop_state:
        factors_seen += 1
        breakdown.append({
            "key": "absentee",
            "label": f"Absentee owner ({own_state})",
            "points": 8,
            "detail": "mailing address out of state",
        })
        total += 8

    # 7) Equity / LTV — prefer explicit equity_pct from PR when available
    eq_pct = p.get("equity_pct")
    est_val = p.get("estimated_value") or p.get("assessed_value")
    loan = p.get("loan_balance")
    if eq_pct is None and est_val and loan is not None and est_val > 0:
        eq_pct = max(0.0, min(1.0, (est_val - loan) / est_val))

    if eq_pct is not None:
        factors_seen += 1
        if eq_pct >= 0.95:
            pts, label = 22, "Owned free & clear"
        elif eq_pct >= 0.75:
            pts, label = 18, f"Strong equity {round(eq_pct * 100)}%"
        elif eq_pct >= 0.50:
            pts, label = 12, f"Solid equity {round(eq_pct * 100)}%"
        elif eq_pct >= 0.25:
            pts, label = 6, f"Some equity {round(eq_pct * 100)}%"
        elif eq_pct >= 0.0:
            pts, label = 2, f"Thin equity {round(eq_pct * 100)}%"
        else:
            pts, label = -10, f"Underwater {round(abs(eq_pct) * 100)}%"
        breakdown.append({"key": "equity", "label": label, "points": pts})
        total += pts

    # 8) Years owned — long-time holders (esp. with high equity) are a
    #    sweet spot for off-market acquisition. Senior demographic skew.
    yo = p.get("years_owned")
    if isinstance(yo, (int, float)) and yo > 0:
        factors_seen += 1
        if yo >= 30:
            pts, label = 12, f"Owned {int(yo)}+ years"
            detail = "long-tenure → retirement-liquidity profile"
        elif yo >= 20:
            pts, label = 9, f"Owned {int(yo)} years"
            detail = "strong tenure"
        elif yo >= 10:
            pts, label = 6, f"Owned {int(yo)} years"
            detail = "established owner"
        elif yo >= 5:
            pts, label = 3, f"Owned {int(yo)} years"
            detail = ""
        else:
            pts, label, detail = 0, "", ""
        if pts > 0:
            breakdown.append({"key": "tenure", "label": label, "points": pts, "detail": detail})
            total += pts

    # 9) Sale history pause — never sold (or 15+ years) suggests motivated
    last_sale = _years_since(p.get("last_sale_date"))
    if last_sale is not None and last_sale >= 15 and not (yo and yo >= 15):
        factors_seen += 1
        pts = 6 if last_sale >= 25 else 4
        breakdown.append({
            "key": "stale_sale",
            "label": f"Last sale {last_sale}+ years ago",
            "points": pts,
            "detail": "long acquisition window",
        })
        total += pts

    # 10) Sale-date proximity (auction not already counted under fc_stage)
    if not used_stage and fc_days is not None and fc_days >= 0:
        factors_seen += 1
        if fc_days <= 14:
            pts, label = 14, f"Sale in {fc_days}d"
        elif fc_days <= 30:
            pts, label = 10, f"Sale in {fc_days}d"
        elif fc_days <= 60:
            pts, label = 6, f"Sale in {fc_days}d"
        else:
            pts, label = 0, ""
        if pts > 0:
            breakdown.append({"key": "sale", "label": label, "points": pts, "detail": "time pressure"})
            total += pts

    # 11) Stacked debt
    debt = (p.get("default_amount") or 0) + (p.get("lien_amount") or 0)
    if debt >= 25_000:
        factors_seen += 1
        pts = 10 if debt >= 100_000 else 7 if debt >= 50_000 else 4
        breakdown.append({
            "key": "debt",
            "label": f"${debt:,} stacked debt",
            "points": pts,
            "detail": "larger debt → more negotiation room",
        })
        total += pts

    # 12) Multiple mortgages — junior + senior = financial layering
    mc = p.get("mortgage_count")
    if isinstance(mc, int) and mc >= 2:
        factors_seen += 1
        pts = min(5, (mc - 1) * 3)
        breakdown.append({
            "key": "multi_mortgage",
            "label": f"{mc} active mortgages",
            "points": pts,
            "detail": "junior liens compound pressure",
        })
        total += pts

    # 13) Asking-price discount vs AVM
    asking = p.get("asking_price")
    if asking and est_val and est_val > 0:
        spread = 1 - (asking / est_val)
        if spread > 0.02:
            factors_seen += 1
            pts = min(int(round(spread * 60)), 18)
            breakdown.append({
                "key": "spread",
                "label": f"Asking {int(spread * 100)}% below est. value",
                "points": pts,
                "detail": f"${asking:,} vs ${est_val:,} AVM",
            })
            total += pts

    # 14) Freshness — fresher signals are easier to action
    last_seen = p.get("last_seen")
    if last_seen:
        try:
            ls = datetime.fromisoformat(str(last_seen).replace("Z", "+00:00"))
            if ls.tzinfo is None:
                ls = ls.replace(tzinfo=timezone.utc)
            days_old = int((datetime.now(timezone.utc) - ls).total_seconds() // 86_400)
            factors_seen += 1
            if days_old <= 7:
                breakdown.append({"key": "fresh", "label": "Fresh (≤7d)", "points": 4})
                total += 4
            elif days_old <= 30:
                breakdown.append({"key": "fresh", "label": "Recent (≤30d)", "points": 2})
                total += 2
        except Exception:
            pass

    # Negative signals
    if p.get("hoa_delinquent"):
        factors_seen += 1
        breakdown.append({
            "key": "hoa_delinq",
            "label": "HOA delinquent",
            "points": 6,
            "detail": "broader financial stress signal",
        })
        total += 6

    total = max(0, min(100, int(round(total))))
    band = _band(total)

    confidence = int(round(min(100, (factors_seen / factors_possible) * 100)))

    # Recommended next action — heuristic on score + freshness
    if total >= 70:
        recommendation = (
            "Strong signal. Skip-trace the owner now and queue a postcard "
            "while it's fresh."
        )
    elif total >= 50:
        recommendation = (
            "Solid lead. Pull the owner contact and mail. Watch for new "
            "signals stacking on this parcel."
        )
    elif total >= 30:
        recommendation = (
            "Worth a watch — add to alerts and re-score in 30 days. Don't "
            "spend a token yet unless you have local knowledge."
        )
    else:
        recommendation = (
            "Light signal. Skip — go pull the next parcel from the feed."
        )

    return {
        "total": total,
        "band": band,
        "breakdown": breakdown,
        "confidence": confidence,
        "recommendation": recommendation,
    }
