"""Mailer templates + campaigns.

Templates: persisted HTML for postcard front + back.
Campaigns: a send job — template + recipients (parcel keys) + sender block.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from services.lob_client import lob_client
from services import identity, tokens_pricing
from services.rate_limit import limiter
from storage import tokens_db
from storage.off_market_db import _conn, _ph, get_one, _resolve_url, _is_postgres

log = logging.getLogger(__name__)

router = APIRouter(prefix="/mailers", tags=["mailers"])


# ---------- schema ----------

SQLITE_MAILER_SCHEMA = """
CREATE TABLE IF NOT EXISTS mailer_templates (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT,
    front_html   TEXT NOT NULL,
    back_html    TEXT NOT NULL,
    size         TEXT DEFAULT '4x6',
    qr_url       TEXT,
    is_preset    INTEGER DEFAULT 0,
    created_at   TEXT,
    updated_at   TEXT
);

CREATE TABLE IF NOT EXISTS mailer_campaigns (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    template_id   TEXT,
    from_name     TEXT,
    from_address_line1 TEXT,
    from_address_city  TEXT,
    from_address_state TEXT,
    from_address_zip   TEXT,
    parcel_keys   TEXT,           -- JSON array
    status        TEXT,            -- draft | sent | failed
    lob_postcard_ids TEXT,         -- JSON array
    sent_count    INTEGER DEFAULT 0,
    error_count   INTEGER DEFAULT 0,
    created_at    TEXT,
    sent_at       TEXT
);
"""

POSTGRES_MAILER_SCHEMA = """
CREATE TABLE IF NOT EXISTS mailer_templates (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT,
    front_html   TEXT NOT NULL,
    back_html    TEXT NOT NULL,
    size         TEXT DEFAULT '4x6',
    qr_url       TEXT,
    is_preset    BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mailer_campaigns (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    template_id   TEXT,
    from_name     TEXT,
    from_address_line1 TEXT,
    from_address_city  TEXT,
    from_address_state TEXT,
    from_address_zip   TEXT,
    parcel_keys   JSONB,
    status        TEXT,
    lob_postcard_ids JSONB,
    sent_count    INTEGER DEFAULT 0,
    error_count   INTEGER DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    sent_at       TIMESTAMPTZ
);
"""


def _ensure_schema() -> None:
    """Lazy create-tables + seed presets on first request."""
    url = _resolve_url()
    now = datetime.now(timezone.utc).isoformat()
    if _is_postgres(url):
        import psycopg
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute(POSTGRES_MAILER_SCHEMA)
                for t in PRESET_TEMPLATES:
                    cur.execute(
                        "INSERT INTO mailer_templates (id, name, description, front_html, back_html, size, is_preset, created_at, updated_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,TRUE,%s,%s) ON CONFLICT (id) DO NOTHING",
                        (t["id"], t["name"], t["description"], t["front_html"],
                         t["back_html"], t["size"], now, now),
                    )
            conn.commit()
    else:
        path = Path(__file__).resolve().parent.parent / ".data" / "off_market.sqlite"
        path.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(str(path))
        try:
            c.executescript(SQLITE_MAILER_SCHEMA)
            c.commit()
            _seed_presets(c)
        finally:
            c.close()


PRESET_TEMPLATES = [
    {
        "id": "preset-cash-offer",
        "name": "Cash offer — minimal",
        "description": "Clean, direct cash-offer postcard with QR scan-to-call.",
        "size": "4x6",
        "front_html": """<html><body style="margin:0;font-family:Helvetica,sans-serif;width:6in;height:4in;background:#0f1f3d;color:#fff;display:flex;align-items:center;justify-content:center;text-align:center;">
<div><h1 style="font-size:48px;margin:0 0 14px;color:#1d6cf2">CASH OFFER</h1>
<p style="font-size:18px;margin:0;letter-spacing:2px">No fees · No repairs · 14-day close</p></div></body></html>""",
        "back_html": """<html><body style="margin:0;font-family:Helvetica,sans-serif;width:6in;height:4in;padding:0.3in;box-sizing:border-box;font-size:14px">
<p>Hi {{to.name}},</p>
<p>I noticed your property at {{property_address}} and wanted to reach out directly. I buy houses in {{property_city}} for cash — no fees, no repairs, no agents.</p>
<p>If a quick, certain sale would help, scan the QR code or call me anytime.</p>
<p style="margin-top:0.25in;">— {{from.name}}</p>
<div style="position:absolute;bottom:0.3in;right:0.3in;width:0.9in;height:0.9in;background:#fff;border:1px solid #ccc;display:flex;align-items:center;justify-content:center;font-size:9px;color:#999">QR</div>
</body></html>""",
    },
    {
        "id": "preset-distressed",
        "name": "Distressed — empathetic",
        "description": "Soft tone for preforeclosure / probate. Reads like a neighbor, not a vulture.",
        "size": "4x6",
        "front_html": """<html><body style="margin:0;font-family:Georgia,serif;width:6in;height:4in;background:#f5f1ea;color:#0f1f3d;display:flex;align-items:center;justify-content:center;text-align:center;">
<div><h1 style="font-size:38px;margin:0 0 10px">A note from a neighbor</h1>
<p style="font-style:italic;font-size:16px;margin:0;color:#666">about your property at {{property_address}}</p></div></body></html>""",
        "back_html": """<html><body style="margin:0;font-family:Georgia,serif;width:6in;height:4in;padding:0.3in;box-sizing:border-box;font-size:13px">
<p>Hi {{to.name}},</p>
<p>I work with families dealing with property situations — inherited homes, behind on taxes, or just ready to be done. No judgment, no pressure.</p>
<p>If a conversation would help, I'm happy to share what your options are. Scan the QR code or call.</p>
<p style="margin-top:0.25in;">— {{from.name}}</p>
<div style="position:absolute;bottom:0.3in;right:0.3in;width:0.9in;height:0.9in;background:#fff;border:1px solid #ccc;display:flex;align-items:center;justify-content:center;font-size:9px;color:#999">QR</div>
</body></html>""",
    },
    {
        "id": "preset-vacant",
        "name": "Vacant property",
        "description": "For absentee owners with vacant or neglected parcels.",
        "size": "4x6",
        "front_html": """<html><body style="margin:0;font-family:Helvetica,sans-serif;width:6in;height:4in;background:#1d6cf2;color:#fff;display:flex;align-items:center;justify-content:center;text-align:center;">
<div><h1 style="font-size:42px;margin:0 0 12px;font-weight:800">Tired of the upkeep?</h1>
<p style="font-size:18px;margin:0">I'd buy {{property_address}} as-is.</p></div></body></html>""",
        "back_html": """<html><body style="margin:0;font-family:Helvetica,sans-serif;width:6in;height:4in;padding:0.3in;box-sizing:border-box;font-size:14px">
<p>Hi {{to.name}},</p>
<p>I noticed your property at {{property_address}} has been unoccupied. Carrying costs, taxes, and travel add up.</p>
<p>I buy properties as-is for cash. No cleanout, no repairs, no agents. If you're ready to be done with it, let's talk.</p>
<p style="margin-top:0.25in;">— {{from.name}}</p>
<div style="position:absolute;bottom:0.3in;right:0.3in;width:0.9in;height:0.9in;background:#fff;border:1px solid #ccc;display:flex;align-items:center;justify-content:center;font-size:9px;color:#999">QR</div>
</body></html>""",
    },
]


def _seed_presets(c) -> None:
    """Insert preset templates into SQLite if missing."""
    now = datetime.now(timezone.utc).isoformat()
    for t in PRESET_TEMPLATES:
        c.execute(
            "INSERT OR IGNORE INTO mailer_templates (id, name, description, front_html, back_html, size, is_preset, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (t["id"], t["name"], t["description"], t["front_html"], t["back_html"],
             t["size"], 1, now, now),
        )
    c.commit()


# ---------- models ----------

class TemplateIn(BaseModel):
    name: str
    description: Optional[str] = None
    front_html: str
    back_html: str
    size: str = "4x6"
    qr_url: Optional[str] = None


class TemplateOut(TemplateIn):
    id: str
    is_preset: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CampaignIn(BaseModel):
    name: str
    template_id: Optional[str] = None      # null → use inline html
    front_html: Optional[str] = None
    back_html: Optional[str] = None
    size: str = "4x6"
    parcel_keys: List[str] = Field(default_factory=list)
    from_name: str
    from_address_line1: str
    from_address_city: str
    from_address_state: str
    from_address_zip: str


class CampaignOut(BaseModel):
    id: str
    name: str
    template_id: Optional[str]
    parcel_keys: List[str]
    status: str
    sent_count: int
    error_count: int
    created_at: Optional[str]
    sent_at: Optional[str]
    lob_postcard_ids: List[str] = []


# ---------- helpers ----------

def _row_to_template(r: dict, dialect: str) -> TemplateOut:
    is_preset = bool(r.get("is_preset"))
    return TemplateOut(
        id=r["id"],
        name=r["name"],
        description=r.get("description"),
        front_html=r["front_html"],
        back_html=r["back_html"],
        size=r.get("size") or "4x6",
        qr_url=r.get("qr_url"),
        is_preset=is_preset,
        created_at=str(r["created_at"]) if r.get("created_at") else None,
        updated_at=str(r["updated_at"]) if r.get("updated_at") else None,
    )


# ---------- template endpoints ----------

@router.get("/templates")
async def list_templates() -> dict:
    _ensure_schema()
    with _conn() as (cur, dialect):
        cur.execute(
            "SELECT id, name, description, front_html, back_html, size, qr_url, is_preset, "
            "created_at, updated_at FROM mailer_templates ORDER BY is_preset DESC, created_at DESC"
        )
        rows = cur.fetchall()
        cols = [c.name if hasattr(c, "name") else c[0] for c in cur.description] if dialect == "pg" else None
        out = []
        for r in rows:
            d = dict(r) if dialect == "sqlite" else dict(zip(cols, r))
            out.append(_row_to_template(d, dialect).model_dump())
    return {"results": out}


@router.post("/templates")
async def create_template(t: TemplateIn) -> dict:
    _ensure_schema()
    tid = "tmpl_" + uuid.uuid4().hex[:10]
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as (cur, dialect):
        ph = _ph(dialect)
        cur.execute(
            f"INSERT INTO mailer_templates (id, name, description, front_html, back_html, size, qr_url, is_preset, created_at, updated_at) "
            f"VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})",
            (tid, t.name, t.description, t.front_html, t.back_html, t.size, t.qr_url, False, now, now),
        )
    return {"id": tid}


@router.put("/templates/{template_id}")
async def update_template(template_id: str, t: TemplateIn) -> dict:
    _ensure_schema()
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as (cur, dialect):
        ph = _ph(dialect)
        cur.execute(
            f"UPDATE mailer_templates SET name={ph}, description={ph}, front_html={ph}, back_html={ph}, "
            f"size={ph}, qr_url={ph}, updated_at={ph} WHERE id={ph} AND is_preset=" + ("FALSE" if dialect == "pg" else "0"),
            (t.name, t.description, t.front_html, t.back_html, t.size, t.qr_url, now, template_id),
        )
    return {"ok": True}


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str) -> dict:
    _ensure_schema()
    with _conn() as (cur, dialect):
        ph = _ph(dialect)
        cur.execute(
            f"DELETE FROM mailer_templates WHERE id={ph} AND is_preset=" + ("FALSE" if dialect == "pg" else "0"),
            (template_id,),
        )
    return {"ok": True}


# ---------- campaign endpoints ----------

@router.get("/campaigns")
async def list_campaigns() -> dict:
    _ensure_schema()
    with _conn() as (cur, dialect):
        cur.execute(
            "SELECT id, name, template_id, parcel_keys, status, sent_count, error_count, "
            "lob_postcard_ids, created_at, sent_at FROM mailer_campaigns ORDER BY created_at DESC LIMIT 100"
        )
        rows = cur.fetchall()
        cols = [c.name if hasattr(c, "name") else c[0] for c in cur.description] if dialect == "pg" else None
        out = []
        for r in rows:
            d = dict(r) if dialect == "sqlite" else dict(zip(cols, r))
            pk = d.get("parcel_keys") or []
            if isinstance(pk, str):
                pk = json.loads(pk)
            ids = d.get("lob_postcard_ids") or []
            if isinstance(ids, str):
                ids = json.loads(ids)
            out.append({
                "id": d["id"],
                "name": d["name"],
                "template_id": d.get("template_id"),
                "parcel_keys": pk,
                "status": d.get("status") or "draft",
                "sent_count": d.get("sent_count") or 0,
                "error_count": d.get("error_count") or 0,
                "lob_postcard_ids": ids,
                "created_at": str(d["created_at"]) if d.get("created_at") else None,
                "sent_at": str(d["sent_at"]) if d.get("sent_at") else None,
            })
    return {"results": out, "lob_mode": lob_client.mode}


@router.post("/campaigns")
async def send_campaign(
    c: CampaignIn,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None),
) -> dict:
    """Create + immediately send a postcard campaign through Lob.

    Each recipient must have a known mailing address. For the demo we
    use the property address itself as the mailing address (real flows
    use the owner mailing address from skip-trace).
    """
    _ensure_schema()

    if not c.parcel_keys:
        raise HTTPException(status_code=400, detail="No recipients selected")

    # Pre-charge token cost for the whole batch.
    user_id = identity.optional_user_id(authorization, x_user_id) or ""
    # 5 sends/min — way above interactive use; blocks scripted spam.
    limiter.check("mailer_send", user_id or "_anon", max=5, per_seconds=60)
    per_postcard = tokens_pricing.cost_tokens("mailer_postcard")
    total_cost = per_postcard * len(c.parcel_keys)
    debited_total = 0
    if user_id:
        ok, bal = tokens_db.debit(
            user_id,
            total_cost,
            action_key="mailer_postcard",
            note=f"Campaign {c.name} — {len(c.parcel_keys)} postcards",
        )
        if not ok:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "insufficient_tokens",
                    "required": total_cost,
                    "balance": bal,
                    "action": "mailer_postcard",
                    "per_unit": per_postcard,
                    "recipients": len(c.parcel_keys),
                },
            )
        debited_total = total_cost

    # Resolve template HTML (either from id or inline)
    front_html = c.front_html
    back_html = c.back_html
    if c.template_id:
        with _conn() as (cur, dialect):
            ph = _ph(dialect)
            cur.execute(
                f"SELECT front_html, back_html, size FROM mailer_templates WHERE id={ph}",
                (c.template_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Template not found")
            front_html = row["front_html"] if dialect == "sqlite" else row[0]
            back_html  = row["back_html"]  if dialect == "sqlite" else row[1]

    if not front_html or not back_html:
        raise HTTPException(400, "Postcard front + back HTML required")

    # Look up each parcel and dispatch through Lob
    sent_ids: List[str] = []
    sent = 0
    errors = 0
    for pk in c.parcel_keys:
        rec = get_one(pk)
        if not rec:
            errors += 1
            continue
        try:
            res = await lob_client.create_postcard(
                to={
                    "name": rec.get("address") or "Current Resident",
                    "address_line1": rec.get("address") or "",
                    "address_city": rec.get("city") or "",
                    "address_state": rec.get("state") or "",
                    "address_zip": rec.get("zip") or "",
                },
                from_address={
                    "name": c.from_name,
                    "address_line1": c.from_address_line1,
                    "address_city": c.from_address_city,
                    "address_state": c.from_address_state,
                    "address_zip": c.from_address_zip,
                },
                front_html=front_html.replace("{{property_address}}", rec.get("address") or "")
                                     .replace("{{property_city}}", rec.get("city") or ""),
                back_html=back_html.replace("{{property_address}}", rec.get("address") or "")
                                   .replace("{{property_city}}", rec.get("city") or "")
                                   .replace("{{from.name}}", c.from_name)
                                   .replace("{{to.name}}", "Property Owner"),
                description=c.name,
                size=c.size,
                metadata={"parcel_key": pk, "campaign": c.name},
            )
            sent_ids.append(res.get("id", ""))
            sent += 1
        except httpx.HTTPStatusError as e:
            log.exception("Lob postcard failed for %s: %s", pk, e)
            errors += 1

    # Persist the campaign log
    cid = "camp_" + uuid.uuid4().hex[:10]
    now = datetime.now(timezone.utc).isoformat()
    pk_json = json.dumps(c.parcel_keys)
    ids_json = json.dumps(sent_ids)
    status_str = "sent" if sent and not errors else ("partial" if sent else "failed")

    with _conn() as (cur, dialect):
        ph = _ph(dialect)
        cur.execute(
            f"""INSERT INTO mailer_campaigns (
                id, name, template_id, from_name, from_address_line1, from_address_city,
                from_address_state, from_address_zip, parcel_keys, status,
                lob_postcard_ids, sent_count, error_count, created_at, sent_at
            ) VALUES ({", ".join([ph]*15)})""",
            (
                cid, c.name, c.template_id, c.from_name, c.from_address_line1,
                c.from_address_city, c.from_address_state, c.from_address_zip,
                pk_json, status_str, ids_json, sent, errors, now, now,
            ),
        )

    # Refund tokens for postcards that failed to dispatch.
    refunded = 0
    if user_id and debited_total and errors:
        refund_amount = errors * per_postcard
        tokens_db.refund(
            user_id,
            refund_amount,
            action_key="mailer_postcard",
            note=f"Campaign {c.name} — refund {errors} failed postcards",
        )
        refunded = refund_amount

    return {
        "id": cid,
        "status": status_str,
        "sent_count": sent,
        "error_count": errors,
        "lob_postcard_ids": sent_ids,
        "lob_mode": lob_client.mode,
        "tokens": {
            "spent": debited_total - refunded,
            "refunded": refunded,
            "per_unit": per_postcard,
            "balance": tokens_db.balance(user_id) if user_id else None,
        },
    }
