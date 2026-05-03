"""Per-scraper run telemetry.

Pipeline writes a row each time a scraper executes. Surface in
/admin/scrapers so we can see at a glance which sources are
delivering vs which have silently broken on a selector change.

  scraper_runs
    id           bigserial / autoincrement
    slug         scraper key in pipeline.SCRAPERS
    source       canonical source tag (preforeclosure, vacant, etc.)
    started_at   timestamptz
    finished_at  timestamptz
    scraped      int   — RawLeads yielded
    persisted    int   — rows actually upserted into off_market_listings
    errors       int
    elapsed_s    real
    status       text  — ok | error | empty
    note         text  — last log message if errored
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from storage.off_market_db import _conn, _ph

log = logging.getLogger(__name__)


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS scraper_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    slug         TEXT NOT NULL,
    source       TEXT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    scraped      INTEGER NOT NULL DEFAULT 0,
    persisted    INTEGER NOT NULL DEFAULT 0,
    errors       INTEGER NOT NULL DEFAULT 0,
    elapsed_s    REAL,
    status       TEXT NOT NULL DEFAULT 'ok',
    note         TEXT
);
CREATE INDEX IF NOT EXISTS scraper_runs_slug_idx
    ON scraper_runs(slug, started_at DESC);
"""

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS scraper_runs (
    id           BIGSERIAL PRIMARY KEY,
    slug         TEXT NOT NULL,
    source       TEXT,
    started_at   TIMESTAMPTZ NOT NULL,
    finished_at  TIMESTAMPTZ,
    scraped      INTEGER NOT NULL DEFAULT 0,
    persisted    INTEGER NOT NULL DEFAULT 0,
    errors       INTEGER NOT NULL DEFAULT 0,
    elapsed_s    DOUBLE PRECISION,
    status       TEXT NOT NULL DEFAULT 'ok',
    note         TEXT
);
CREATE INDEX IF NOT EXISTS scraper_runs_slug_idx
    ON scraper_runs(slug, started_at DESC);
"""


def _ensure(cur, dialect: str) -> None:
    if dialect == "pg":
        cur.execute(_PG_SCHEMA)
    else:
        cur.executescript(_SQLITE_SCHEMA)


def record_run(
    slug: str,
    *,
    source: str | None,
    started_at: datetime,
    finished_at: datetime | None,
    scraped: int,
    persisted: int,
    errors: int,
    elapsed_s: float,
    status: str,
    note: str | None = None,
) -> None:
    try:
        with _conn() as (cur, dialect):
            _ensure(cur, dialect)
            ph = _ph(dialect)
            cur.execute(
                f"""
                INSERT INTO scraper_runs (slug, source, started_at, finished_at,
                  scraped, persisted, errors, elapsed_s, status, note)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
                """,
                (
                    slug, source,
                    started_at.isoformat(),
                    finished_at.isoformat() if finished_at else None,
                    int(scraped), int(persisted), int(errors),
                    float(elapsed_s),
                    status, (note or "")[:1000],
                ),
            )
    except Exception as exc:  # pragma: no cover
        log.warning("scraper_runs.record failed: %s", exc)


def health(days: int = 14) -> list[dict]:
    """Per-scraper health summary over the last N days.

    Returns a row per slug with last run, total runs, totals, and a
    derived `state` (`green` recent + producing, `yellow` recent +
    empty, `red` no run in 48h).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows: list[dict] = []
    try:
        with _conn() as (cur, dialect):
            _ensure(cur, dialect)
            ph = _ph(dialect)
            cur.execute(
                f"""
                SELECT slug,
                       MAX(started_at)         AS last_run,
                       COUNT(*)                AS runs,
                       COALESCE(SUM(scraped), 0)   AS total_scraped,
                       COALESCE(SUM(persisted), 0) AS total_persisted,
                       COALESCE(SUM(errors), 0)    AS total_errors,
                       MAX(source)             AS last_source
                FROM scraper_runs
                WHERE started_at >= {ph}
                GROUP BY slug
                ORDER BY last_run DESC
                """,
                (cutoff,),
            )
            now = datetime.now(timezone.utc)
            for r in cur.fetchall() or []:
                d = dict(r) if isinstance(r, dict) else {
                    "slug": r[0], "last_run": r[1], "runs": r[2],
                    "total_scraped": r[3], "total_persisted": r[4],
                    "total_errors": r[5], "last_source": r[6],
                }
                last = d.get("last_run")
                last_dt = None
                if last:
                    try:
                        last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
                    except Exception:
                        last_dt = None
                hours_since = None
                if last_dt:
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    hours_since = (now - last_dt).total_seconds() / 3600.0

                state = "green"
                if hours_since is None or hours_since > 48:
                    state = "red"
                elif int(d["total_persisted"]) == 0:
                    state = "yellow"

                d["hours_since_run"] = round(hours_since, 1) if hours_since is not None else None
                d["state"] = state
                d["runs"] = int(d["runs"])
                d["total_scraped"] = int(d["total_scraped"])
                d["total_persisted"] = int(d["total_persisted"])
                d["total_errors"] = int(d["total_errors"])
                d["last_run"] = str(d["last_run"]) if d["last_run"] else None
                rows.append(d)
    except Exception as exc:
        log.warning("scraper_runs.health failed: %s", exc)
    return rows


def recent(slug: str, limit: int = 30) -> list[dict]:
    """Per-scraper run history, newest first."""
    out: list[dict] = []
    try:
        with _conn() as (cur, dialect):
            _ensure(cur, dialect)
            ph = _ph(dialect)
            cur.execute(
                f"""
                SELECT id, slug, source, started_at, finished_at,
                       scraped, persisted, errors, elapsed_s, status, note
                FROM scraper_runs
                WHERE slug = {ph}
                ORDER BY started_at DESC
                LIMIT {ph}
                """,
                (slug, int(limit)),
            )
            for r in cur.fetchall() or []:
                d = dict(r) if isinstance(r, dict) else {
                    "id": r[0], "slug": r[1], "source": r[2],
                    "started_at": r[3], "finished_at": r[4],
                    "scraped": r[5], "persisted": r[6], "errors": r[7],
                    "elapsed_s": r[8], "status": r[9], "note": r[10],
                }
                d["started_at"] = str(d["started_at"]) if d.get("started_at") else None
                d["finished_at"] = str(d["finished_at"]) if d.get("finished_at") else None
                out.append(d)
    except Exception as exc:
        log.warning("scraper_runs.recent failed: %s", exc)
    return out
