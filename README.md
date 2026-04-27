# OnlyOffMarkets

Every off-market real-estate lead in one feed. Public-record signals
(preforeclosures, tax delinquencies, probate, FSBO, REO, auctions,
code violations) from county recorders, treasurers, and licensed APIs.

## Layout

```
apps/
  web/          Vite + React + Tailwind frontend
  api/          FastAPI backend + 17 scrapers + nightly pipeline
```

## Quick start

### Frontend
```bash
cd apps/web
npm install
npm run dev          # http://localhost:5174
```

### API
```bash
cd apps/api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python seed_demo.py        # seed local SQLite with 9 demo signals
.venv/bin/uvicorn app:app --reload --port 8001
```

## Configuration

Create `apps/api/.env` from the variables in `apps/api/config.py`. Key
settings:

| Var | Purpose |
|-----|---------|
| `OFFMARKET_DB_URL` | Postgres URL. Empty → falls back to local SQLite. |
| `ATTOM_API_KEY` | ATTOM Data Solutions (preforeclosure / REO / absentee). |
| `INVESTORLIFT_API_KEY` | InvestorLift wholesaler marketplace. |
| `REDIS_URL` | Optional response cache. Falls back to in-process. |

## Scrapers

See [apps/api/SCRAPING.md](apps/api/SCRAPING.md) for the full ops doc —
sources, legal posture, dedup strategy, ATTOM stacking.

Run one scraper:
```bash
cd apps/api
.venv/bin/python -m scrapers.pierce_nod
```

Run the full pipeline:
```bash
.venv/bin/python -m scrapers.pipeline --source=all
```

## Brand

Signals, not listings. We never claim a property is for sale unless
its source confirms it.
