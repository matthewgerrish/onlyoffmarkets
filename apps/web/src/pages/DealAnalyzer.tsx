import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Search, Sparkles, Loader2, MapPin, Home, ArrowRight,
  Flame, Target, Building2, Calendar, Bed, Bath, Maximize2,
  TrendingUp, AlertTriangle, Crown, Send, ExternalLink,
} from 'lucide-react';
import Seo from '../components/Seo';
import { useToast } from '../components/Toast';
import { analyzeAddress, AnalyzerResponse } from '../lib/analyzer';

/** Free-text deal analyzer.
 *
 * Address in → composite analysis out:
 *   • Deal score (distress + financial pressure + recency)
 *   • ADU potential (WA + CA only) with units-possible
 *   • Owner / building / valuation snapshot
 */
export default function DealAnalyzer() {
  const [address, setAddress] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AnalyzerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  useEffect(() => { inputRef.current?.focus(); }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await analyzeAddress(address.trim());
      setResult(r);
      if (!r.sources.found) {
        toast.info('No parcel match — showing geocoded location + state-law ADU only');
      }
    } catch (e) {
      setError((e as Error).message || 'Analysis failed');
    } finally {
      setBusy(false);
    }
  };

  const tryExample = (q: string) => { setAddress(q); inputRef.current?.focus(); };

  return (
    <>
      <Seo title="Deal Analyzer · OnlyOffMarkets" />

      {/* HERO + INPUT */}
      <section className="relative overflow-hidden bg-gradient-to-b from-brand-50/60 via-white to-white">
        <div className="absolute inset-x-0 top-0 h-[460px] bg-[radial-gradient(ellipse_at_top,rgba(29,108,242,0.18),transparent_70%)] pointer-events-none" />
        <div className="container-page relative pt-12 pb-16">
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-slate-200 text-xs text-slate-600 mb-5 shadow-sm animate-fade-in-down">
              <Sparkles className="w-3.5 h-3.5 text-brand-500" />
              <span className="font-semibold">Deal Analyzer</span>
              <span className="text-slate-400">·</span>
              <span>any US address · ADU score for WA + CA</span>
            </div>
            <h1 className="font-display text-5xl sm:text-6xl font-extrabold tracking-tight text-brand-navy leading-[1.02] animate-fade-in-up">
              Score any address<br />
              <span className="text-brand-500">in five seconds.</span>
            </h1>
            <p className="mt-5 text-lg text-slate-600 max-w-xl mx-auto animate-fade-in-up" style={{ animationDelay: '90ms' }}>
              Distress signals, equity, ADU potential — combined into one
              walk-on-a-deal-or-walk-away gauge.
            </p>

            <form onSubmit={onSubmit} className="mt-7 max-w-xl mx-auto animate-fade-in-up" style={{ animationDelay: '160ms' }}>
              <div className="relative">
                <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  ref={inputRef}
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="123 Main St, Seattle WA 98101"
                  className="w-full bg-white border border-slate-200 rounded-full pl-12 pr-32 py-4 text-base
                    text-slate-900 placeholder:text-slate-400 shadow-brand
                    focus:outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                  required
                />
                <button
                  type="submit"
                  disabled={busy}
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 btn-primary !px-5 !py-2.5 text-sm disabled:opacity-60"
                >
                  {busy ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Analyzing…
                    </>
                  ) : (
                    <>Analyze <ArrowRight className="w-4 h-4" /></>
                  )}
                </button>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 justify-center">
                {[
                  '1234 1st Ave, Seattle WA',
                  '500 Sunset Blvd, Los Angeles CA',
                  '78 Lombard St, San Francisco CA',
                ].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => tryExample(q)}
                    className="text-[11px] text-slate-500 hover:text-brand-600 bg-white border border-slate-200 hover:border-brand-300 rounded-full px-2.5 py-1 transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </form>

            {error && (
              <div className="mt-5 max-w-xl mx-auto card p-3 bg-rose-50 border-rose-200 text-rose-700 text-sm inline-flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
              </div>
            )}
          </div>
        </div>
      </section>

      {result && <ResultPanel r={result} />}
    </>
  );
}

/* ---------------- Result panel ---------------- */

function ResultPanel({ r }: { r: AnalyzerResponse }) {
  const dealScore = computeDealScore(r);
  return (
    <section className="container-page py-12 animate-fade-in-up">
      {/* Heading bar */}
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">Analysis</p>
          <h2 className="font-display text-3xl font-extrabold text-brand-navy mt-1 truncate">
            {r.address || r.query}
          </h2>
          <div className="mt-1 text-sm text-slate-500 inline-flex items-center gap-2 flex-wrap">
            <MapPin className="w-3.5 h-3.5 text-brand-400" />
            {[r.city, r.state, r.zip].filter(Boolean).join(', ') || 'Location resolved'}
            {r.county && <span className="text-slate-400">· {r.county}</span>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <SourcePill r={r} />
        </div>
      </div>

      {/* DUAL GAUGES */}
      <div className="mt-8 grid lg:grid-cols-2 gap-5">
        <DealGauge score={dealScore.total} band={dealScore.band} breakdown={dealScore.breakdown} />
        <AduGauge adu={r.adu} />
      </div>

      {/* PROPERTY SNAPSHOT */}
      <div className="mt-5 card p-5">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
          Property snapshot
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
          <Datum icon={Home} label="Type" value={fmtType(r.property_type)} />
          <Datum icon={Calendar} label="Year built" value={r.year_built} />
          <Datum icon={Bed} label="Beds" value={r.bedrooms} />
          <Datum icon={Bath} label="Baths" value={fmt(r.bathrooms)} />
          <Datum icon={Maximize2} label="Living sqft" value={fmtInt(r.sqft)} />
          <Datum icon={Maximize2} label="Lot sqft" value={fmtInt(r.lot_sqft)} />
        </div>
      </div>

      {/* FINANCIAL */}
      <div className="mt-5 grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <MoneyCard label="Estimated value" v={r.estimated_value} accent="brand" />
        <MoneyCard label="Assessed" v={r.assessed_value} accent="slate" />
        <MoneyCard label="Loan balance" v={r.loan_balance} accent="rose" sub={r.ltv != null ? `${Math.round(r.ltv * 100)}% LTV` : undefined} />
        <MoneyCard
          label="Equity"
          v={r.equity}
          accent="emerald"
          sub={r.estimated_value && r.equity != null && r.estimated_value > 0
            ? `${Math.round((r.equity / r.estimated_value) * 100)}% of value`
            : undefined}
        />
      </div>

      {/* DISTRESS + OWNER */}
      <div className="mt-5 grid lg:grid-cols-2 gap-5">
        <DistressCard r={r} />
        <OwnerCard r={r} />
      </div>

      {/* ACTIONS */}
      <div className="mt-6 card p-5 bg-gradient-to-br from-brand-50 via-white to-amber-50">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <div className="font-display font-bold text-brand-navy inline-flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-500" /> Next steps
            </div>
            <p className="text-sm text-slate-600 mt-1 max-w-xl">
              {dealScore.total >= 70
                ? "Strong signal. Skip-trace the owner and queue a postcard while it's fresh."
                : dealScore.total >= 40
                ? 'Worth a closer look. Pull the owner contact and watch for new signals.'
                : 'Light signal. Add to your watch list — re-score in 30 days.'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/search" className="btn-outline text-sm">
              <Send className="w-4 h-4" /> Send mailer
            </Link>
            <Link to="/alerts" className="btn-primary text-sm">
              <Flame className="w-4 h-4" /> Save to alerts
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------------- Gauges ---------------- */

function DealGauge({
  score, band, breakdown,
}: { score: number; band: string; breakdown: Array<{ key: string; label: string; points: number; detail?: string }> }) {
  const hex = bandHex(band);
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(score));
    return () => cancelAnimationFrame(id);
  }, [score]);
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="font-display font-bold text-brand-navy inline-flex items-center gap-2">
          <Target className="w-5 h-5" style={{ color: hex }} /> Deal score
        </div>
        <span className="pill text-[11px] uppercase tracking-wider font-bold"
          style={{ color: hex, backgroundColor: hex + '15', borderColor: hex + '40', borderWidth: 1 }}>
          {band}
        </span>
      </div>
      <div className="flex items-center gap-5">
        <div className="relative w-28 h-28 shrink-0">
          <svg viewBox="0 0 36 36" className="absolute inset-0 -rotate-90">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgb(241,245,249)" strokeWidth="3.5" />
            <circle
              cx="18" cy="18" r="15.9" fill="none" strokeWidth="3.5" strokeLinecap="round"
              stroke={hex}
              style={{
                strokeDasharray: `${shown} 100`,
                transition: 'stroke-dasharray 900ms cubic-bezier(0.16, 1, 0.3, 1)',
              }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display font-extrabold text-3xl tabular-nums" style={{ color: hex }}>
              {score}
            </span>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">/100</span>
          </div>
        </div>
        <div className="min-w-0 flex-1">
          {breakdown.length === 0 ? (
            <div className="text-sm text-slate-500">
              No active distress signals. Score reflects state-baseline only.
            </div>
          ) : (
            <ul className="space-y-1.5">
              {breakdown.slice(0, 4).map((b) => (
                <li key={b.key + b.label} className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-slate-600 truncate">{b.label}</span>
                  <span className="font-mono font-bold text-slate-900 tabular-nums">
                    {b.points >= 0 ? '+' : ''}{b.points}
                  </span>
                </li>
              ))}
              {breakdown.length > 4 && (
                <li className="text-[11px] text-slate-400 italic">
                  + {breakdown.length - 4} more factor{breakdown.length - 4 === 1 ? '' : 's'}
                </li>
              )}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function AduGauge({ adu }: { adu: AnalyzerResponse['adu'] }) {
  const hex = aduHex(adu.band);
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(adu.score));
    return () => cancelAnimationFrame(id);
  }, [adu.score]);
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="font-display font-bold text-brand-navy inline-flex items-center gap-2">
          <Building2 className="w-5 h-5" style={{ color: hex }} /> ADU potential
        </div>
        <span className="pill text-[11px] uppercase tracking-wider font-bold"
          style={{ color: hex, backgroundColor: hex + '15', borderColor: hex + '40', borderWidth: 1 }}>
          {adu.band}
        </span>
      </div>
      <div className="flex items-center gap-5">
        <div className="relative w-28 h-28 shrink-0">
          <svg viewBox="0 0 36 36" className="absolute inset-0 -rotate-90">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgb(241,245,249)" strokeWidth="3.5" />
            <circle
              cx="18" cy="18" r="15.9" fill="none" strokeWidth="3.5" strokeLinecap="round"
              stroke={hex}
              style={{
                strokeDasharray: `${shown} 100`,
                transition: 'stroke-dasharray 900ms cubic-bezier(0.16, 1, 0.3, 1)',
              }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display font-extrabold text-3xl tabular-nums" style={{ color: hex }}>
              {adu.score}
            </span>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">/100</span>
          </div>
        </div>
        <div className="min-w-0 flex-1">
          {!adu.eligible ? (
            <div className="text-sm text-slate-500">
              {adu.notes[0] || 'Not eligible based on available data.'}
            </div>
          ) : (
            <>
              <div className="text-sm text-slate-700 mb-2">
                Up to <strong className="text-brand-navy">{adu.units_possible} dwelling unit{adu.units_possible === 1 ? '' : 's'}</strong>
                {' '}possible {adu.state ? `under ${adu.state}` : ''}{adu.state === 'CA' ? ' AB 68 / SB 9' : adu.state === 'WA' ? ' HB 1337' : ''}.
              </div>
              <ul className="space-y-1.5">
                {adu.breakdown.slice(0, 3).map((b) => (
                  <li key={b.key + b.label} className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-slate-600 truncate">{b.label}</span>
                    <span className="font-mono font-bold text-slate-900 tabular-nums">
                      +{b.points}
                    </span>
                  </li>
                ))}
                {adu.breakdown.length > 3 && (
                  <li className="text-[11px] text-slate-400 italic">
                    + {adu.breakdown.length - 3} more factor{adu.breakdown.length - 3 === 1 ? '' : 's'}
                  </li>
                )}
              </ul>
            </>
          )}
        </div>
      </div>
      {adu.notes.length > 0 && (
        <p className="mt-4 text-[11px] text-slate-500 italic leading-relaxed">
          {adu.notes[0]}
        </p>
      )}
    </div>
  );
}

/* ---------------- Cards / atoms ---------------- */

function MoneyCard({ label, v, accent, sub }: { label: string; v: number | null; accent: 'brand' | 'slate' | 'rose' | 'emerald'; sub?: string }) {
  const cls = {
    brand: 'border-brand-200 text-brand-700',
    slate: 'border-slate-200 text-slate-700',
    rose:  'border-rose-200 text-rose-700',
    emerald: 'border-emerald-200 text-emerald-700',
  }[accent];
  return (
    <div className={`card p-4 border ${cls}`}>
      <div className="text-[10px] uppercase tracking-wider font-bold opacity-70">{label}</div>
      <div className="font-display font-extrabold text-2xl mt-1 tabular-nums text-slate-900">
        {v != null ? `$${v.toLocaleString()}` : '—'}
      </div>
      {sub && <div className="text-[11px] text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}

function DistressCard({ r }: { r: AnalyzerResponse }) {
  const tags = r.distress.tags || [];
  return (
    <div className="card p-5">
      <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 inline-flex items-center gap-2">
        <Flame className="w-3.5 h-3.5 text-rose-500" /> Distress signals
      </div>
      {tags.length === 0 ? (
        <div className="text-sm text-slate-500">No active distress signals on file.</div>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((t) => (
            <span key={t} className="pill bg-rose-50 text-rose-700 border border-rose-100 text-[11px]">
              {t.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}
      <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
        {r.distress.default_amount != null && (
          <Mini label="Default amount" v={`$${r.distress.default_amount.toLocaleString()}`} />
        )}
        {r.distress.years_delinquent != null && (
          <Mini label="Years delinquent" v={r.distress.years_delinquent} />
        )}
        {r.distress.vacancy_months != null && (
          <Mini label="Months vacant" v={r.distress.vacancy_months} />
        )}
        {r.distress.sale_date && (
          <Mini label="Sale date" v={String(r.distress.sale_date).slice(0, 10)} />
        )}
      </div>
    </div>
  );
}

function OwnerCard({ r }: { r: AnalyzerResponse }) {
  return (
    <div className="card p-5">
      <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 inline-flex items-center gap-2">
        <Crown className="w-3.5 h-3.5 text-amber-500" /> Owner
      </div>
      <div className="text-slate-900 font-display font-bold">
        {r.owner_name || '—'}
      </div>
      {r.owner_state && r.state && r.owner_state !== r.state && (
        <div className="mt-1 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-50 border border-amber-100 text-amber-700 text-[10px] font-bold uppercase tracking-wider">
          Absentee — mails to {r.owner_state}
        </div>
      )}
      {r.parcel_apn && (
        <div className="mt-3 text-xs text-slate-500">
          <span className="text-slate-400">APN:</span>{' '}
          <span className="font-mono">{r.parcel_apn}</span>
        </div>
      )}
      {r.lat && r.lng && (
        <a
          href={`https://www.google.com/maps?q=${r.lat},${r.lng}`}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"
        >
          <ExternalLink className="w-3 h-3" /> View on map
        </a>
      )}
    </div>
  );
}

function Datum({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value: any }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold flex items-center gap-1">
        <Icon className="w-3 h-3" /> {label}
      </div>
      <div className="mt-0.5 font-display font-extrabold text-slate-900 tabular-nums">
        {value != null && value !== '' ? value : <span className="text-slate-300 font-normal">—</span>}
      </div>
    </div>
  );
}

function Mini({ label, v }: { label: string; v: any }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2 border border-slate-100">
      <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">{label}</div>
      <div className="font-mono font-bold text-slate-900 tabular-nums">{v}</div>
    </div>
  );
}

function SourcePill({ r }: { r: AnalyzerResponse }) {
  const sources: string[] = [];
  if (r.sources.off_market_db) sources.push('OnlyOffMarkets DB');
  if (r.sources.propertyradar) sources.push('PropertyRadar');
  if (r.sources.attom)         sources.push('ATTOM');
  return (
    <div className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
      {sources.length === 0 ? 'geocoded only · upgrade for full property data' : 'data: ' + sources.join(' + ')}
    </div>
  );
}

/* ---------------- Helpers ---------------- */

function fmt(v: any): any { return v == null || v === '' ? null : v; }
function fmtInt(v: number | null): string | null { return v == null ? null : v.toLocaleString(); }
function fmtType(s: string | null): string | null {
  if (!s) return null;
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function bandHex(band: string): string {
  switch (band) {
    case 'top':     return '#f43f5e';
    case 'hot':     return '#f97316';
    case 'warm':    return '#f59e0b';
    case 'warming': return '#eab308';
    default:        return '#1d6cf2';
  }
}

function aduHex(band: string): string {
  switch (band) {
    case 'excellent': return '#10b981';
    case 'good':      return '#22c55e';
    case 'limited':   return '#eab308';
    default:          return '#94a3b8';
  }
}

/** Minimal client-side scoring mirror — the backend already returns
 *  the inputs we need; we recompute here so the UI updates instantly
 *  if we adjust the formula later without an API roundtrip. */
function computeDealScore(r: AnalyzerResponse): {
  total: number; band: string;
  breakdown: Array<{ key: string; label: string; points: number; detail?: string }>;
} {
  const breakdown: Array<{ key: string; label: string; points: number; detail?: string }> = [];
  let total = 0;
  const W: Record<string, number> = {
    auction: 25, preforeclosure: 22, 'tax-lien': 18, probate: 16,
    vacant: 14, reo: 12, fsbo: 10, motivated_seller: 12,
    expired: 8, canceled: 8, wholesale: 6, network: 4,
  };
  // top source
  let top = 0; let topTag: string | null = null;
  for (const t of r.distress.tags) {
    const w = W[t] ?? 0;
    if (w > top) { top = w; topTag = t; }
  }
  if (topTag) {
    breakdown.push({ key: 'primary', label: `${topTag.replace(/_/g, ' ')} signal`, points: top });
    total += top;
  }
  const extras = r.distress.tags.length - 1;
  if (extras > 0) {
    const pts = Math.min(extras * 6, 18);
    breakdown.push({ key: 'stack', label: `${extras} stacked source${extras === 1 ? '' : 's'}`, points: pts });
    total += pts;
  }
  if (r.distress.years_delinquent && r.distress.years_delinquent > 0) {
    const pts = Math.min(r.distress.years_delinquent * 4, 16);
    breakdown.push({ key: 'delinq', label: `${r.distress.years_delinquent}y delinquent`, points: pts });
    total += pts;
  }
  if (r.distress.vacancy_months && r.distress.vacancy_months > 0) {
    const pts = Math.min(Math.round(r.distress.vacancy_months * 1.5), 14);
    breakdown.push({ key: 'vacant', label: `${r.distress.vacancy_months}mo vacant`, points: pts });
    total += pts;
  }
  if (r.owner_state && r.state && r.owner_state !== r.state) {
    breakdown.push({ key: 'absentee', label: `Absentee owner (${r.owner_state})`, points: 8 });
    total += 8;
  }
  if (r.distress.sale_date) {
    const days = Math.round((new Date(r.distress.sale_date).getTime() - Date.now()) / 86_400_000);
    if (days >= 0 && days <= 60) {
      const pts = days <= 14 ? 14 : days <= 30 ? 10 : 6;
      breakdown.push({ key: 'sale', label: `Sale in ${days}d`, points: pts });
      total += pts;
    }
  }
  // LTV
  if (r.estimated_value && r.loan_balance != null && r.estimated_value > 0) {
    const ltv = r.loan_balance / r.estimated_value;
    let pts = 0; let label = '';
    if (ltv <= 0.05)        { pts = 18; label = 'Owned free & clear'; }
    else if (ltv <= 0.4)    { pts = 14; label = `Low LTV ${Math.round(ltv * 100)}%`; }
    else if (ltv <= 0.65)   { pts =  9; label = `Moderate LTV ${Math.round(ltv * 100)}%`; }
    else if (ltv < 0.85)    { pts =  4; label = `High LTV ${Math.round(ltv * 100)}%`; }
    else if (ltv < 1.0)     { pts =  0; label = `Tight LTV ${Math.round(ltv * 100)}%`; }
    else                    { pts = -8; label = `Underwater ${Math.round(ltv * 100)}%`; }
    if (pts !== 0 || label) {
      breakdown.push({ key: 'ltv', label, points: pts });
      total += pts;
    }
  }
  if (r.spread_pct && r.spread_pct > 0.02) {
    const pts = Math.min(Math.round(r.spread_pct * 60), 18);
    breakdown.push({ key: 'spread', label: `Asking ${Math.round(r.spread_pct * 100)}% below est.`, points: pts });
    total += pts;
  }
  total = Math.max(0, Math.min(100, Math.round(total)));
  let band = 'cold';
  if (total >= 85) band = 'top';
  else if (total >= 70) band = 'hot';
  else if (total >= 50) band = 'warm';
  else if (total >= 30) band = 'warming';
  return { total, band, breakdown };
}

void TrendingUp; // kept import in case we add a trend chip later
