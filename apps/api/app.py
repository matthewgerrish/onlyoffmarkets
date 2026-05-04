"""
OnlyOffMarkets API.

Read-only public API backing the React frontend.

Run:
    uvicorn app:app --reload --port 8001
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routes.off_market import router as off_market_router
from routes.owner import router as owner_router
from routes.mailers import router as mailers_router
from routes.admin import router as admin_router
from routes.tokens import router as tokens_router
from routes.billing import router as billing_router
from routes.auth import router as auth_router
from routes.analyzer import router as analyzer_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)-32s %(message)s",
)

app = FastAPI(
    title="OnlyOffMarkets API",
    version="0.1.0",
    description="Public read API for off-market real-estate signals.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "onlyoffmarkets-api"}


app.include_router(off_market_router)
app.include_router(owner_router)
app.include_router(mailers_router)
app.include_router(admin_router)
app.include_router(tokens_router)
app.include_router(billing_router)
app.include_router(auth_router)
app.include_router(analyzer_router)
