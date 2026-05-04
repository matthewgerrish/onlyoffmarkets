"""Deal Analyzer — POST an address, get a full thesis back."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from services import (
    batchdata_client,
    deal_analyzer,
    identity,
    propertyradar_client,
)
from services.rate_limit import limiter

log = logging.getLogger(__name__)
router = APIRouter(prefix="/analyzer", tags=["analyzer"])


class AnalyzeIn(BaseModel):
    address: str


@router.get("/debug/propertyradar")
async def debug_pr_config() -> dict:
    """Diagnostic only — returns key SHAPE (length, prefix, whitespace
    flags) so we can verify a paste landed cleanly. Never returns the
    secret value."""
    return propertyradar_client.key_shape()


@router.get("/debug/batchdata")
async def debug_bd_config() -> dict:
    """Diagnostic only — returns BatchData key SHAPE + whether it
    looks like a sandbox key. Never returns the secret value."""
    return batchdata_client.key_shape()


@router.get("/debug/batchdata/probe")
async def debug_bd_probe() -> dict:
    """Probe v1 / v2 / v3 of the BatchData property-search endpoint
    with the current key. Returns the status code we got from each
    version so we can see which one the sandbox key is bound to.
    Each call requests take=1 so the metered cost is at most 1 record."""
    return await batchdata_client.probe_versions()


@router.post("")
async def analyze(
    body: AnalyzeIn,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None),
) -> dict:
    user_id = identity.optional_user_id(authorization, x_user_id) or "_anon"
    # Free-but-throttled — analyzer is cheap on our end (one geocode + one
    # property lookup) but should not be hammered. 30/min/user.
    limiter.check("analyzer", user_id, max=30, per_seconds=60)

    address = (body.address or "").strip()
    if len(address) < 5:
        raise HTTPException(400, "address too short")
    return await deal_analyzer.analyze(address)
