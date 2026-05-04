"""Watchlist routes — saved Recon results.

Auth required. Identity comes from JWT (preferred) or X-User-Id
(legacy anonymous) via services/identity.py.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from services import identity
from services.rate_limit import limiter
from storage import watchlist_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class SaveIn(BaseModel):
    parcel_key: str
    address: str
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    lat: float | None = None
    lng: float | None = None
    deal_score: int | None = None
    deal_band: str | None = None
    adu_score: int | None = None
    adu_band: str | None = None
    snapshot: dict | None = None
    notes: str | None = None


@router.get("")
async def list_watchlist(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None),
    limit: int = 100,
) -> dict:
    user_id = identity.resolve_user_id(authorization, x_user_id)
    return {"results": watchlist_db.list_for(user_id, limit=min(int(limit), 500))}


@router.post("")
async def save_watchlist(
    body: SaveIn,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None),
) -> dict:
    user_id = identity.resolve_user_id(authorization, x_user_id)
    limiter.check("watchlist_save", user_id, max=60, per_seconds=60)

    if not body.parcel_key or len(body.parcel_key) < 2:
        raise HTTPException(400, "parcel_key required")
    if not body.address or len(body.address) < 3:
        raise HTTPException(400, "address required")

    row = watchlist_db.save(
        user_id,
        parcel_key=body.parcel_key,
        address=body.address,
        city=body.city,
        state=body.state,
        zip_=body.zip,
        lat=body.lat,
        lng=body.lng,
        deal_score=body.deal_score,
        deal_band=body.deal_band,
        adu_score=body.adu_score,
        adu_band=body.adu_band,
        snapshot=body.snapshot,
        notes=body.notes,
    )
    return {"ok": True, "saved": row}


class NotesIn(BaseModel):
    notes: str


@router.put("/{parcel_key}/notes")
async def update_notes(
    parcel_key: str,
    body: NotesIn,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None),
) -> dict:
    user_id = identity.resolve_user_id(authorization, x_user_id)
    ok = watchlist_db.update_notes(user_id, parcel_key, body.notes or "")
    if not ok:
        raise HTTPException(404, "not found")
    return {"ok": True}


@router.delete("/{parcel_key}")
async def delete_watchlist(
    parcel_key: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None),
) -> dict:
    user_id = identity.resolve_user_id(authorization, x_user_id)
    ok = watchlist_db.remove(user_id, parcel_key)
    return {"ok": ok}
