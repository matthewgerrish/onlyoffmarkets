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
