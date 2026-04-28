"""
Off-market listing persistence.

Backed by Postgres in prod, SQLite for local dev. Driver picked from
the `OFFMARKET_DB_URL` env var:

  empty / unset             → local SQLite at apps/api/.data/off_market.sqlite
  sqlite:///path/to/file    → that SQLite file
  postgres[ql]://user:...   → Postgres via psycopg

Schema kept tiny on purpose — two tables:

  off_market_listings    One row per canonical parcel. Source tags
                         aggregated; most recent values win.
  off_market_sources     Append-only log of every raw scrape that
                         landed — lets us audit where a record came
                         from and when.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from scrapers.models import RawLead
from storage.address_matcher import parcel_key, normalize_address

# Load apps/api/.env on import so OFFMARKET_DB_URL is in os.environ
# regardless of where the entrypoint runs from.
_API_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_API_DIR / ".env")

log = logging.getLogger(__name__)


# ---------- driver selection ----------

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent.parent / ".data" / "off_market.sqlite"


def _resolve_url() -> str:
    """Return the connection URL. Empty → local SQLite default."""
    return (os.environ.get("OFFMARKET_DB_URL") or "").strip()


def _is_postgres(url: str) -> bool:
    return url.startswith("postgres://") or url.startswith("postgresql://")


# ---------- schema (dialect-specific) ----------

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS off_market_listings (
    parcel_key         TEXT PRIMARY KEY,
    parcel_apn         TEXT,
    address            TEXT,
    city               TEXT,
    county             TEXT,
    state              TEXT,
    zip                TEXT,
    source_tags        TEXT,
    default_amount     INTEGER,
    sale_date          TEXT,
    asking_price       INTEGER,
    lien_amount        INTEGER,
    years_delinquent   INTEGER,
    vacancy_months     INTEGER,
    owner_state        TEXT,
    estimated_value    INTEGER,
    assessed_value     INTEGER,
    loan_balance       INTEGER,
    estimated_equity   INTEGER,
    spread_pct         REAL,
    adu_ready          INTEGER DEFAULT 0,
    adu_score          INTEGER DEFAULT 0,
    first_seen         TEXT,
    last_seen          TEXT
);
CREATE INDEX IF NOT EXISTS idx_off_market_state     ON off_market_listings(state);
CREATE INDEX IF NOT EXISTS idx_off_market_county    ON off_market_listings(county);
CREATE INDEX IF NOT EXISTS idx_off_market_last_seen ON off_market_listings(last_seen);

CREATE TABLE IF NOT EXISTS off_market_sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    parcel_key      TEXT,
    source          TEXT,
    source_id       TEXT,
    source_url      TEXT,
    scraped_at      TEXT,
    payload         TEXT,
    UNIQUE(source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_sources_parcel ON off_market_sources(parcel_key);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS off_market_listings (
    parcel_key         TEXT PRIMARY KEY,
    parcel_apn         TEXT,
    address            TEXT,
    city               TEXT,
    county             TEXT,
    state              TEXT,
    zip                TEXT,
    source_tags        JSONB,
    default_amount     BIGINT,
    sale_date          TIMESTAMPTZ,
    asking_price       BIGINT,
    lien_amount        BIGINT,
    years_delinquent   INTEGER,
    vacancy_months     INTEGER,
    owner_state        TEXT,
    estimated_value    BIGINT,
    assessed_value     BIGINT,
    loan_balance       BIGINT,
    estimated_equity   BIGINT,
    spread_pct         DOUBLE PRECISION,
    adu_ready          BOOLEAN DEFAULT FALSE,
    adu_score          INTEGER DEFAULT 0,
    first_seen         TIMESTAMPTZ DEFAULT NOW(),
    last_seen          TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE off_market_listings ADD COLUMN IF NOT EXISTS assessed_value BIGINT;
ALTER TABLE off_market_listings ADD COLUMN IF NOT EXISTS loan_balance   BIGINT;
CREATE INDEX IF NOT EXISTS idx_off_market_state     ON off_market_listings(state);
CREATE INDEX IF NOT EXISTS idx_off_market_county    ON off_market_listings(county);
CREATE INDEX IF NOT EXISTS idx_off_market_last_seen ON off_market_listings(last_seen);

CREATE TABLE IF NOT EXISTS off_market_sources (
    id              BIGSERIAL PRIMARY KEY,
    parcel_key      TEXT,
    source          TEXT,
    source_id       TEXT,
    source_url      TEXT,
    scraped_at      TIMESTAMPTZ,
    payload         JSONB,
    UNIQUE(source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_sources_parcel ON off_market_sources(parcel_key);
"""


# ---------- connection helpers ----------

@contextmanager
def _conn():
    """Yield a (cursor, dialect) tuple; commit + close on exit."""
    url = _resolve_url()
    if _is_postgres(url):
        # psycopg auto-imported only when we need it — keeps dev install slim.
        import psycopg
        with psycopg.connect(url, autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.execute(POSTGRES_SCHEMA)
                yield cur, "pg"
                conn.commit()
    else:
        if url.startswith("sqlite:///"):
            path = Path(url[len("sqlite:///"):])
        else:
            path = DEFAULT_SQLITE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript(SQLITE_SCHEMA)
            _sqlite_migrate(conn)
            yield conn.cursor(), "sqlite"
            conn.commit()
        finally:
            conn.close()


def _sqlite_migrate(conn) -> None:
    """Add columns that may be missing on older DBs. SQLite has no
    ADD COLUMN IF NOT EXISTS, so check pragma first."""
    cur = conn.execute("PRAGMA table_info(off_market_listings)")
    existing = {row[1] for row in cur.fetchall()}
    for col, decl in [("assessed_value", "INTEGER"), ("loan_balance", "INTEGER")]:
        if col not in existing:
            conn.execute(f"ALTER TABLE off_market_listings ADD COLUMN {col} {decl}")


def _ph(dialect: str) -> str:
    """Return the placeholder syntax for the dialect (`?` for sqlite, `%s` for pg)."""
    return "%s" if dialect == "pg" else "?"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row, cursor, dialect: str) -> dict:
    """Normalize a row to a dict regardless of driver."""
    if dialect == "sqlite":
        return dict(row)
    cols = [c.name for c in cursor.description]
    return dict(zip(cols, row))


# ---------- public API ----------

def upsert(lead: RawLead) -> str | None:
    """Persist a RawLead. Returns the parcel_key it merged into, or None
    if the lead lacked any identity signal."""
    key = parcel_key(lead.raw_address, lead.parcel_apn)
    if not key:
        log.warning("Skipping lead with no address/APN: %s/%s", lead.source, lead.source_id)
        return None

    now = _now_iso()
    payload_json = json.dumps(lead.model_dump(mode="json"))
    sale_date_str = lead.sale_date.isoformat() if lead.sale_date else None

    with _conn() as (cur, dialect):
        ph = _ph(dialect)

        # 1. Append the raw source record (idempotent on UNIQUE(source, source_id))
        cur.execute(
            f"""
            INSERT INTO off_market_sources
                (parcel_key, source, source_id, source_url, scraped_at, payload)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            ON CONFLICT (source, source_id) DO NOTHING
            """,
            (key, lead.source, lead.source_id, lead.source_url, lead.scraped_at.isoformat(), payload_json),
        )

        # 2. Read existing tags so we can union the new one in
        cur.execute(
            f"SELECT source_tags FROM off_market_listings WHERE parcel_key = {ph}",
            (key,),
        )
        row = cur.fetchone()
        tags: set[str] = set()
        if row:
            existing = row[0] if dialect == "pg" else row["source_tags"]
            if existing:
                tags = set(existing if isinstance(existing, list) else json.loads(existing))
        tags.add(lead.source)
        tags_serialized = sorted(tags)
        if dialect == "sqlite":
            tags_serialized = json.dumps(tags_serialized)
        else:
            tags_serialized = json.dumps(tags_serialized)  # psycopg auto-casts to JSONB

        # 3. Upsert the canonical row, merging non-null fields forward
        cur.execute(
            f"""
            INSERT INTO off_market_listings (
                parcel_key, parcel_apn, address, city, county, state, zip,
                source_tags,
                default_amount, sale_date, asking_price, lien_amount,
                years_delinquent, vacancy_months, owner_state,
                estimated_value, assessed_value, loan_balance,
                first_seen, last_seen
            )
            VALUES ({", ".join([ph] * 20)})
            ON CONFLICT (parcel_key) DO UPDATE SET
                parcel_apn       = COALESCE(EXCLUDED.parcel_apn, off_market_listings.parcel_apn),
                address          = COALESCE(EXCLUDED.address, off_market_listings.address),
                city             = COALESCE(EXCLUDED.city, off_market_listings.city),
                county           = COALESCE(EXCLUDED.county, off_market_listings.county),
                state            = COALESCE(EXCLUDED.state, off_market_listings.state),
                zip              = COALESCE(EXCLUDED.zip, off_market_listings.zip),
                source_tags      = EXCLUDED.source_tags,
                default_amount   = COALESCE(EXCLUDED.default_amount, off_market_listings.default_amount),
                sale_date        = COALESCE(EXCLUDED.sale_date, off_market_listings.sale_date),
                asking_price     = COALESCE(EXCLUDED.asking_price, off_market_listings.asking_price),
                lien_amount      = COALESCE(EXCLUDED.lien_amount, off_market_listings.lien_amount),
                years_delinquent = COALESCE(EXCLUDED.years_delinquent, off_market_listings.years_delinquent),
                vacancy_months   = COALESCE(EXCLUDED.vacancy_months, off_market_listings.vacancy_months),
                owner_state      = COALESCE(EXCLUDED.owner_state, off_market_listings.owner_state),
                estimated_value  = COALESCE(EXCLUDED.estimated_value, off_market_listings.estimated_value),
                assessed_value   = COALESCE(EXCLUDED.assessed_value, off_market_listings.assessed_value),
                loan_balance     = COALESCE(EXCLUDED.loan_balance, off_market_listings.loan_balance),
                last_seen        = EXCLUDED.last_seen
            """,
            (
                key, lead.parcel_apn, normalize_address(lead.raw_address),
                lead.city, lead.county, lead.state, lead.zip,
                tags_serialized,
                lead.default_amount,
                sale_date_str,
                lead.asking_price, lead.lien_amount,
                lead.years_delinquent, lead.vacancy_duration_months, lead.owner_state,
                lead.estimated_value, lead.assessed_value, lead.loan_balance,
                now, now,
            ),
        )

    return key


def query(
    state: str | None = None,
    county: str | None = None,
    source: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Cheap fetch for the API — returns the canonical records, newest first."""
    with _conn() as (cur, dialect):
        ph = _ph(dialect)
        clauses: list[str] = []
        params: list = []

        if state:
            clauses.append(f"state = {ph}")
            params.append(state)
        if county:
            clauses.append(f"county = {ph}")
            params.append(county)
        if source:
            if dialect == "pg":
                clauses.append(f"source_tags @> {ph}::jsonb")
                params.append(json.dumps([source]))
            else:
                clauses.append(f"source_tags LIKE {ph}")
                params.append(f'%"{source}"%')

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM off_market_listings {where} ORDER BY last_seen DESC LIMIT {ph}"
        params.append(limit)

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        out = [_row_to_dict(r, cur, dialect) for r in rows]

    # Normalize JSON columns + datetimes
    for r in out:
        tags = r.get("source_tags")
        if isinstance(tags, str):
            r["source_tags"] = json.loads(tags)
        for k in ("first_seen", "last_seen", "sale_date"):
            v = r.get(k)
            if isinstance(v, datetime):
                r[k] = v.isoformat()
    return out


def source_counts(state: str | None = None, county: str | None = None) -> dict:
    """Return {'all': total, '<source>': n, ...} via a single grouped SQL
    query — much cheaper than fetching 10k rows and counting in Python."""
    with _conn() as (cur, dialect):
        ph = _ph(dialect)
        clauses = []
        params: list = []
        if state:
            clauses.append(f"state = {ph}")
            params.append(state)
        if county:
            clauses.append(f"county = {ph}")
            params.append(county)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        cur.execute(f"SELECT count(*) FROM off_market_listings {where}", tuple(params))
        total = cur.fetchone()[0]

        if dialect == "pg":
            sql = f"""
                SELECT tag, count(*)
                FROM off_market_listings, jsonb_array_elements_text(source_tags) AS tag
                {where}
                GROUP BY tag
            """
        else:
            # SQLite: source_tags is JSON text; use json_each
            sql = f"""
                SELECT je.value AS tag, count(*)
                FROM off_market_listings, json_each(off_market_listings.source_tags) AS je
                {where}
                GROUP BY je.value
            """
        cur.execute(sql, tuple(params))
        counts: dict = {"all": total}
        for tag, n in cur.fetchall():
            counts[tag] = n
    return counts


def get_one(parcel_key_value: str) -> dict | None:
    """Fetch a canonical record + its raw source log."""
    with _conn() as (cur, dialect):
        ph = _ph(dialect)
        cur.execute(
            f"SELECT * FROM off_market_listings WHERE parcel_key = {ph}",
            (parcel_key_value,),
        )
        row = cur.fetchone()
        if not row:
            return None
        record = _row_to_dict(row, cur, dialect)

        cur.execute(
            f"""SELECT source, source_id, source_url, scraped_at, payload
                FROM off_market_sources
                WHERE parcel_key = {ph}
                ORDER BY scraped_at DESC""",
            (parcel_key_value,),
        )
        source_rows = cur.fetchall()
        sources = []
        for s in source_rows:
            sd = _row_to_dict(s, cur, dialect)
            payload = sd.get("payload")
            if isinstance(payload, str):
                sd["payload"] = json.loads(payload)
            scraped = sd.get("scraped_at")
            if isinstance(scraped, datetime):
                sd["scraped_at"] = scraped.isoformat()
            sources.append(sd)
        record["sources"] = sources

    # Normalize JSON + datetime columns on the record
    tags = record.get("source_tags")
    if isinstance(tags, str):
        record["source_tags"] = json.loads(tags)
    for k in ("first_seen", "last_seen", "sale_date"):
        v = record.get(k)
        if isinstance(v, datetime):
            record[k] = v.isoformat()
    return record
