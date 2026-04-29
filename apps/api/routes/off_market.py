"""
Public read API for off-market signals.

Read-only — writes happen only from the nightly pipeline. Cached for
10 minutes per filter combination to absorb traffic spikes without
re-hitting SQLite/Postgres.

Two endpoints:
  GET /off-market               — paginated list with source counts
  GET /off-market/{parcel_key}  — single record with raw source log
"""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from cache import cache
from storage.off_market_db import query as db_query, get_one, source_counts

log = logging.getLogger(__name__)

router = APIRouter(prefix="/off-market", tags=["off-market"])


SOURCE_TYPES = Literal[
    "all", "preforeclosure", "auction", "fsbo", "tax-lien",
    "probate", "vacant", "reo", "canceled", "expired",
    "motivated_seller", "wholesale", "network",
]


def _parse_states(states: str | None, state: str | None) -> list[str] | None:
    """Accept ?states=WA,CA,OR or legacy ?state=WA. Returns None or list of 2-letter codes."""
    if states:
        out = [s.strip().upper() for s in states.split(",") if s.strip()]
        return out or None
    if state:
        return [state.upper()]
    return None


@router.get("")
async def list_off_market(
    source: SOURCE_TYPES = "all",
    state: str | None = Query(None, min_length=2, max_length=2, description="Single state (legacy)"),
    states: str | None = Query(None, description="Comma-separated list of 2-letter state codes"),
    county: str | None = None,
    property_type: str | None = Query(None, description="single_family|condo|townhome|multi_family|land|commercial|manufactured|other"),
    min_value: int | None = Query(None, ge=0),
    max_value: int | None = Query(None, ge=0),
    min_beds: int | None = Query(None, ge=0),
    min_baths: float | None = Query(None, ge=0),
    min_sqft: int | None = Query(None, ge=0),
    max_sqft: int | None = Query(None, ge=0),
    limit: int = Query(60, ge=1, le=300),
) -> dict:
    state_list = _parse_states(states, state)
    cache_key = (
        f"off-market:list:{source}:{','.join(state_list) if state_list else 'any'}:{county or 'any'}:"
        f"{property_type or 'any'}:{min_value or 0}:{max_value or 0}:"
        f"{min_beds or 0}:{min_baths or 0}:{min_sqft or 0}:{max_sqft or 0}:{limit}"
    )
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

    rows = db_query(
        states=state_list,
        county=county,
        source=None if source == "all" else source,
        property_type=property_type,
        min_value=min_value,
        max_value=max_value,
        min_beds=min_beds,
        min_baths=min_baths,
        min_sqft=min_sqft,
        max_sqft=max_sqft,
        limit=limit,
    )

    # Source counts via single grouped SQL query (was: pull 10k rows + Python loop)
    counts = source_counts(state=state_list[0] if state_list and len(state_list) == 1 else None, county=county)

    payload = {
        "results": rows,
        "counts": counts,
        "disclaimer": (
            "Records aggregated from public county recorder, treasurer, court, "
            "and assessor filings. Verify with the source before making offers."
        ),
    }
    await cache.set_json(cache_key, 600, payload)
    return payload


@router.get("/_/coverage")
async def coverage_summary() -> dict:
    """Public coverage summary — totals + state breakdown.

    Cheap (single grouped SQL query). No token. Used by the hero stats
    on the marketing site.
    """
    cached = await cache.get_json("off-market:coverage")
    if cached:
        return cached

    counts = source_counts()
    # Single-pass groupings
    from storage.off_market_db import _conn
    with _conn() as (cur, dialect):
        cur.execute(
            "SELECT state, count(*) FROM off_market_listings WHERE state IS NOT NULL GROUP BY state ORDER BY count(*) DESC LIMIT 60"
        )
        states_rows = cur.fetchall()
        cur.execute(
            "SELECT city, state, count(*) FROM off_market_listings "
            "WHERE city IS NOT NULL AND state IS NOT NULL "
            "GROUP BY city, state ORDER BY count(*) DESC LIMIT 80"
        )
        city_rows = cur.fetchall()
        cur.execute(
            "SELECT property_type, count(*) FROM off_market_listings "
            "WHERE property_type IS NOT NULL "
            "GROUP BY property_type ORDER BY count(*) DESC"
        )
        ptype_rows = cur.fetchall()

    def _g(row, idx, key):
        return row[idx] if dialect == "pg" else row[key]

    by_state = {_g(r, 0, "state"): _g(r, 1, "count(*)") for r in states_rows}
    top_cities = [
        {"city": _g(r, 0, "city"), "state": _g(r, 1, "state"), "count": _g(r, 2, "count(*)")}
        for r in city_rows
    ]
    by_property_type = {_g(r, 0, "property_type"): _g(r, 1, "count(*)") for r in ptype_rows}

    payload = {
        "total_parcels":  counts["all"],
        "by_source":      {k: v for k, v in counts.items() if k != "all"},
        "by_state":       by_state,
        "states_covered": len(by_state),
        "top_cities":     top_cities,
        "by_property_type": by_property_type,
    }
    await cache.set_json("off-market:coverage", 600, payload)
    return payload


@router.get("/_/pins")
async def all_pins(
    state: str | None = Query(None, min_length=2, max_length=2),
    states: str | None = Query(None),
    source: SOURCE_TYPES = "all",
    property_type: str | None = Query(None),
    min_value: int | None = Query(None, ge=0),
    max_value: int | None = Query(None, ge=0),
    min_beds: int | None = Query(None, ge=0),
    min_baths: float | None = Query(None, ge=0),
    min_sqft: int | None = Query(None, ge=0),
    max_sqft: int | None = Query(None, ge=0),
) -> dict:
    """Lightweight pin payload for the map — every parcel with coordinates.

    Returns only the fields needed to render a marker (parcel_key, lat,
    lng, score-driving fields). Cached for 5 min. Up to 10k pins.
    """
    state_list = _parse_states(states, state)
    cache_key = (
        f"off-market:pins:{','.join(state_list) if state_list else 'any'}:{source}:{property_type or 'any'}:"
        f"{min_value or 0}:{max_value or 0}:{min_beds or 0}:{min_baths or 0}:{min_sqft or 0}:{max_sqft or 0}"
    )
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

    from storage.off_market_db import _conn, _ph
    with _conn() as (cur, dialect):
        ph = _ph(dialect)
        clauses = ["latitude IS NOT NULL", "longitude IS NOT NULL"]
        params: list = []
        if state_list:
            placeholders = ",".join([ph] * len(state_list))
            clauses.append(f"state IN ({placeholders})")
            params.extend(state_list)
        if property_type:
            clauses.append(f"property_type = {ph}")
            params.append(property_type)
        if min_value is not None:
            clauses.append(f"COALESCE(asking_price, estimated_value, assessed_value) >= {ph}")
            params.append(min_value)
        if max_value is not None:
            clauses.append(f"COALESCE(asking_price, estimated_value, assessed_value) <= {ph}")
            params.append(max_value)
        if min_beds is not None:
            clauses.append(f"bedrooms >= {ph}")
            params.append(min_beds)
        if min_baths is not None:
            clauses.append(f"bathrooms >= {ph}")
            params.append(min_baths)
        if min_sqft is not None:
            clauses.append(f"sqft >= {ph}")
            params.append(min_sqft)
        if max_sqft is not None:
            clauses.append(f"sqft <= {ph}")
            params.append(max_sqft)
        if source != "all":
            if dialect == "pg":
                clauses.append(f"source_tags @> {ph}::jsonb")
                import json as _json
                params.append(_json.dumps([source]))
            else:
                clauses.append(f"source_tags LIKE {ph}")
                params.append(f'%"{source}"%')
        where = "WHERE " + " AND ".join(clauses)

        cur.execute(
            f"SELECT parcel_key, latitude, longitude, source_tags, "
            f"default_amount, lien_amount, asking_price, sale_date, "
            f"years_delinquent, vacancy_months, owner_state, state, "
            f"estimated_value, assessed_value, loan_balance, "
            f"property_type, last_seen "
            f"FROM off_market_listings {where} LIMIT 10000",
            tuple(params),
        )
        rows = cur.fetchall()

        out = []
        import json as _json2
        for r in rows:
            if dialect == "pg":
                cols = [c.name for c in cur.description]
                d = dict(zip(cols, r))
            else:
                d = dict(r)
            tags = d.get("source_tags")
            if isinstance(tags, str):
                tags = _json2.loads(tags)
            out.append({
                "parcel_key": d["parcel_key"],
                "latitude": d["latitude"],
                "longitude": d["longitude"],
                "source_tags": tags or [],
                "state": d.get("state"),
                "default_amount": d.get("default_amount"),
                "lien_amount": d.get("lien_amount"),
                "asking_price": d.get("asking_price"),
                "sale_date": str(d["sale_date"]) if d.get("sale_date") else None,
                "years_delinquent": d.get("years_delinquent"),
                "vacancy_months": d.get("vacancy_months"),
                "owner_state": d.get("owner_state"),
                "estimated_value": d.get("estimated_value"),
                "assessed_value": d.get("assessed_value"),
                "loan_balance": d.get("loan_balance"),
                "property_type": d.get("property_type"),
                "last_seen": str(d["last_seen"]) if d.get("last_seen") else None,
            })

    payload = {"pins": out, "count": len(out)}
    await cache.set_json(cache_key, 300, payload)
    return payload


@router.get("/{parcel_key}")
async def get_off_market(parcel_key: str) -> dict:
    row = get_one(parcel_key)
    if not row:
        raise HTTPException(status_code=404, detail="Property not found")
    return row
