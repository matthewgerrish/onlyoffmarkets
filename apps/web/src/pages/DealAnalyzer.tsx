import { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import {
  Sparkles, MapPin, Home, Loader2,
  Flame, Target, Building2, Calendar, Bed, Bath, Maximize2,
  TrendingUp, AlertTriangle, Crown, Send, ExternalLink,
  Radar, CheckCircle2, Bookmark, BookmarkCheck,
} from 'lucide-react';
import Seo from '../components/Seo';
import { useToast } from '../components/Toast';
import ScoreGauge from '../components/ScoreGauge';
import AddressAutocomplete from '../components/AddressAutocomplete';
import { analyzeAddress, AnalyzerResponse } from '../lib/analyzer';
import { saveToWatchlist, parcelKeyFor } from '../lib/watchlist';

/** Free-text deal analyzer.
 *
 * Address in → composite analysis out:
 *   • Deal score (distress + financial pressure + recency)
 *   • ADU potential (WA + CA only) with units-possible
 *   • Owner / building / valuation snapshot
 */
type Step = 0 | 1 | 2 | 3;
const STEPS = [
  { label: 'Geocoding address', icon: MapPin },
  { label: 'Looking up parcel', icon: Home },
  { label: 'Computing score', icon: Target },
] as const;

export default function DealAnalyzer() {
  const [address, setAddress] = useState('');
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState<Step>(0);
  const [result, setResult] = useState<AnalyzerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [params, setParams] = useSearchParams();
  const toast = useToast();

  // Synthetic step animation while the real analysis runs server-side.
  useEffect(() => {
    if (!busy) return;
    setStep(0);
    const t1 = setTimeout(() => setStep(1), 400);
    const t2 = setTimeout(() => setStep(2), 900);
    const t3 = setTimeout(() => setStep(3), 1500);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [busy]);

  // Pre-fill from ?address= (e.g. arriving from Watchlist re-Recon).
  useEffect(() => {
    const a = params.get('address');
    if (a) {
      setAddress(a);
      void runAnalysis(a);
      params.delete('address');
      setParams(params, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runAnalysis = async (q: string) => {
    if (!q.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await analyzeAddress(q.trim());
      setResult(r);
      if (!r.sources.found) {
        toast.info('No parcel match — showing geocoded location + state-law ADU only');
      }
    } catch (e) {
      setError((e as Error).message || 'Recon failed');
    } finally {
      setBusy(false);
    }
  };

  const tryExample = (q: string) => {
    setAddress(q);
    void runAnalysis(q);
  };

  return (
    <>
      <Seo title="Recon · OnlyOffMarkets" />

      {/* HERO + INPUT */}
      <section className="relative overflow-hidden hero-glow bg-gradient-to-b from-brand-50/40 via-white to-white">
        {/* Floating radar-pulse rings — pinging the target */}
        <div className="pointer-events-none absolute inset-0 flex items-start justify-center pt-32 opacity-40">
          <div className="absolute w-72 h-72 rounded-full border border-brand-300 animate-pulse-ring" style={{ animationDuration: '3s' }} />
          <div className="absolute w-96 h-96 rounded-full border border-brand-200 animate-pulse-ring" style={{ animationDuration: '4s', animationDelay: '0.6s' }} />
        </div>
        <div className="container-page relative pt-12 pb-16">
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-slate-200 text-xs text-slate-600 mb-5 shadow-sm animate-fade-in-down">
              <Radar className="w-3.5 h-3.5 text-brand-500" />
              <span className="font-semibold">Recon</span>
              <span className="text-slate-400">·</span>
              <span>any US address · ADU score for WA + CA</span>
            </div>
            <h1 className="font-display text-5xl sm:text-6xl font-extrabold tracking-tight text-brand-navy leading-[1.02] animate-fade-in-up">
              Read any address<br />
              <span className="text-brand-500">in five seconds.</span>
            </h1>
            <p className="mt-5 text-lg text-slate-600 max-w-xl mx-auto animate-fade-in-up" style={{ animationDelay: '90ms' }}>
              Drop an address. Get a deal score, ADU potential, owner snapshot,
              and a one-line "go or skip" call — instantly.
            </p>

            <div className="mt-7 max-w-xl mx-auto animate-fade-in-up" style={{ animationDelay: '160ms' }}>
              <AddressAutocomplete
                value={address}
                onChange={setAddress}
                onSelect={(v) => { setAddress(v); void runAnalysis(v); }}
                busy={busy}
              />
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
            </div>

            {error && (
              <div className="mt-5 max-w-xl mx-auto card p-3 bg-rose-50 border-rose-200 text-rose-700 text-sm inline-flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
              </div>
            )}
          </div>
        </div>
      </section>

      {busy && !result && <ScanningPanel step={step} />}
      {result && <ResultPanel r={result} />}
    </>
  );
}

/** Multi-step skeleton shown while the analyzer is running. */
function ScanningPanel({ step }: { step: Step }) {
  return (
    <section className="container-page py-12 animate-fade-in">
      <div className="max-w-2xl mx-auto card p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-full bg-brand-50 text-brand-500 inline-flex items-center justify-center">
            <Radar className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-brand-500">
              Recon in progress
            </div>
            <div className="text-sm text-slate-500">
              Live look-up across our DB + paid sources
            </div>
          </div>
        </div>

        <ol className="mt-3 space-y-3">
          {STEPS.map((s, i) => {
            const active = step === i;
            const done = step > i;
            const Icon = s.icon;
            return (
              <li
                key={s.label}
                className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                  active ? 'border-brand-300 bg-brand-50/40 shadow-brand'
                  : done ? 'border-emerald-200 bg-emerald-50/40'
                  : 'border-slate-100 bg-slate-50'
                }`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                  active ? 'bg-brand-500 text-white shadow-glow-brand'
                  : done ? 'bg-emerald-500 text-white'
                  : 'bg-white border border-slate-200 text-slate-400'
                }`}>
                  {done ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </div>
                <div className={`text-sm font-semibold ${
                  active ? 'text-brand-700' : done ? 'text-emerald-700' : 'text-slate-500'
                }`}>
                  {s.label}{active ? '…' : done ? ' ✓' : ''}
                </div>
              </li>
            );
          })}
        </ol>

        <div className="mt-5 grid grid-cols-2 gap-3">
          <div className="skeleton h-24 rounded-2xl" />
          <div className="skeleton h-24 rounded-2xl" />
        </div>
      </div>
    </section>
  );
}

/* ---------------- Result panel ---------------- */

function ResultPanel({ r }: { r: AnalyzerResponse }) {
  // Backend is authoritative now. Frontend just renders.
  const deal = r.deal;
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const toast = useToast();
  const nav = useNavigate();
  const parcelKey = parcelKeyFor(r);

  const onSave = async () => {
    if (saved || saving) return;
    setSaving(true);
    try {
      await saveToWatchlist({
        parcel_key: parcelKey,
        address:    r.address || r.query,
        city:       r.city,
        state:      r.state,
        zip:        r.zip,
        lat:        r.lat,
        lng:        r.lng,
        deal_score: r.deal.total,
        deal_band:  r.deal.band,
        adu_score:  r.adu.score,
        adu_band:   r.adu.band,
        snapshot:   r,
      });
      setSaved(true);
      toast.success('Saved to watchlist');
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const onMail = () => {
    nav(`/mailers?parcels=${encodeURIComponent(parcelKey)}`);
  };
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
          <ConfidencePill confidence={deal.confidence} />
          <SourcePill r={r} />
        </div>
      </div>

      {/* DUAL GAUGES */}
      <div className="mt-8 grid lg:grid-cols-2 gap-5">
        <DealGauge score={deal.total} band={deal.band} breakdown={deal.breakdown} />
        <AduGauge adu={r.adu} />
      </div>

      {/* RECOMMENDED NEXT */}
      <div className="mt-5 card p-4 bg-gradient-to-r from-brand-50 via-white to-amber-50 border-brand-100">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-white border border-brand-100 flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4 text-brand-500" />
          </div>
          <div className="text-sm text-slate-700">
            <strong className="text-brand-navy">Recommendation: </strong>
            {deal.recommendation}
          </div>
        </div>
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

      {/* FORECLOSURE TIMELINE (only when there's an active stage) */}
      {(r.distress.foreclosure_stage || r.distress.sale_date) && (
        <div className="mt-5">
          <ForeclosureTimeline r={r} />
        </div>
      )}

      {/* DISTRESS + OWNER */}
      <div className="mt-5 grid lg:grid-cols-2 gap-5">
        <DistressCard r={r} />
        <OwnerCard r={r} />
      </div>

      {/* OWNERSHIP / SALE HISTORY (only when paid source delivered them) */}
      {(r.ownership.years_owned !== null || r.ownership.last_sale_date || r.ownership.equity_pct !== null) && (
        <div className="mt-5 card p-5">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 inline-flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 text-brand-500" /> Ownership context
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {r.ownership.years_owned != null && (
              <Datum
                icon={Calendar}
                label="Years owned"
                value={`${r.ownership.years_owned}y`}
              />
            )}
            {r.ownership.equity_pct != null && (
              <Datum
                icon={TrendingUp}
                label="Equity"
                value={`${Math.round(r.ownership.equity_pct * 100)}%`}
              />
            )}
            {r.ownership.last_sale_date && (
              <Datum
                icon={Calendar}
                label="Last sale"
                value={String(r.ownership.last_sale_date).slice(0, 10)}
              />
            )}
            {r.ownership.last_sale_price != null && (
              <Datum
                icon={TrendingUp}
                label="Sale price"
                value={`$${r.ownership.last_sale_price.toLocaleString()}`}
              />
            )}
            {r.ownership.mortgage_count != null && r.ownership.mortgage_count > 0 && (
              <Datum
                icon={Home}
                label="Mortgages"
                value={r.ownership.mortgage_count}
              />
            )}
          </div>
        </div>
      )}

      {/* ACTIONS */}
      <div className="mt-6 card p-5 bg-gradient-to-br from-brand-50 via-white to-amber-50">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <div className="font-display font-bold text-brand-navy inline-flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-500" /> Next steps
            </div>
            <p className="text-sm text-slate-600 mt-1 max-w-xl">
              {deal.total >= 70
                ? "Strong signal. Skip-trace the owner and queue a postcard while it's fresh."
                : deal.total >= 40
                ? 'Worth a closer look. Pull the owner contact and watch for new signals.'
                : 'Light signal. Add to your watch list — re-score in 30 days.'}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={onSave}
              disabled={saving}
              className={`btn-outline text-sm ${saved ? 'border-emerald-300 text-emerald-700 hover:!text-emerald-800' : ''}`}
            >
              {saved ? (
                <><BookmarkCheck className="w-4 h-4" /> Saved</>
              ) : saving ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
              ) : (
                <><Bookmark className="w-4 h-4" /> Save to watchlist</>
              )}
            </button>
            <button onClick={onMail} className="btn-outline text-sm">
              <Send className="w-4 h-4" /> Send mailer
            </button>
            <Link to="/alerts" className="btn-primary text-sm">
              <Flame className="w-4 h-4" /> Save alert
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
  return (
    <div className="card card-hover p-6 relative overflow-hidden">
      {/* radial brand-glow as a subtle background layer */}
      <div
        className="absolute -top-10 -right-10 w-40 h-40 rounded-full blur-3xl opacity-30 pointer-events-none"
        style={{ background: hex }}
      />
      <div className="relative flex items-center justify-between gap-3 mb-4">
        <div className="font-display font-bold text-brand-navy inline-flex items-center gap-2">
          <Target className="w-5 h-5" style={{ color: hex }} /> Deal score
        </div>
        <span className="pill text-[11px] uppercase tracking-wider font-bold"
          style={{ color: hex, backgroundColor: hex + '15', borderColor: hex + '40', borderWidth: 1 }}>
          {band}
        </span>
      </div>
      <div className="relative flex items-center gap-5">
        <ScoreGauge score={score} hex={hex} size={112} />
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
  return (
    <div className="card card-hover p-6 relative overflow-hidden">
      <div
        className="absolute -top-10 -left-10 w-40 h-40 rounded-full blur-3xl opacity-30 pointer-events-none"
        style={{ background: hex }}
      />
      <div className="relative flex items-center justify-between gap-3 mb-4">
        <div className="font-display font-bold text-brand-navy inline-flex items-center gap-2">
          <Building2 className="w-5 h-5" style={{ color: hex }} /> ADU potential
        </div>
        <span className="pill text-[11px] uppercase tracking-wider font-bold"
          style={{ color: hex, backgroundColor: hex + '15', borderColor: hex + '40', borderWidth: 1 }}>
          {adu.band}
        </span>
      </div>
      <div className="relative flex items-center gap-5">
        <ScoreGauge score={adu.score} hex={hex} size={112} />
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

function ConfidencePill({ confidence }: { confidence: number }) {
  // Buckets: 0-40 = thin, 40-70 = ok, 70+ = strong
  const tier =
    confidence >= 70 ? 'strong' : confidence >= 40 ? 'ok' : 'thin';
  const cfg = {
    strong: { cls: 'bg-emerald-50 text-emerald-700 border border-emerald-100', dot: 'bg-emerald-500' },
    ok:     { cls: 'bg-amber-50 text-amber-700 border border-amber-100',       dot: 'bg-amber-500' },
    thin:   { cls: 'bg-slate-100 text-slate-600 border border-slate-200',       dot: 'bg-slate-400' },
  }[tier];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${cfg.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {confidence}% confidence
    </span>
  );
}

function ForeclosureTimeline({ r }: { r: AnalyzerResponse }) {
  const stage = (r.distress.foreclosure_stage || '').toUpperCase();
  const sale = r.distress.sale_date;
  const days =
    sale ? Math.round((new Date(sale).getTime() - Date.now()) / 86_400_000) : null;
  const steps: Array<{ key: string; label: string; active: boolean; future?: boolean }> = [
    { key: 'NOD',     label: 'NOD filed',         active: stage === 'NOD' || stage === 'NTS' || stage === 'AUCTION' },
    { key: 'NTS',     label: 'NTS recorded',      active: stage === 'NTS' || stage === 'AUCTION' },
    { key: 'AUCTION', label: 'Auction',           active: stage === 'AUCTION' },
    { key: 'REO',     label: 'Bank-owned (REO)',  active: false, future: true },
  ];
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-500 inline-flex items-center gap-2">
          <Flame className="w-3.5 h-3.5 text-rose-500" /> Foreclosure timeline
        </div>
        {days !== null && days >= 0 && (
          <span className="text-[11px] font-mono font-bold text-rose-600 bg-rose-50 border border-rose-100 rounded-full px-2.5 py-1">
            Auction in {days}d
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 sm:gap-4 flex-wrap">
        {steps.map((s, i) => (
          <div key={s.key} className="flex items-center gap-2 sm:gap-3">
            <div className="flex flex-col items-center min-w-[64px]">
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  s.active
                    ? 'bg-rose-500 text-white shadow-glow-rose'
                    : s.future
                    ? 'bg-slate-200 text-slate-400'
                    : 'bg-slate-100 text-slate-400 border border-slate-200'
                }`}
              >
                {i + 1}
              </div>
              <div className={`mt-1.5 text-[10px] font-semibold ${
                s.active ? 'text-rose-600' : 'text-slate-400'
              }`}>
                {s.label}
              </div>
            </div>
            {i < steps.length - 1 && (
              <div className={`hidden sm:block w-8 h-px ${
                steps[i + 1].active ? 'bg-rose-300' : 'bg-slate-200'
              }`} />
            )}
          </div>
        ))}
      </div>
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

/* Server is now the single source of truth for the deal score (see
 * apps/api/services/deal_scoring.py). The frontend just renders. */
