# Off-Market Scraping Plan

How we build and maintain the nine off-market feeds powering the
`/off-market` page and the "Off-market leads" daily alerts.

## Principles (read first)

1. **Public records only, by default.** County recorder, treasurer,
   assessor, and court data are legal to aggregate. Private-site
   scraping is reserved for sources whose ToS explicitly allow it
   (e.g., Craigslist RSS) or where we use an official partner API
   (Zillow Research, RealtyTrac, HUDHomestore).
2. **Taste over completeness.** Owners of pre-foreclosure,
   probate, and absentee properties didn't opt in to being marketed.
   The UI frames each record as *"public filing — verified by us"*,
   not as a lead list. Every outbound touch goes through a vetted
   direct-mail flow, never unsolicited email.
3. **Identity first, source second.** Every scraped record gets
   matched to a canonical parcel (APN + normalized address) before
   it's stored. A property in pre-foreclosure AND vacant AND probate
   is one record with three flags, not three records.
4. **Rate limit yourself.** 1 request/second per source, max. Cache
   landing pages. Use polite `User-Agent` that includes a contact URL.

## Nine sources — status and approach

| Source | Method | Legal posture | Target cadence |
|---|---|---|---|
| **Pre-Foreclosure (NOD/NTS)** | **County recorders: Pierce (active), King (active), Thurston (active)** + ATTOM Data API | Public record + licensed feed | Daily |
| **Trustee Sales / Auction** | **Quality Loan Service (active) + NWTS (active) + Clear Recon (active)** + ATTOM Data API (incl. Auction.com feed) | Public record + licensed feed | Daily |
| **For Sale By Owner** | **Craigslist RSS (active)** + ForSaleByOwner.com partner feed | RSS is Craigslist's documented reuse surface; FSBO.com has opt-in publication | 2×/day |
| **Tax Liens & Delinquent** | **Pierce (active), King (active), Thurston (active)** Treasurer tax-foreclosure PDFs | Public record | Daily check, annual refresh |
| **Probate & Inherited** | **Pierce (active), King (active), Thurston (active)** Superior Court case searches | Public record | Daily |
| **Vacant / Absentee Owner** | **ATTOM `basicprofile`** (active today) + County Assessor parcel data | Licensed + public record | Daily (ATTOM); Weekly (county) |
| **Bank-Owned (REO)** | HUDHomestore.com + HomePath + HomeSteps **+ ATTOM Data API** | Official public feeds + licensed feed | Daily |
| **Our Off-Market Network** | Internal Airtable / direct entry (+ Investorlift email auto-forward) | Opt-in | Real-time (manual) |

### Commercial: ATTOM Data Solutions

ATTOM covers **pre-foreclosure, auction (including Auction.com's feed),
and REO** through two endpoints:

- `foreclosure/snapshot` — paginated list for a county FIPS. Called once
  per county per day.
- `property/expandedprofile` — per-record enrichment. Called on demand
  only for records we actually surface.

**Daily cost model:**
- ~30 snapshot calls/county × 3 counties = 90 calls/day
- ~200 detail enrichment calls/day on new records
- **~290 calls/day = ~9K/month** — comfortably inside the ATTOM entry tier

**Stacking strategy:** County scrapers run *first* in the nightly pipeline
(free, local source-of-truth), then ATTOM runs *second* and layers its tags
onto parcels the county scrapers already touched. When ATTOM and the Pierce
recorder both flag the same parcel as pre-foreclosure, they merge into a
single `off_market_listings` row with both source IDs in
`off_market_sources` — never duplicated.

Each source lives in its own file under [`scrapers/`](./scrapers/).
All scrapers inherit from `BaseScraper` and emit `RawLead` records
that a single normalizer in `scrapers/pipeline.py` turns into
canonical listings.

## Data flow

```
scrapers/<source>.py           ──┐
                                  ├─→  RawLead  ──→  address_matcher.py  ──┐
other scrapers                   ──┘   (Pydantic)     (→ APN + normalized)  ↓
                                                                            ↓
                                                            off_market_db.py (Postgres)
                                                                            ↓
                                                            routes/off_market.py (GET)
                                                                            ↓
                                                            React frontend /off-market
```

## Running

Nightly cron (see `jobs/nightly.py`) runs every scraper in sequence
with per-source caching and rate-limits. Manually trigger one:

```bash
python -m scrapers.pierce_nod
python -m scrapers.pipeline --source=all
```

## County-specific notes

### King County
- Recorder: https://recording.kingcounty.gov — session-cookie required, no bulk API. Search by document type (NOTS, NOD).
- Assessor: https://info.kingcounty.gov/Assessor/eRealProperty — parcel bulk data available via SharePoint FOIA request (quarterly dumps).
- Treasurer: https://kingcounty.gov/depts/finance/treasury — tax delinquency list published annually (Q2).

### Pierce County
- Auditor/Recorder: https://co.pierce.wa.us/1173/Recording-Department — has a web search + CSV export.
- Assessor: https://epip.co.pierce.wa.us — parcel data via bulk FTP (annual + monthly deltas).
- Treasurer: https://piercecountywa.gov/treasurer — monthly delinquency reports.

### Thurston County
- Auditor: https://www.thurstoncountywa.gov/departments/auditor — recording search, no API.
- Assessor: https://tcproperty.thurstoncountywa.gov — parcel search + downloadable spreadsheets.

## Deduplication strategy

Keyed on `parcel_apn` if known, else a hash of the
`normalize_address()` output. When two sources flag the same APN,
merge tags (`adu-ready`, `pre-foreclosure`, `vacant`) onto one record
and keep the earliest filing date per tag.

## Legal checklist

- [x] No CFAA concerns — only public records + opt-in feeds.
- [x] `robots.txt` respected (our scraper exits if a source disallows).
- [x] User-Agent identifies us + links to contact URL.
- [x] Data retention: delete records whose source document was sealed
      or corrected (probate, especially) within 72h of notice.
- [x] Fair Housing: no scraping or filtering on race, family status,
      ethnicity, religion, or any protected class — ever.

---

## Paid commercial sources — comparison + setup (2026)

After the WA-only county scrapers proved fragile (silent breakage on
selector drift, ~zero leads in production), we layered commercial
APIs that cover all 50 states from one endpoint.

### Recommended stack (by ROI)

| Provider | Cost | Coverage | Best for | Status |
|---|---|---|---|---|
| **PropertyRadar** | $199-$499/mo | 150M+ properties, all 50 states | One-stop nationwide distress (NOD/NTS, auction, tax, probate, vacant, absentee, equity) | **Integrated** — set `PROPERTYRADAR_API_KEY` |
| **BatchData** | Pay-as-you-go (~$0.07/skip-trace + property API) | Nationwide | Combines property + skip-trace in one row | **Integrated** — same `BATCHDATA_API_KEY` we use for skip-trace |
| **ATTOM Foreclosure bundle** | ~$300/mo | Nationwide | Foreclosure-specific cross-validation | **Integrated** — `ATTOM_API_KEY` (free 30-day trial) |
| **REI Data Vault** | ~$50-100/mo | Nationwide | Cheap bulk lists (no real-time) | Not integrated — drop-in pattern available |
| **PropStream API** | $99 + extras | Nationwide | Alt to PropertyRadar | Not integrated |
| **CoreLogic** | $1k+/mo | Best in class | Enterprise | Not integrated |
| **DataTree (First American)** | ~$500/mo | Title-derived | Recorded transactions | Not integrated |

### What each integrated client does

- `services/propertyradar_client.py` — wraps `/v1/properties` with the
  pre-built criteria blocks for each signal. Mock-safe when the key
  is unset (returns []).
- `services/batchdata_client.py` — wraps `/api/v1/property/search`
  with the same set of distress filters. Same key powers skip-trace
  in `services/skip_trace_providers.py`.
- `scrapers/propertyradar.py` — 7 scrapers, one per signal:
  `pr-preforeclosure`, `pr-auction`, `pr-tax-lien`, `pr-probate`,
  `pr-vacant`, `pr-absentee`, `pr-high-equity`.
- `scrapers/batchdata.py` — 6 scrapers mirroring the PropertyRadar
  set: `bd-preforeclosure`, `bd-auction`, `bd-tax-lien`, `bd-vacant`,
  `bd-absentee`, `bd-high-equity`.

Both clients paginate state-by-state to avoid payload caps and respect
provider-side rate limiting (429 → log + skip).

### Activation (Fly secrets)

```bash
# PropertyRadar — best ROI for nationwide
fly secrets set PROPERTYRADAR_API_KEY=pr_... -a onlyoffmarkets-api

# BatchData — already set if skip-trace is enabled
fly secrets set BATCHDATA_API_KEY=batch_... -a onlyoffmarkets-api

# ATTOM — already set; foreclosure bundle just enables more endpoints
fly secrets set ATTOM_API_KEY=... -a onlyoffmarkets-api
```

### Observability

Every scraper run is logged to `scraper_runs` (sqlite/pg). Visible at
`GET /admin/scrapers?token=...&days=14`:

- `state: "green"` — recent run + at least one row persisted
- `state: "yellow"` — recent run + zero persisted (parser drift?)
- `state: "red"` — no run in 48h
- `state: "never"` — registered but never executed

### When to add a new commercial source

Drop `services/<provider>_client.py` + `scrapers/<provider>.py`,
register the scrapers in `pipeline.py`. The base class
(`scrapers/base.py`) handles rate-limiting, robots.txt, caching,
retries, and User-Agent.

### Rule of thumb

If a source's monthly cost exceeds the marginal revenue from the
leads it provides, drop it. Run `/admin/scrapers` weekly. Anything
red or yellow for 7 days = unsubscribe or fix.

---

## 2026-05 update — PropertyRadar deactivated for SaaS resale

PropertyRadar's API ToS state:

> The PropertyRadar API is intended for end-users only — you can not
> use it to build applications you sell to others. […] We also offer
> OAuth, so partner applications can access the API on behalf of our
> shared customers.

Since OnlyOffMarkets is a SaaS sold to others, hitting one PropertyRadar
account on behalf of every customer is a clear ToS violation. Effective
2026-05-04 the production stack is:

  Underwrite lookup ladder:  DB → **BatchData** → ATTOM → geocode
  Pipeline:                  PR scrapers commented out, BD scrapers active

The `services/propertyradar_client.py` and `scrapers/propertyradar.py`
files remain in the repo. To re-enable:

  1. Apply to PropertyRadar's partner program (OAuth flow).
  2. Switch backend from one shared key to per-user OAuth tokens.
  3. Uncomment the `pr-*` entries in `pipeline.py SCRAPERS`.

BatchData was chosen as the primary because:
  * Their published license tiers include explicit SaaS / Platform
    rights for app builders.
  * Same `BATCHDATA_API_KEY` already powers our skip-trace flow —
    marginal cost is zero to flip property search on.
  * Coverage is ~80% of PropertyRadar for distress signals; data
    depth is shallower but more than adequate for our gauge math.

ATTOM stays in the chain as a foreclosure-bundle cross-validation
layer. Their developer terms permit embedded analytics use.
