"""
Address → canonical parcel matcher.

Raw scraper output has messy addresses ("1234 N STEVENS ST TACOMA WA",
"1234 North Stevens St", "1234 N. Stevens Street, Tacoma, WA 98403").
We need to collapse them all to the same APN so sources can dedupe.

Strategy:
  1. Normalize the raw string (uppercase, strip, collapse whitespace,
     spell-out directionals/street-types). Produces a canonical string.
  2. Hash the canonical string → parcel_key.
  3. If we have a real county assessor lookup (we will, see note below),
     replace the hash with the authoritative APN.

The hash fallback is correct enough to dedupe within a single scraping
run. Once the assessor parcel-lookup service is wired up, we replace
`_parcel_from_hash` with `_parcel_from_assessor`.

This file is intentionally small and dependency-free — it gets
imported into every scraper's downstream pipeline.
"""
from __future__ import annotations

import hashlib
import re

# USPS-style abbreviations → canonical full word.
STREET_TYPE_MAP = {
    "ST": "STREET", "STR": "STREET", "STREET": "STREET",
    "AVE": "AVENUE", "AV": "AVENUE", "AVENUE": "AVENUE",
    "BLVD": "BOULEVARD", "BOULEVARD": "BOULEVARD",
    "DR": "DRIVE", "DRIVE": "DRIVE",
    "RD": "ROAD", "ROAD": "ROAD",
    "LN": "LANE", "LANE": "LANE",
    "CT": "COURT", "COURT": "COURT",
    "PL": "PLACE", "PLACE": "PLACE",
    "WAY": "WAY",
    "PKWY": "PARKWAY", "PARKWAY": "PARKWAY",
    "HWY": "HIGHWAY", "HIGHWAY": "HIGHWAY",
    "CIR": "CIRCLE", "CIRCLE": "CIRCLE",
    "TERR": "TERRACE", "TERRACE": "TERRACE",
}

DIRECTION_MAP = {
    "N": "NORTH", "NORTH": "NORTH",
    "S": "SOUTH", "SOUTH": "SOUTH",
    "E": "EAST",  "EAST":  "EAST",
    "W": "WEST",  "WEST":  "WEST",
    "NE": "NORTHEAST", "NW": "NORTHWEST",
    "SE": "SOUTHEAST", "SW": "SOUTHWEST",
    "NORTHEAST": "NORTHEAST", "NORTHWEST": "NORTHWEST",
    "SOUTHEAST": "SOUTHEAST", "SOUTHWEST": "SOUTHWEST",
}

UNIT_RE = re.compile(r"\b(APT|SUITE|STE|UNIT|#)\s*[A-Z0-9]+", re.I)
ZIP_RE  = re.compile(r"\b\d{5}(?:-\d{4})?\b")
PUNCT   = re.compile(r"[.,;:]")


def normalize_address(raw: str | None) -> str | None:
    """Return a canonical uppercase, expanded, unit-stripped form.
    Returns None if the input has no usable signal."""
    if not raw:
        return None
    s = raw.upper().strip()
    s = PUNCT.sub(" ", s)
    s = UNIT_RE.sub("", s)
    s = ZIP_RE.sub("", s)
    s = re.sub(r"\bWA\b", "", s)  # state letters add no info once we know county
    s = re.sub(r"\s+", " ", s).strip()

    tokens = s.split()
    expanded = []
    for t in tokens:
        if t in DIRECTION_MAP:
            expanded.append(DIRECTION_MAP[t])
        elif t in STREET_TYPE_MAP:
            expanded.append(STREET_TYPE_MAP[t])
        else:
            expanded.append(t)
    return " ".join(expanded) or None


def parcel_key(address: str | None, apn: str | None = None) -> str | None:
    """Pick the best available stable key for a property.

    When we have a real APN from the source, use it — that's authoritative.
    Otherwise hash the normalized address."""
    if apn:
        return f"apn:{apn.strip().upper()}"
    norm = normalize_address(address)
    if not norm:
        return None
    return "addr:" + hashlib.sha1(norm.encode()).hexdigest()[:16]


# ---------- future: real assessor lookup ----------
#
# Each of the three counties exposes a parcel-search web service. We'll
# wrap each in a small async helper here:
#
#   async def pierce_apn_from_address(address: str) -> str | None:
#   async def king_apn_from_address(address: str) -> str | None:
#   async def thurston_apn_from_address(address: str) -> str | None:
#
# And a county-dispatching helper:
#
#   async def apn_for(address: str, county: str) -> str | None:
#
# Until those are wired, `parcel_key` falls back to the hash and
# downstream dedup still works correctly within a single pipeline run.
