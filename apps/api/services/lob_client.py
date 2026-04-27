"""Lob direct-mail client.

Docs: https://docs.lob.com
Auth: HTTP Basic — API key as username, empty password.
Test keys (`test_*`) → sandbox, no charges.

Set `LOB_API_KEY` in apps/api/.env to enable live calls. When unset,
the routes return a mock response so dev still works end-to-end.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

log = logging.getLogger(__name__)

LOB_BASE_URL = "https://api.lob.com/v1"


class LobClient:
    def __init__(self) -> None:
        self.api_key = os.environ.get("LOB_API_KEY", "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def mode(self) -> str:
        if not self.api_key:
            return "mock"
        return "test" if self.api_key.startswith("test_") else "live"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=LOB_BASE_URL,
            auth=(self.api_key, ""),
            headers={"Accept": "application/json"},
            timeout=30.0,
        )

    async def account(self) -> Dict[str, Any]:
        if not self.configured:
            return {"authenticated": False, "mode": "mock", "message": "LOB_API_KEY not set"}
        async with self._client() as c:
            r = await c.get("/postcards", params={"limit": 1})
            r.raise_for_status()
            return {"authenticated": True, "mode": self.mode}

    async def create_postcard(
        self,
        *,
        to: Dict[str, str],
        from_address: Dict[str, str],
        front_html: str,
        back_html: str,
        description: Optional[str] = None,
        size: str = "4x6",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.configured:
            return {
                "id": "psc_mock_" + (description or "x")[:6],
                "url": "",
                "expected_delivery_date": None,
                "to": to,
                "from": from_address,
                "size": size,
                "mode": "mock",
                "description": description,
            }

        payload: Dict[str, Any] = {
            "to": to,
            "from": from_address,
            "front": front_html,
            "back": back_html,
            "size": size,
        }
        if description:
            payload["description"] = description
        if metadata:
            for k, v in metadata.items():
                payload[f"metadata[{k}]"] = str(v)

        async with self._client() as c:
            r = await c.post("/postcards", data=payload)
            if r.status_code >= 400:
                log.error("Lob postcard failed: %s %s", r.status_code, r.text[:400])
            r.raise_for_status()
            return r.json()


lob_client = LobClient()
