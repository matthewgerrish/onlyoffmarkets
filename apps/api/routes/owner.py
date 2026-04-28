"""Owner contact lookup endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services import skip_trace
from storage.off_market_db import get_one

router = APIRouter(prefix="/owner", tags=["owner"])


@router.get("/{parcel_key}")
async def lookup_owner(parcel_key: str) -> dict:
    rec = get_one(parcel_key)
    if not rec:
        raise HTTPException(status_code=404, detail="Property not found")
    return skip_trace.lookup(
        parcel_key,
        rec.get("address"),
        known_owner_name=rec.get("owner_name"),
    )
