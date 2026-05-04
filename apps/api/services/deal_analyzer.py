"""Deal Analyzer — given an address, return a full investment thesis.

Lookup ladder (cheapest first; richest if available):
  1. Our own DB — if we already scraped this parcel, return that row.
  2. PropertyRadar — if PROPERTYRADAR_API_KEY set, query by address.
  3. ATTOM — fallback enrichment via /property/basicprofile.
  4. Geocode-only — at minimum, return location + ADU score from
     state law, even when no parcel match.

The returned shape is what the frontend renders directly:

  {
    address, city, state, zip, county, lat, lng,
    parcel_apn, owner_name, year_built, beds, baths, sqft, lot_sqft,
    estimated_value, assessed_value, loan_balance,
    distress: { tags: [...], factors: [...] }
    deal: { score, band, breakdown, equity, ltv, spread_pct }
    adu:  { score, band, units_possible, breakdown, notes }
    sources: { off_market: bool, propertyradar: bool, attom: bool }
  }
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from services import adu_scoring, batchdata_client as bd, deal_scoring
from services import propertyradar_client as pr  # kept for future partner-OAuth integration
from storage.off_market_db import _conn, _ph

log = logging.getLogger(__name__)

MAPBOX_TOKEN = os.environ.get("MAPBOX_API_KEY") or os.environ.get("VITE_MAPBOX_TOKEN")
ATTOM_API_KEY = os.environ.get("ATTOM_API_KEY")
ATTOM_BASE = "https://api.gateway.attomdata.com/propertyapi/v1.0.0"


# ---- Geocoding ----------------------------------------------------------

async def geocode(address: str) -> dict[str, Any] | None:
    """Resolve a free-text address → {street, city, state, zip, lat, lng}.

    Uses Mapbox if a token is available; falls back to a rough parser
    so the analyzer still works in dev with no token.
    """
    addr = (address or "").strip()
    if not addr:
        return None

    if MAPBOX_TOKEN:
        url = (
            "https://api.mapbox.com/geocoding/v5/mapbox.places/"
            f"{httpx.QueryParams({'q': addr})}".replace("q=", "") + ".json"
        )
        # cleaner: use Mapbox URL pattern directly
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{addr}.json"
        try:
            async with httpx.AsyncClient(timeout=10.0) as cx:
                r = await cx.get(
                    url,
                    params={
                        "access_token": MAPBOX_TOKEN,
                        "country": "us",
                        "types": "address,postcode,place",
                        "limit": 1,
                    },
                )
                r.raise_for_status()
                data = r.json()
                feats = data.get("features") or []
                if feats:
                    f = feats[0]
                    ctx = {c.get("id", "").split(".")[0]: c for c in f.get("context", [])}
                    return {
                        "address": (f.get("text") or "") + " " + (f.get("address") or ""),
                        "full":     f.get("place_name"),
                        "lng":      f.get("center", [None, None])[0],
                        "lat":      f.get("center", [None, None])[1],
                        "city":     ctx.get("place", {}).get("text"),
                        "state":    (ctx.get("region", {}).get("short_code") or "").replace("US-", ""),
                        "zip":      ctx.get("postcode", {}).get("text"),
                        "county":   ctx.get("district", {}).get("text"),
                    }
        except Exception as exc:
            log.warning("Mapbox geocode failed: %s", exc)

    # Best-effort parse fallback so the analyzer still works without
    # Mapbox configured. We pull `STATE_CODE` (2 caps) and 5-digit zip
    # straight out of the typed address — good enough for ADU scoring
    # which only needs state.
    import re
    state_m = re.search(r"\b([A-Z]{2})\b(?!\d)", addr)
    zip_m   = re.search(r"\b(\d{5})(?:-\d{4})?\b", addr)
    # crude "City" extraction. Two common shapes:
    #   "123 Main St, Seattle, WA 98101"   → 3 parts, parts[1] is city
    #   "123 Main St, Seattle WA 98101"    → 2 parts, the trailing
    #                                         chunk has "City STATE ZIP"
    parts = [p.strip() for p in addr.split(",")]
    city = None
    if len(parts) >= 3:
        city = parts[-2]
    elif len(parts) == 2 and state_m:
        # Pull the city out of "Seattle WA 98101" — everything before
        # the 2-letter state code.
        tail = parts[-1]
        idx = tail.find(state_m.group(1))
        if idx > 0:
            city = tail[:idx].strip().rstrip(",")
    return {
        "address": parts[0] if parts else addr,
        "full":    addr,
        "lat":     None,
        "lng":     None,
        "city":    city,
        "state":   state_m.group(1) if state_m else None,
        "zip":     zip_m.group(1)   if zip_m   else None,
        "county":  None,
    }


# ---- Lookup ladder ------------------------------------------------------

async def lookup_property(address_block: dict[str, Any]) -> dict[str, Any] | None:
    """Lookup ladder: DB → BatchData → ATTOM → geocode-only.

    PropertyRadar is intentionally NOT in this chain — their ToS
    forbids serving their data inside an application sold to others
    without a partner / OAuth agreement. The PR scraper code remains
    in the repo (services/propertyradar_client.py) so we can re-enable
    it once we're an approved PR partner.
    """
    rec = _from_db(address_block)
    if rec:
        rec["source_origin"] = "off_market_db"
        return rec

    if bd.is_live():
        rec = await _from_batchdata(address_block)
        if rec:
            rec["source_origin"] = "batchdata"
            return rec

    if ATTOM_API_KEY:
        rec = await _from_attom(address_block)
        if rec:
            rec["source_origin"] = "attom"
            return rec

    return None


def _from_db(addr: dict[str, Any]) -> dict[str, Any] | None:
    """Look up by address text + city + state — fuzzy enough to catch
    a parcel we already scraped."""
    address = (addr.get("address") or addr.get("full") or "").strip()
    if not address:
        return None
    state = (addr.get("state") or "").upper()
    city = (addr.get("city") or "")
    try:
        with _conn() as (cur, dialect):
            ph = _ph(dialect)
            # Try exact match first
            cur.execute(
                f"""SELECT parcel_key, parcel_apn, address, city, county, state, zip,
                          source_tags, default_amount, sale_date, asking_price,
                          lien_amount, years_delinquent, vacancy_months,
                          owner_state, owner_name, latitude, longitude,
                          estimated_value, assessed_value, loan_balance,
                          property_type, bedrooms, bathrooms, sqft, lot_sqft,
                          year_built, last_seen
                   FROM off_market_listings
                   WHERE LOWER(address) LIKE LOWER({ph}) AND state = {ph}
                   LIMIT 1""",
                (f"%{address[:60]}%", state),
            )
            row = cur.fetchone()
            if not row:
                return None
            d = dict(row) if isinstance(row, dict) else dict(zip(
                ["parcel_key","parcel_apn","address","city","county","state","zip",
                 "source_tags","default_amount","sale_date","asking_price","lien_amount",
                 "years_delinquent","vacancy_months","owner_state","owner_name",
                 "latitude","longitude","estimated_value","assessed_value","loan_balance",
                 "property_type","bedrooms","bathrooms","sqft","lot_sqft","year_built","last_seen"],
                row,
            ))
            # Normalize source_tags JSON
            import json
            t = d.get("source_tags")
            if isinstance(t, str):
                try:
                    d["source_tags"] = json.loads(t)
                except Exception:
                    d["source_tags"] = []
            elif t is None:
                d["source_tags"] = []
            return d
    except Exception as exc:
        log.warning("DB lookup failed: %s", exc)
        return None


async def _from_batchdata(addr: dict[str, Any]) -> dict[str, Any] | None:
    """Query BatchData /api/v1/property/search by address. Returns the
    first match or None.

    BatchData licenses their property API for SaaS resale (their
    Platform tier), so we can serve this data to OnlyOffMarkets
    customers without ToS issues. Same key powers our skip-trace.
    """
    address = (addr.get("address") or "").strip()
    state = (addr.get("state") or "").upper()
    city = (addr.get("city") or "").strip()
    zip_ = (addr.get("zip") or "").strip()
    if not address:
        return None

    # Build the address-targeted search criteria. BatchData supports
    # exact-address lookup via the searchCriteria.address block.
    crit: dict[str, Any] = {"address": {"street": {"any": [address]}}}
    if state: crit["address"]["state"] = {"any": [state]}
    if city:  crit["address"]["city"]  = {"any": [city]}
    if zip_:  crit["address"]["zip"]   = {"any": [zip_]}

    rows = await bd.search(crit, page=1, take=1)
    if not rows:
        return None
    p = rows[0]
    addr_p = p.get("address") or {}
    owner  = p.get("owner") or {}
    val    = p.get("valuation") or {}
    mort   = p.get("mortgage") or {}
    fc     = p.get("foreclosure") or {}
    bldg   = p.get("building") or {}
    geo    = (addr_p.get("location") or {}) if isinstance(addr_p, dict) else {}

    # Equity %: prefer BatchData's explicit value if present
    eq_pct_raw = p.get("equityPercent") or val.get("equityPercent")
    eq_pct = None
    if eq_pct_raw is not None:
        try:
            v = float(eq_pct_raw)
            eq_pct = v / 100.0 if v > 1 else v
        except (TypeError, ValueError):
            eq_pct = None

    fc_stage_raw = (fc.get("stage") or fc.get("type") or "").lower()
    fc_stage = None
    if fc_stage_raw:
        if "auction" in fc_stage_raw or "trustee" in fc_stage_raw: fc_stage = "AUCTION"
        elif "nts" in fc_stage_raw:                                 fc_stage = "NTS"
        elif "nod" in fc_stage_raw or "lis" in fc_stage_raw:        fc_stage = "NOD"

    # Distress tag list inferred from BatchData flags
    tags: list[str] = []
    if fc_stage in ("NOD", "NTS"):    tags.append("preforeclosure")
    if fc_stage == "AUCTION":         tags.append("auction")
    if p.get("taxDelinquent") or (p.get("taxDelinquentYears") or 0) > 0:
        tags.append("tax-lien")
    if p.get("vacant"):               tags.append("vacant")
    if p.get("inProbate"):            tags.append("probate")

    return {
        "parcel_apn":  str(p.get("apn") or addr_p.get("parcelNumber") or ""),
        "address":     str(addr_p.get("street") or addr_p.get("line1") or address),
        "city":        addr_p.get("city"),
        "county":      addr_p.get("county"),
        "state":       addr_p.get("state") or state,
        "zip":         str(addr_p.get("zip") or "") or None,
        "owner_name":  owner.get("fullName") or " ".join(filter(None, [owner.get("firstName"), owner.get("lastName")])) or None,
        "owner_state": (owner.get("mailingAddress") or {}).get("state"),
        "estimated_value": _int(val.get("estimatedValue") or val.get("avm")),
        "assessed_value":  _int(val.get("assessedValue")),
        "loan_balance":    _int(mort.get("balance") or mort.get("estimatedBalance")),
        "bedrooms":   _int(bldg.get("bedrooms") or bldg.get("beds")),
        "bathrooms":  _float(bldg.get("bathrooms") or bldg.get("baths")),
        "sqft":       _int(bldg.get("livingArea") or bldg.get("buildingSqFt")),
        "lot_sqft":   _int(bldg.get("lotSize") or bldg.get("lotSqFt")),
        "year_built": _int(bldg.get("yearBuilt")),
        "property_type": _norm_type(bldg.get("propertyType") or bldg.get("propertyUse")),
        "latitude":   _float(geo.get("lat") or geo.get("latitude")),
        "longitude":  _float(geo.get("lng") or geo.get("longitude")),
        "source_tags": tags,
        "default_amount": _int(fc.get("defaultAmount")),
        "sale_date": fc.get("saleDate") or fc.get("auctionDate"),
        "years_delinquent": _int(p.get("taxDelinquentYears")),
        "vacancy_months": _int(p.get("vacancyMonths")),

        # Paid-source enrichment for the scoring service
        "foreclosure_stage": fc_stage,
        "equity_pct":        eq_pct,
        "years_owned":       _int(p.get("yearsOwned") or owner.get("yearsOwned")),
        "last_sale_date":    p.get("lastSaleDate") or p.get("priorSaleDate"),
        "last_sale_price":   _int(p.get("lastSalePrice") or p.get("priorSalePrice")),
        "mortgage_count":    _int(mort.get("count")),
        "mortgage_orig_year": _int(mort.get("originationYear") or mort.get("originatedYear")),
        "hoa_delinquent":    bool(p.get("hoaDelinquent")) if p.get("hoaDelinquent") is not None else None,
    }


async def _from_propertyradar(addr: dict[str, Any]) -> dict[str, Any] | None:
    """Query PropertyRadar by address. Returns the first match or None."""
    address = (addr.get("address") or "").strip()
    state = (addr.get("state") or "").upper()
    if not address:
        return None
    criteria = [{"name": "SiteAddress", "value": [address]}]
    rows = await pr.search_properties(criteria, states=[state] if state else None, limit=1)
    if not rows:
        return None
    p = rows[0]

    def f(*names):
        for n in names:
            v = p.get(n)
            if v not in (None, "", []):
                return v
        return None
    # Equity %: prefer PR's explicit value when present (more accurate
    # than our derived loan/value because it incorporates junior liens).
    eq_pct_raw = f("EquityPercent", "equity_percent")
    if eq_pct_raw is not None:
        try:
            v = float(eq_pct_raw)
            eq_pct = v / 100.0 if v > 1 else v   # tolerate 0-1 vs 0-100 forms
        except (TypeError, ValueError):
            eq_pct = None
    else:
        eq_pct = None

    return {
        "parcel_apn":  str(f("APN", "ParcelNumber", "apn") or ""),
        "address":     str(f("SiteAddress", "address") or address),
        "city":        f("SiteCity", "city"),
        "county":      f("County", "county"),
        "state":       f("SiteState", "state") or state,
        "zip":         str(f("SiteZip", "zip") or "") or None,
        "owner_name":  f("OwnerName", "owner_name"),
        "owner_state": f("OwnerState", "OwnerMailingState"),
        "estimated_value": _int(f("AVM", "EstimatedValue")),
        "assessed_value":  _int(f("AssessedValue")),
        "loan_balance":    _int(f("EstimatedMortgageBalance", "LoanBalance")),
        "bedrooms":   _int(f("Bedrooms", "Beds")),
        "bathrooms":  _float(f("Bathrooms", "Baths")),
        "sqft":       _int(f("LivingArea", "BuildingSqFt")),
        "lot_sqft":   _int(f("LotArea", "LotSqFt")),
        "year_built": _int(f("YearBuilt")),
        "property_type": _norm_type(f("PropertyType", "PropertyUse")),
        "latitude":   _float(f("Latitude", "lat")),
        "longitude":  _float(f("Longitude", "lng")),
        "source_tags": _pr_distress_tags(p),
        "default_amount": _int(f("DefaultAmount")),
        "sale_date": f("AuctionDate", "TrusteeSaleDate"),
        "years_delinquent": _int(f("TaxDelinquentYears")),
        "vacancy_months": _int(f("VacancyMonths")),

        # Paid-source enrichment for the scoring service
        "foreclosure_stage": (f("ForeclosureStage") or "").upper() or None,
        "equity_pct":        eq_pct,
        "years_owned":       _int(f("YearsOwned", "OwnerYears")),
        "last_sale_date":    f("LastSaleDate", "PriorSaleDate"),
        "last_sale_price":   _int(f("LastSalePrice", "PriorSalePrice")),
        "mortgage_count":    _int(f("MortgageCount")),
        "mortgage_orig_year": _int(f("FirstMortgageOriginationYear", "MortgageOriginationYear")),
        "hoa_delinquent":    bool(f("HOADelinquent")) if f("HOADelinquent") is not None else None,
    }


def _pr_distress_tags(p: dict) -> list[str]:
    out = []
    fc = (p.get("ForeclosureStage") or "").lower()
    if fc in ("nod", "nts"):  out.append("preforeclosure")
    if fc == "auction":       out.append("auction")
    if p.get("TaxDelinquentYears"):     out.append("tax-lien")
    if p.get("InProbate"):              out.append("probate")
    if p.get("Vacant"):                 out.append("vacant")
    return out


async def _from_attom(addr: dict[str, Any]) -> dict[str, Any] | None:
    """ATTOM /property/basicprofile by address."""
    address = (addr.get("address") or "").strip()
    state = (addr.get("state") or "").upper()
    city = (addr.get("city") or "").strip()
    zip_ = (addr.get("zip") or "").strip()
    if not address:
        return None
    try:
        async with httpx.AsyncClient(timeout=12.0) as cx:
            r = await cx.get(
                f"{ATTOM_BASE}/property/basicprofile",
                params={
                    "address1": address,
                    "address2": " ".join(p for p in [city, state, zip_] if p).strip(),
                },
                headers={
                    "Accept": "application/json",
                    "apikey": ATTOM_API_KEY,
                },
            )
            if r.status_code != 200:
                return None
            data = r.json()
    except Exception as exc:
        log.warning("ATTOM lookup failed: %s", exc)
        return None
    props = (data or {}).get("property") or []
    if not props:
        return None
    p = props[0]
    addr_p = p.get("address") or {}
    summ   = p.get("summary") or {}
    bldg   = p.get("building") or {}
    rooms  = (bldg.get("rooms") or {})
    size   = (bldg.get("size") or {})
    lot    = p.get("lot") or {}
    valu   = p.get("avm") or {}
    asses  = p.get("assessment") or {}
    location = p.get("location") or {}
    owner = ((asses.get("owner") or {}).get("owner1") or {})
    return {
        "parcel_apn": p.get("identifier", {}).get("apn"),
        "address": addr_p.get("oneLine") or address,
        "city": addr_p.get("locality"),
        "county": addr_p.get("countrySubd"),
        "state": addr_p.get("countrySubd") or state,
        "zip": addr_p.get("postal1"),
        "owner_name": owner.get("fullName"),
        "owner_state": ((asses.get("owner") or {}).get("mailingaddressoneline") or "")[-2:] or None,
        "estimated_value": _int((valu.get("amount") or {}).get("value")),
        "assessed_value": _int((asses.get("assessed") or {}).get("assdttlvalue")),
        "loan_balance": None,
        "bedrooms": _int(rooms.get("beds")),
        "bathrooms": _float(rooms.get("bathstotal")),
        "sqft": _int(size.get("universalsize")),
        "lot_sqft": _int(lot.get("lotsize2") or lot.get("lotSize")),
        "year_built": _int(summ.get("yearbuilt")),
        "property_type": _norm_type(summ.get("propclass") or summ.get("proptype")),
        "latitude": _float(location.get("latitude")),
        "longitude": _float(location.get("longitude")),
        "source_tags": [],
        "default_amount": None, "sale_date": None,
        "years_delinquent": None, "vacancy_months": None,
    }


# ---- Helpers ------------------------------------------------------------

def _int(v):
    try:
        if v is None or v == "": return None
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _float(v):
    try:
        if v is None or v == "": return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _norm_type(s):
    if not s: return None
    t = str(s).lower()
    if "single" in t or "sfr" in t: return "single_family"
    if "condo" in t:                return "condo"
    if "town" in t:                 return "townhome"
    if "multi" in t or "duplex" in t: return "multi_family"
    if "land" in t or "vacant lot" in t: return "land"
    if "commercial" in t:           return "commercial"
    if "manufactur" in t or "mobile" in t: return "manufactured"
    return "other"


# ---- Orchestrator -------------------------------------------------------

async def analyze(address: str) -> dict[str, Any]:
    """Top-level entry point. Returns the full analysis dict."""
    addr = await geocode(address) or {"address": address}

    prop = await lookup_property(addr) or {}
    # Merge geocoded coords if the lookup didn't include them
    if prop.get("latitude") is None and addr.get("lat") is not None:
        prop["latitude"] = addr["lat"]
    if prop.get("longitude") is None and addr.get("lng") is not None:
        prop["longitude"] = addr["lng"]

    # Equity / LTV / spread
    est_val   = prop.get("estimated_value") or prop.get("assessed_value")
    loan      = prop.get("loan_balance")
    asking    = prop.get("asking_price")
    ltv       = (loan / est_val) if (est_val and loan and est_val > 0) else None
    equity    = (est_val - loan) if (est_val and loan is not None) else None
    spread_pct = ((est_val - asking) / est_val) if (est_val and asking and est_val > 0) else None

    # ADU
    adu = adu_scoring.score_adu(
        state=prop.get("state") or addr.get("state"),
        property_type=prop.get("property_type"),
        lot_sqft=prop.get("lot_sqft"),
        sqft=prop.get("sqft"),
        year_built=prop.get("year_built"),
    )

    # Authoritative deal score using all fields we extracted.
    deal = deal_scoring.score_deal({
        **prop,
        "state": (prop.get("state") or addr.get("state") or "").upper(),
        "estimated_value": est_val,
        "loan_balance":    loan,
        "asking_price":    asking,
    })
    return {
        "query":   address,
        "address": prop.get("address") or addr.get("full") or address,
        "city":    prop.get("city") or addr.get("city"),
        "county":  prop.get("county") or addr.get("county"),
        "state":   (prop.get("state") or addr.get("state") or "").upper() or None,
        "zip":     prop.get("zip") or addr.get("zip"),
        "lat":     prop.get("latitude")  or addr.get("lat"),
        "lng":     prop.get("longitude") or addr.get("lng"),

        "parcel_apn": prop.get("parcel_apn"),
        "owner_name": prop.get("owner_name"),
        "owner_state": prop.get("owner_state"),

        "year_built": prop.get("year_built"),
        "bedrooms":   prop.get("bedrooms"),
        "bathrooms":  prop.get("bathrooms"),
        "sqft":       prop.get("sqft"),
        "lot_sqft":   prop.get("lot_sqft"),
        "property_type": prop.get("property_type"),

        "estimated_value": est_val,
        "assessed_value":  prop.get("assessed_value"),
        "loan_balance":    loan,
        "asking_price":    asking,
        "ltv":             ltv,
        "equity":          equity,
        "spread_pct":      spread_pct,

        "distress": {
            "tags":              prop.get("source_tags") or [],
            "default_amount":    prop.get("default_amount"),
            "sale_date":         prop.get("sale_date"),
            "years_delinquent":  prop.get("years_delinquent"),
            "vacancy_months":    prop.get("vacancy_months"),
            "foreclosure_stage": prop.get("foreclosure_stage"),
            "hoa_delinquent":    prop.get("hoa_delinquent"),
        },

        # Owner / sale context (paid sources only)
        "ownership": {
            "years_owned":       prop.get("years_owned"),
            "last_sale_date":    prop.get("last_sale_date"),
            "last_sale_price":   prop.get("last_sale_price"),
            "mortgage_count":    prop.get("mortgage_count"),
            "equity_pct":        prop.get("equity_pct"),
        },

        "deal": deal,
        "adu":  adu,

        "sources": {
            "off_market_db": prop.get("source_origin") == "off_market_db",
            "propertyradar": prop.get("source_origin") == "propertyradar",
            "attom":         prop.get("source_origin") == "attom",
            "found":         bool(prop),
            "geocoder":      "mapbox" if MAPBOX_TOKEN else "fallback",
        },
    }
