"""Skip-trace provider HTTP clients.

Two real providers + a deterministic mock:

- BatchData (standard tier)  — POST https://api.batchdata.com/api/v1/property/skip-trace
- TLOxp     (pro tier)       — POST https://api.tlo.com/v3/skiptrace
- mock                       — deterministic fake data so the UI works in dev

Each client returns the canonical `dict` shape the rest of the app expects:

    {
        "provider": "<name>",
        "owner_name": str | None,
        "phones":  [ { "number": str, "type": str, "confidence": str } ],
        "emails":  [ { "address": str, "confidence": str } ],
        "mailing_address": str | None,
        "raw": <provider response, kept only when DEBUG_SKIP_TRACE is set>,
    }

Real providers fall back to mock + a logged warning if their HTTP call fails,
so a misconfigured key never breaks the UI.
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

BATCHDATA_URL = os.environ.get(
    "BATCHDATA_URL",
    "https://api.batchdata.com/api/v1/property/skip-trace",
)
TLO_URL = os.environ.get("TLO_URL", "https://api.tlo.com/v3/skiptrace")
DEBUG = bool(os.environ.get("DEBUG_SKIP_TRACE"))
HTTP_TIMEOUT = 12.0


# ---------- Public dispatch ----------------------------------------------------

def lookup(
    tier: str,
    parcel_key: str,
    address: str | None,
    known_owner_name: str | None,
) -> dict[str, Any]:
    """Resolve owner contact for a single parcel using the requested tier.

    Falls back to mock when the configured provider key is missing.
    """
    if tier == "pro":
        key = os.environ.get("TLO_API_KEY") or os.environ.get("TLOXP_API_KEY")
        if key:
            try:
                return _tlo_lookup(key, parcel_key, address, known_owner_name)
            except Exception as exc:  # pragma: no cover — network path
                log.warning("TLOxp lookup failed (%s); using mock fallback", exc)
        return _mock(parcel_key, address, known_owner_name, provider="mock-pro")

    # default → standard
    key = os.environ.get("BATCHDATA_API_KEY")
    if key:
        try:
            return _batchdata_lookup(key, parcel_key, address, known_owner_name)
        except Exception as exc:  # pragma: no cover — network path
            log.warning("BatchData lookup failed (%s); using mock fallback", exc)
    return _mock(parcel_key, address, known_owner_name, provider="mock-standard")


# ---------- BatchData ----------------------------------------------------------

def _batchdata_lookup(
    api_key: str,
    parcel_key: str,
    address: str | None,
    known_owner_name: str | None,
) -> dict[str, Any]:
    street, city, state, zip_ = _split_address(address)
    payload = {
        "requests": [
            {
                "propertyAddress": {
                    "street": street,
                    "city": city,
                    "state": state,
                    "zip": zip_,
                },
                **(_split_name(known_owner_name) or {}),
            }
        ]
    }
    with httpx.Client(timeout=HTTP_TIMEOUT) as cx:
        r = cx.post(
            BATCHDATA_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        r.raise_for_status()
        data = r.json()

    # BatchData response: { "results": { "persons": [ { name, phoneNumbers, emails, ... } ] } }
    persons = (
        (data.get("results") or {}).get("persons")
        or data.get("persons")
        or []
    )
    person = persons[0] if persons else {}

    phones = []
    for p in person.get("phoneNumbers") or []:
        phones.append(
            {
                "number": _format_phone(p.get("number") or p.get("phone") or ""),
                "type": (p.get("type") or "Mobile").title(),
                "confidence": (p.get("confidence") or "medium").lower(),
            }
        )
    emails = []
    for e in person.get("emails") or []:
        emails.append(
            {
                "address": e.get("address") or e.get("email") or "",
                "confidence": (e.get("confidence") or "medium").lower(),
            }
        )
    name = person.get("name") or {}
    full_name = (
        " ".join(filter(None, [name.get("first"), name.get("last")]))
        or known_owner_name
    )
    mailing = _format_mailing(person.get("mailingAddress") or {})

    out = {
        "provider": "batchdata",
        "owner_name": full_name,
        "phones": [p for p in phones if p["number"]],
        "emails": [e for e in emails if e["address"]],
        "mailing_address": mailing,
    }
    if DEBUG:
        out["raw"] = data
    return out


# ---------- TLOxp --------------------------------------------------------------

def _tlo_lookup(
    api_key: str,
    parcel_key: str,
    address: str | None,
    known_owner_name: str | None,
) -> dict[str, Any]:
    street, city, state, zip_ = _split_address(address)
    name = _split_name(known_owner_name) or {}
    payload = {
        "address": {"line1": street, "city": city, "state": state, "zip": zip_},
        "name": {"first": name.get("first"), "last": name.get("last")},
        "permissiblePurpose": "BFR",  # caller has GLBA-compliant purpose
    }
    with httpx.Client(timeout=HTTP_TIMEOUT) as cx:
        r = cx.post(
            TLO_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
        )
        r.raise_for_status()
        data = r.json()

    subj = (data.get("subject") or data.get("result") or {})
    phones = [
        {
            "number": _format_phone(p.get("number") or ""),
            "type": (p.get("lineType") or p.get("type") or "Mobile").title(),
            "confidence": (p.get("confidence") or "high").lower(),
        }
        for p in subj.get("phones") or []
    ]
    emails = [
        {
            "address": e.get("address") or "",
            "confidence": (e.get("confidence") or "high").lower(),
        }
        for e in subj.get("emails") or []
    ]
    full_name = subj.get("fullName") or known_owner_name
    mailing = _format_mailing(subj.get("currentAddress") or {})

    out = {
        "provider": "tlo",
        "owner_name": full_name,
        "phones": [p for p in phones if p["number"]],
        "emails": [e for e in emails if e["address"]],
        "mailing_address": mailing,
    }
    if DEBUG:
        out["raw"] = data
    return out


# ---------- Mock (deterministic) ----------------------------------------------

def _mock(
    parcel_key: str,
    address: str | None,
    known_owner_name: str | None,
    *,
    provider: str,
) -> dict[str, Any]:
    seed = parcel_key + (address or "")
    h = hashlib.sha1(seed.encode()).hexdigest()
    area = (int(h[:3], 16) % 700) + 200
    nxx = (int(h[3:6], 16) % 700) + 200
    line = int(h[6:10], 16) % 10000
    fake_phone = f"({area}) {nxx:03d}-{line:04d}"
    email_h = h[:8]

    fakes_first = ["James", "Linda", "Robert", "Mary", "Michael", "Patricia", "John", "Jennifer"]
    fakes_last = ["Hansen", "Martinez", "Cohen", "Patel", "Nguyen", "Williams", "Thompson", "Lee"]
    name_h = int(h, 16)
    fake_name = (
        known_owner_name
        or f"{fakes_first[name_h % len(fakes_first)]} {fakes_last[(name_h // 11) % len(fakes_last)]}"
    )
    return {
        "provider": provider,
        "owner_name": fake_name,
        "phones": [
            {"number": fake_phone, "type": "Mobile", "confidence": "high"},
        ],
        "emails": [
            {"address": f"owner.{email_h}@example.com", "confidence": "medium"},
        ],
        "mailing_address": None,
    }


# ---------- Helpers ------------------------------------------------------------

def _split_address(addr: str | None) -> tuple[str, str, str, str]:
    if not addr:
        return ("", "", "", "")
    parts = [p.strip() for p in addr.split(",")]
    street = parts[0] if parts else ""
    city = parts[1] if len(parts) > 1 else ""
    state = ""
    zip_ = ""
    if len(parts) > 2:
        tail = parts[2].split()
        if tail:
            state = tail[0]
        if len(tail) > 1:
            zip_ = tail[1]
    return (street, city, state, zip_)


def _split_name(full: str | None) -> dict[str, str] | None:
    if not full:
        return None
    bits = full.strip().split()
    if not bits:
        return None
    if len(bits) == 1:
        return {"first": bits[0], "last": ""}
    return {"first": bits[0], "last": " ".join(bits[1:])}


def _format_phone(raw: str) -> str:
    digits = "".join(c for c in str(raw) if c.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw


def _format_mailing(addr: dict[str, Any]) -> str | None:
    if not addr:
        return None
    line1 = addr.get("line1") or addr.get("street") or ""
    city = addr.get("city") or ""
    state = addr.get("state") or ""
    zip_ = addr.get("zip") or addr.get("postalCode") or ""
    parts = [line1, ", ".join(filter(None, [city, state])), zip_]
    out = " ".join(p for p in parts if p).strip()
    return out or None
