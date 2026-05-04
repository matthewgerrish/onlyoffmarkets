import { useEffect } from 'react';
import {
  X, MapPin, Database, FileSearch, Calculator, Building2, Gauge,
  Server, Zap, ShieldCheck, ArrowDown, ExternalLink,
} from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
}

/** Right-side drawer that walks the user through the entire Underwrite
 *  pipeline — what happens to an address from the moment it leaves
 *  the input to the moment the gauges render. */
export default function MethodologyDrawer({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    // Lock body scroll while open
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  return (
    <div
      className={`fixed inset-0 z-[60] flex transition-opacity ${
        open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
      }`}
      aria-hidden={!open}
    >
      {/* Backdrop */}
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="flex-1 bg-slate-900/40 backdrop-blur-sm"
      />
      {/* Sheet */}
      <div
        className={`w-full max-w-xl bg-white border-l border-slate-200 shadow-2xl h-full overflow-y-auto transition-transform duration-300 ease-out ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Sticky header */}
        <div className="sticky top-0 z-10 bg-white/90 backdrop-blur border-b border-slate-100 px-6 py-4 flex items-center justify-between">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-brand-500">
              Methodology
            </div>
            <h2 className="font-display font-extrabold text-xl text-brand-navy mt-0.5">
              How Underwrite works
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-full hover:bg-slate-100"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-7">
          {/* Intro */}
          <div className="card p-5 bg-gradient-to-br from-brand-50 via-white to-amber-50 border-brand-100">
            <p className="text-sm text-slate-700 leading-relaxed">
              You drop an address. We resolve it, look it up across our
              public-record DB and any paid sources you have connected, run a
              <strong className="text-brand-navy"> 14-factor deal score </strong>
              and a <strong className="text-brand-navy">state-aware ADU score</strong>
              , then return everything as one snapshot.
            </p>
          </div>

          {/* Pipeline steps */}
          <section>
            <SectionTitle icon={Server}>The pipeline</SectionTitle>
            <ol className="mt-3 space-y-3">
              <PipeStep
                n={1}
                icon={MapPin}
                accent="#1d6cf2"
                title="Geocoding"
                desc="Mapbox normalizes the input — '1234 1st Ave Seattle' becomes structured city / state / zip with lat-lng. If Mapbox is off, we fall back to a regex parser that pulls out the state code so ADU scoring still works."
              />
              <PipeStep
                n={2}
                icon={FileSearch}
                accent="#1d6cf2"
                title="Parcel lookup ladder"
                desc="We try our own DB first (every parcel any scraper has touched). Miss → PropertyRadar by SiteAddress. Miss → ATTOM /property/basicprofile. Whichever hits first owns the snapshot."
                pills={['DB', 'PropertyRadar', 'ATTOM', 'Geocode-only']}
              />
              <PipeStep
                n={3}
                icon={Database}
                accent="#1d6cf2"
                title="Signal extraction"
                desc="Distress tags (foreclosure stage, tax-delinquent years, vacancy months, owner-occupancy), valuation (AVM, assessed, loan balance), tenure (years owned, last sale date + price), and any HOA / multi-mortgage flags get pulled from the response and normalized."
              />
              <PipeStep
                n={4}
                icon={Calculator}
                accent="#f97316"
                title="Deal scoring (14 factors)"
                desc="Server-side formula in services/deal_scoring.py. Each factor adds points; result caps at 100. Underwater LTV penalizes (-points). Confidence = factors-fired ÷ 14, surfaced so you can tell a thin score from a strong one."
              />
              <PipeStep
                n={5}
                icon={Building2}
                accent="#10b981"
                title="ADU scoring (WA + CA only)"
                desc="services/adu_scoring.py applies the live statutes — WA HB 1337 (2 ADUs by-right in cities >25k) and CA AB 68 / AB 1033 / SB 9 (main + ADU + JADU + lot-split for 4 units). Lot size, building footprint, year built, and SB-9 eligibility all stack."
              />
              <PipeStep
                n={6}
                icon={Gauge}
                accent="#f43f5e"
                title="Render"
                desc="Both gauges animate in. Foreclosure timeline appears if there's an active stage. Ownership card appears when paid-source fields are present. Recommendation copy is server-generated based on score tier."
              />
            </ol>
          </section>

          {/* Data sources */}
          <section>
            <SectionTitle icon={Database}>Data sources we draw from</SectionTitle>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <SourceCard
                name="OnlyOffMarkets DB"
                tier="free · always on"
                desc="Every parcel any of our scrapers (NYC violations, Chicago / SF / Philly, WA county courts, ATTOM nightly, etc.) has touched."
                color="#1d6cf2"
              />
              <SourceCard
                name="PropertyRadar"
                tier="$199-499 / mo · best ROI"
                desc="Single API for all 7 distress signals across 50 states. NOD / NTS / Auction stage, tax-default years, equity %, owner tenure, probate flag."
                color="#10b981"
              />
              <SourceCard
                name="ATTOM Data"
                tier="from ~$300 / mo · foreclosure-rich"
                desc="Deep historical records, AVMs, full assessor + sales history. Currently running on a free trial."
                color="#f59e0b"
              />
              <SourceCard
                name="BatchData"
                tier="pay-as-you-go · skip-trace stack"
                desc="Already paying for skip-trace; same key powers the property API for distress filters and bulk-friendly mailer prep."
                color="#8b5cf6"
              />
            </div>
          </section>

          {/* Score factors */}
          <section>
            <SectionTitle icon={Zap}>Deal score factors</SectionTitle>
            <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
              Click the (i) icon on the gauge to see the actual breakdown for any
              parcel. The 14 possible factors:
            </p>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {DEAL_FACTORS.map((f) => (
                <div
                  key={f.label}
                  className="flex items-start gap-2.5 p-2.5 rounded-lg border border-slate-100 bg-slate-50/50"
                >
                  <span
                    className="mt-0.5 inline-flex items-center justify-center w-6 h-6 rounded-full bg-white border border-slate-200 text-[10px] font-mono font-bold text-slate-600 shrink-0"
                  >
                    +{f.max}
                  </span>
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-800 truncate">{f.label}</div>
                    <div className="text-[10px] text-slate-500">{f.note}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* ADU rules */}
          <section>
            <SectionTitle icon={Building2}>ADU rules in plain English</SectionTitle>
            <div className="mt-3 space-y-3">
              <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-3.5">
                <div className="flex items-baseline justify-between mb-1">
                  <span className="font-display font-extrabold text-brand-navy">Washington</span>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                    HB 1337
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  All cities &gt;25k must allow <strong>2 ADUs per single-family lot</strong>.
                  Detached up to 1,000 sqft, by-right. Owner-occupancy mandate
                  eliminated. Reduced parking near transit.
                </p>
              </div>
              <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-3.5">
                <div className="flex items-baseline justify-between mb-1">
                  <span className="font-display font-extrabold text-brand-navy">California</span>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                    AB 68 + SB 9
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Every SFR lot: <strong>main + 1 ADU + 1 JADU</strong> by-right.
                  Lots ≥ 2,400 sqft can split (SB 9) into two separate parcels each
                  carrying a duplex → up to <strong>4 dwelling units total</strong>.
                  Setbacks reduced to 4 ft.
                </p>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-3.5">
                <p className="text-xs text-slate-500 leading-relaxed">
                  <strong className="text-slate-700">Other states:</strong> we
                  return ADU score 0 / band "none" with a clear note. Local
                  ordinances vary too much to score confidently without a
                  per-jurisdiction zoning layer (which we'd license separately).
                </p>
              </div>
            </div>
          </section>

          {/* Confidence */}
          <section>
            <SectionTitle icon={ShieldCheck}>Confidence — what the % means</SectionTitle>
            <div className="mt-3 space-y-2.5 text-sm text-slate-700">
              <ConfRow color="#10b981" label="Strong (≥70%)">
                Most factors fired. PropertyRadar or BatchData populated the
                heavy fields (equity, tenure, foreclosure stage). Trust the score.
              </ConfRow>
              <ConfRow color="#f59e0b" label="OK (40-69%)">
                Some factors fired. Usually means our DB has the parcel but not
                a paid source. Score is directionally right; specific points may
                shift once you connect a paid feed.
              </ConfRow>
              <ConfRow color="#94a3b8" label="Thin (&lt;40%)">
                Geocode-only or near-empty parcel record. Score is a baseline;
                don't act on it without verifying via a paid source.
              </ConfRow>
            </div>
          </section>

          {/* Privacy / posture */}
          <section className="card p-4 border-amber-100 bg-amber-50/40">
            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-amber-700 mb-1.5">
              Disclosure
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              We score public-record signals only. No tenant screening, no FCRA
              decisions, no broker MLS data. Each gauge is a tool to surface
              opportunity — not a substitute for due diligence, financing
              underwriting, or a licensed agent.
            </p>
          </section>

          {/* Footer pointer */}
          <div className="pt-2 pb-1 text-[11px] text-slate-400 inline-flex items-center gap-1.5">
            <ExternalLink className="w-3 h-3" />
            Source files in this repo:
            <code className="bg-slate-100 px-1.5 py-0.5 rounded font-mono">
              services/deal_scoring.py
            </code>
            <code className="bg-slate-100 px-1.5 py-0.5 rounded font-mono">
              services/adu_scoring.py
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------------- bits ---------------- */

const DEAL_FACTORS = [
  { max: 30, label: 'Foreclosure stage',     note: 'NOD / NTS / Auction with day-window weighting' },
  { max: 25, label: 'Source-tag base',       note: 'highest-weight active distress source' },
  { max: 22, label: 'Equity (free & clear)', note: 'EquityPercent or derived LTV' },
  { max: 18, label: 'Stack bonus',           note: 'multiple distress sources on one parcel' },
  { max: 18, label: 'Asking discount',       note: 'asking-price below est. value' },
  { max: 16, label: 'Tax delinquency',       note: 'years behind on county taxes' },
  { max: 16, label: 'Vacancy duration',      note: 'months unoccupied' },
  { max: 12, label: 'Tenure',                note: 'years owned (retirement-liquidity skew)' },
  { max: 10, label: 'Stacked debt',          note: 'default + lien amounts' },
  { max:  8, label: 'Absentee owner',        note: 'mailing state ≠ property state' },
  { max:  6, label: 'Stale sale history',    note: 'last sale 15+ years ago' },
  { max:  6, label: 'HOA delinquent',        note: 'broader financial stress signal' },
  { max:  5, label: 'Multiple mortgages',    note: 'junior + senior layering' },
  { max:  4, label: 'Recency bonus',         note: 'fresh signals score higher' },
];

function SectionTitle({
  icon: Icon, children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2 mb-1">
      <Icon className="w-4 h-4 text-brand-500" />
      <h3 className="font-display font-extrabold text-brand-navy text-sm uppercase tracking-[0.12em]">
        {children}
      </h3>
    </div>
  );
}

function PipeStep({
  n, icon: Icon, accent, title, desc, pills,
}: {
  n: number;
  icon: React.ComponentType<{ className?: string }>;
  accent: string;
  title: string;
  desc: string;
  pills?: string[];
}) {
  return (
    <li className="relative pl-12">
      {/* connector */}
      <span className="absolute left-[18px] top-9 bottom-[-12px] w-px bg-slate-200" />
      {/* numbered icon */}
      <div
        className="absolute left-0 top-0.5 w-9 h-9 rounded-full flex items-center justify-center text-white font-bold text-xs shadow-sm"
        style={{ background: accent, boxShadow: `0 6px 14px -4px ${accent}80` }}
      >
        <Icon className="w-4 h-4" />
      </div>
      <div className="font-display font-bold text-slate-900 text-sm flex items-center gap-2">
        <span className="text-[10px] font-mono text-slate-400">0{n}</span>
        {title}
      </div>
      <p className="mt-1 text-xs text-slate-600 leading-relaxed">{desc}</p>
      {pills && pills.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {pills.map((p, i) => (
            <span
              key={p}
              className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-slate-600 bg-slate-50 border border-slate-200 rounded-full px-2 py-0.5"
            >
              {i > 0 && <ArrowDown className="w-3 h-3 text-slate-300 -rotate-90" />}
              {p}
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

function SourceCard({
  name, tier, desc, color,
}: { name: string; tier: string; desc: string; color: string }) {
  return (
    <div className="rounded-xl border border-slate-200 p-3 bg-white relative overflow-hidden">
      <div
        className="absolute top-0 left-0 w-1 h-full"
        style={{ background: color }}
      />
      <div className="pl-2">
        <div className="font-display font-bold text-slate-900 text-sm">{name}</div>
        <div className="text-[10px] uppercase tracking-wider font-semibold mt-0.5"
          style={{ color }}>
          {tier}
        </div>
        <p className="mt-1.5 text-[11px] text-slate-600 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

function ConfRow({
  color, label, children,
}: { color: string; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-50 border border-slate-100">
      <div className="mt-1 w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
      <div className="text-xs">
        <strong className="text-slate-800">{label}</strong>
        <div className="text-slate-600 mt-0.5 leading-relaxed">{children}</div>
      </div>
    </div>
  );
}
