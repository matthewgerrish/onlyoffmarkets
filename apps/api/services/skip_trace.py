"""Skip-trace (owner contact lookup).

Real implementations: BatchData, REIPro, PropStream, Whitepages, IDI Data.
All paid. We expose a single `lookup(parcel_key, address)` interface.
When no provider is configured, return deterministic mock data so the
UI can be built end-to-end.

Set one of these env vars to enable live providers:
  BATCHDATA_API_KEY
  PROPSTREAM_API_KEY
  WHITEPAGES_API_KEY
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict, List

log = logging.getLogger(__name__)


def _has_real_provider() -> bool:
    return any(
        os.environ.get(k)
        for k in ("BATCHDATA_API_KEY", "PROPSTREAM_API_KEY", "WHITEPAGES_API_KEY")
    )


def _mock_phone(seed: str) -> str:
    h = hashlib.sha1(seed.encode()).hexdigest()
    area = (int(h[:3], 16) % 700) + 200          # 200-899
    nxx = (int(h[3:6], 16) % 700) + 200
    line = int(h[6:10], 16) % 10000
    return f"({area}) {nxx:03d}-{line:04d}"


def _mock_email(seed: str) -> str:
    h = hashlib.sha1(seed.encode()).hexdigest()[:8]
    return f"owner.{h}@example.com"


def _mock_name(seed: str) -> str:
    first = ["James", "Linda", "Robert", "Mary", "Michael", "Patricia", "John", "Jennifer"]
    last = ["Hansen", "Martinez", "Cohen", "Patel", "Nguyen", "Williams", "Thompson", "Lee"]
    h = int(hashlib.sha1(seed.encode()).hexdigest(), 16)
    return f"{first[h % len(first)]} {last[(h // 11) % len(last)]}"


def lookup(parcel_key: str, address: str | None = None, known_owner_name: str | None = None) -> Dict[str, Any]:
    """Return owner contact info.

    If we already know the owner name (from ATTOM during scrape), surface it
    directly. Phones/emails still require a paid provider; until one is wired,
    those stay mock so the UI works in dev.
    """
    if _has_real_provider():
        # TODO: wire provider HTTP call.
        # Each vendor differs: BatchData uses POST /property/skip-trace,
        # PropStream uses /v1/skiptrace/property, etc. Until a key is set,
        # we deliberately fall through to mock so the UI works in dev.
        log.warning("Skip-trace provider env var set but client not implemented yet — returning mock")

    seed = parcel_key + (address or "")
    phones: List[Dict[str, str]] = [
        {"number": _mock_phone(seed), "type": "Mobile", "confidence": "high"},
        {"number": _mock_phone(seed + "h"), "type": "Landline", "confidence": "medium"},
    ]
    emails: List[Dict[str, str]] = [
        {"address": _mock_email(seed), "confidence": "medium"},
    ]
    # Real owner name from ATTOM beats the mock name
    owner_name = known_owner_name or _mock_name(seed)
    has_real_name = bool(known_owner_name)
    return {
        "provider": "attom" if has_real_name else "mock",
        "owner_name": owner_name,
        "phones": phones,
        "emails": emails,
        "mailing_address": None,
        "notes": (
            "Owner name from public assessor (ATTOM). Phone + email mocked — "
            "set BATCHDATA_API_KEY / PROPSTREAM_API_KEY for real contact lookup."
        ) if has_real_name else (
            "Mock data — set BATCHDATA_API_KEY / PROPSTREAM_API_KEY for real lookups."
        ),
    }
