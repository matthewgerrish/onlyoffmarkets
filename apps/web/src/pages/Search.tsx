import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MapPin, Filter, Lock, Loader2, Flame, Send, X, Map as MapIcon, List, Columns } from 'lucide-react';
import Seo from '../components/Seo';
import { DealMeter } from '../components/DealMeter';
import SearchMap from '../components/SearchMap';
import { listOffMarket, OffMarketRow, ApiSource } from '../lib/api';
import { SOURCE_LABELS, ALL_SOURCES } from '../lib/sources';
import { dealScore, bandHex, bandTextColor } from '../lib/score';

type SortMode = 'score' | 'newest';
type ViewMode = 'list' | 'map' | 'split';

export default function Search() {
  const [rows, setRows] = useState<OffMarketRow[] | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);

  const [state, setState] = useState<string>('');
  const [enabledSources, setEnabledSources] = useState<Set<ApiSource>>(new Set(ALL_SOURCES));
  const [minScore, setMinScore] = useState<number>(0);
  const [sortMode, setSortMode] = useState<SortMode>('score');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [view, setView] = useState<ViewMode>(() =>
    typeof window !== 'undefined' && window.innerWidth >= 1280 ? 'split' : 'list'
  );
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const nav = useNavigate();

  // Scroll the hovered card into view (map → list direction)
  useEffect(() => {
    if (!hoveredKey) return;
    const el = document.querySelector<HTMLElement>(`[data-parcel-key="${CSS.escape(hoveredKey)}"]`);
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (rect.top < 80 || rect.bottom > window.innerHeight - 40) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [hoveredKey]);

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    setError(null);
    listOffMarket({ state: state || undefined, limit: 300 })
      .then((data) => {
        if (cancelled) return;
        setRows(data.results);
        setCounts(data.counts);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [state]);

  // Pre-score every row so we can sort + filter cheaply.
  const scored = useMemo(() => {
    if (!rows) return null;
    return rows.map((r) => ({ row: r, score: dealScore(r) }));
  }, [rows]);

  const filtered = useMemo(() => {
    if (!scored) return [];
    let out = scored.filter(({ row, score }) => {
      if (score.total < minScore) return false;
      if (!row.source_tags.some((t) => enabledSources.has(t))) return false;
      return true;
    });
    if (sortMode === 'score') {
      out = [...out].sort((a, b) => b.score.total - a.score.total);
    } else {
      out = [...out].sort(
        (a, b) => new Date(b.row.last_seen).getTime() - new Date(a.row.last_seen).getTime()
      );
    }
    return out;
  }, [scored, enabledSources, minScore, sortMode]);

  const toggleSource = (s: ApiSource) => {
    setEnabledSources((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  const states = useMemo(
    () => Array.from(new Set((rows ?? []).map((r) => r.state))).sort(),
    [rows]
  );

  return (
    <>
      <Seo title="Search off-market signals" />
      <div className="container-page py-8">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="font-display text-3xl font-extrabold text-brand-navy">signal feed</h1>
            <p className="text-sm text-slate-500 mt-1">
              {rows === null
                ? 'Loading…'
                : `${filtered.length} of ${rows.length} match — sorted by ${sortMode === 'score' ? 'deal score' : 'newest'}`}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="text-xs text-slate-500 inline-flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-full">
              <Lock className="w-3 h-3" /> Free preview — sign in for full addresses
            </div>
            <div className="flex bg-slate-100 rounded-full p-1 text-xs font-semibold">
              <button
                onClick={() => setSortMode('score')}
                className={`px-3 py-1.5 rounded-full transition-colors ${
                  sortMode === 'score' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                Hottest
              </button>
              <button
                onClick={() => setSortMode('newest')}
                className={`px-3 py-1.5 rounded-full transition-colors ${
                  sortMode === 'newest' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                Newest
              </button>
            </div>
            <div className="flex bg-slate-100 rounded-full p-1 text-xs font-semibold">
              <button
                onClick={() => setView('list')}
                aria-label="List view"
                className={`px-3 py-1.5 rounded-full inline-flex items-center gap-1.5 transition-colors ${
                  view === 'list' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <List className="w-3.5 h-3.5" /> List
              </button>
              <button
                onClick={() => setView('split')}
                aria-label="Split view"
                className={`px-3 py-1.5 rounded-full inline-flex items-center gap-1.5 transition-colors hidden xl:inline-flex ${
                  view === 'split' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <Columns className="w-3.5 h-3.5" /> Split
              </button>
              <button
                onClick={() => setView('map')}
                aria-label="Map view"
                className={`px-3 py-1.5 rounded-full inline-flex items-center gap-1.5 transition-colors ${
                  view === 'map' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <MapIcon className="w-3.5 h-3.5" /> Map
              </button>
            </div>
          </div>
        </div>

        <div className="mt-6 grid lg:grid-cols-[300px_1fr] gap-6">
          <aside className="card p-5 h-fit lg:sticky lg:top-20">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-4">
              <Filter className="w-4 h-4 text-brand-500" /> Filters
            </div>

            {/* Deal meter slider */}
            <div className="mb-5 p-3 -mx-1 rounded-xl bg-gradient-to-br from-brand-50 via-white to-orange-50 border border-slate-100">
              <div className="flex items-center justify-between text-xs font-bold text-slate-600 mb-1.5">
                <span className="inline-flex items-center gap-1">
                  <Flame className="w-3.5 h-3.5 text-rose-500" /> Deal meter
                </span>
                <span className={`font-mono ${minScore >= 70 ? 'text-rose-600' : minScore >= 50 ? 'text-amber-600' : minScore >= 30 ? 'text-yellow-600' : 'text-brand-600'}`}>
                  ≥ {minScore}
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="w-full accent-rose-500"
                aria-label="Minimum deal score"
              />
              <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
                <span>cold</span>
                <span>warm</span>
                <span>hot</span>
                <span>top</span>
              </div>
              <p className="mt-2 text-[11px] text-slate-500 leading-snug">
                0–100 score from preforeclosure status, debt stack, vacancy, absentee owner, sale-date pressure, and more.
              </p>
            </div>

            <label className="block text-xs font-medium text-slate-600 mb-1">State</label>
            <select className="input w-full mb-4" value={state} onChange={(e) => setState(e.target.value)}>
              <option value="">All states</option>
              {states.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

            <div className="text-xs font-medium text-slate-600 mb-2">Sources</div>
            <div className="flex flex-col gap-2">
              {ALL_SOURCES.map((s) => (
                <label key={s} className="flex items-center justify-between gap-2 text-sm text-slate-700 cursor-pointer">
                  <span className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={enabledSources.has(s)}
                      onChange={() => toggleSource(s)}
                      className="accent-brand-500"
                    />
                    {SOURCE_LABELS[s]}
                  </span>
                  {counts[s] !== undefined && (
                    <span className="text-xs text-slate-400 font-mono">{counts[s]}</span>
                  )}
                </label>
              ))}
            </div>
          </aside>

          <div className={`min-w-0 ${view === 'split' ? 'grid grid-cols-[1fr_1.1fr] gap-4 items-start' : 'space-y-3'}`}>
            {view === 'map' && rows !== null && !error && (
              <SearchMap
                rows={filtered.map((f) => f.row)}
                hoveredKey={hoveredKey}
                onPinHover={setHoveredKey}
                onPinClick={(k) => nav(`/property/${encodeURIComponent(k)}`)}
              />
            )}

            {view === 'split' && (
              <>
                {/* Scrollable list (left) */}
                <div className="space-y-3 max-h-[calc(100vh-160px)] overflow-y-auto pr-1">
                  {error && (
                    <div className="card p-6 text-sm text-rose-600 border-rose-200 bg-rose-50">
                      Failed to load signals: {error}
                    </div>
                  )}
                  {rows === null && !error && (
                    <div className="card p-12 flex items-center justify-center text-slate-400">
                      <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading signals…
                    </div>
                  )}
                  {rows !== null && filtered.length === 0 && !error && (
                    <div className="card p-12 text-center text-slate-400">
                      No signals match. Loosen filters.
                    </div>
                  )}
                  {filtered.map(({ row: p, score }) => (
                    <SplitCard
                      key={p.parcel_key}
                      row={p}
                      score={score}
                      hoveredKey={hoveredKey}
                      selected={selected}
                      setSelected={setSelected}
                      onHover={setHoveredKey}
                    />
                  ))}
                </div>
                {/* Sticky map (right) */}
                <div className="sticky top-20">
                  <SearchMap
                    rows={filtered.map((f) => f.row)}
                    hoveredKey={hoveredKey}
                    onPinHover={setHoveredKey}
                    onPinClick={(k) => nav(`/property/${encodeURIComponent(k)}`)}
                    height="calc(100vh - 160px)"
                  />
                </div>
              </>
            )}

            {view === 'list' && error && (
              <div className="card p-6 text-sm text-rose-600 border-rose-200 bg-rose-50">
                Failed to load signals: {error}
                <div className="mt-2 text-xs text-rose-500">Is the API running on port 8001?</div>
              </div>
            )}

            {view === 'list' && rows === null && !error && (
              <div className="card p-12 flex items-center justify-center text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading signals…
              </div>
            )}

            {view === 'list' && rows !== null && filtered.length === 0 && !error && (
              <div className="card p-12 text-center text-slate-400">
                No signals match. Loosen filters or lower the deal-meter threshold.
              </div>
            )}

            {view === 'list' && filtered.map(({ row: p, score }) => (
              <div
                key={p.parcel_key}
                onMouseEnter={() => setHoveredKey(p.parcel_key)}
                onMouseLeave={() => setHoveredKey((k) => (k === p.parcel_key ? null : k))}
                className={`card p-5 hover:border-brand-400 hover:shadow-brand transition-all relative ${
                  selected.has(p.parcel_key) ? 'ring-2 ring-brand-300 border-brand-400' : ''
                } ${hoveredKey === p.parcel_key ? 'border-brand-500 shadow-brand' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={selected.has(p.parcel_key)}
                  onChange={(e) => {
                    e.stopPropagation();
                    setSelected((prev) => {
                      const next = new Set(prev);
                      if (next.has(p.parcel_key)) next.delete(p.parcel_key);
                      else next.add(p.parcel_key);
                      return next;
                    });
                  }}
                  className="absolute top-4 right-4 w-4 h-4 accent-brand-500 z-10"
                  aria-label="Select for bulk action"
                  onClick={(e) => e.stopPropagation()}
                />
                <Link
                  to={`/property/${encodeURIComponent(p.parcel_key)}`}
                  className="flex items-start justify-between gap-4 -m-5 p-5"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <DealMeter score={score} />
                      <span className={`pill bg-slate-100 ${bandTextColor(score.band)} border border-slate-200 uppercase text-[10px]`}>
                        {score.band}
                      </span>
                      {p.years_delinquent && (
                        <span className="text-xs font-semibold text-slate-500">
                          {p.years_delinquent}y delinquent
                        </span>
                      )}
                      {p.owner_state && p.owner_state !== p.state && (
                        <span className="text-xs font-semibold text-slate-500">
                          owner in {p.owner_state}
                        </span>
                      )}
                      {p.owner_name && (
                        <span className="text-xs font-semibold text-slate-500 truncate max-w-[160px]">
                          {p.owner_name}
                        </span>
                      )}
                    </div>
                    <div className="mt-2 font-display font-bold text-slate-900 truncate">
                      {p.address.replace(/^\d+\s/, '••• ')}
                    </div>
                    <div className="text-sm text-slate-500 inline-flex items-center gap-1">
                      <MapPin className="w-3 h-3" />{' '}
                      {[p.city, p.state, p.zip].filter(Boolean).join(', ')}
                      {p.county && ` · ${p.county} County`}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {p.source_tags.map((t) => (
                        <span key={t} className="pill bg-brand-50 text-brand-700 border border-brand-100">
                          {SOURCE_LABELS[t]}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="text-right shrink-0 text-xs">
                    {/* Big score circle */}
                    <div className="mb-3 flex items-center justify-end">
                      <ScoreBadge total={score.total} band={score.band} />
                    </div>
                    {p.default_amount && (
                      <Stat label="Default" v={`$${p.default_amount.toLocaleString()}`} />
                    )}
                    {p.lien_amount && (
                      <Stat label="Lien" v={`$${p.lien_amount.toLocaleString()}`} />
                    )}
                    {p.asking_price && (
                      <Stat label="Asking" v={`$${p.asking_price.toLocaleString()}`} />
                    )}
                    {p.sale_date && (
                      <Stat label="Sale date" v={new Date(p.sale_date).toLocaleDateString()} />
                    )}
                  </div>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sticky bulk-action bar */}
      {selected.size > 0 && (
        <div className="fixed bottom-0 inset-x-0 z-30 bg-white/95 backdrop-blur border-t border-slate-200 shadow-lg pb-[env(safe-area-inset-bottom)]">
          <div className="container-page py-3 flex items-center justify-between gap-3 flex-wrap">
            <div className="text-sm">
              <strong className="text-brand-navy">{selected.size}</strong>{' '}
              <span className="text-slate-600">selected</span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setSelected(new Set())} className="btn-outline text-sm">
                <X className="w-4 h-4" /> Clear
              </button>
              <button
                onClick={() => {
                  const keys = Array.from(selected).join(',');
                  nav(`/mailers?parcels=${encodeURIComponent(keys)}`);
                }}
                className="btn-primary text-sm"
              >
                <Send className="w-4 h-4" /> Send mailer to {selected.size}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Stat({ label, v }: { label: string; v: string }) {
  return (
    <div className="mb-1.5">
      <div className="text-slate-400">{label}</div>
      <div className="font-display font-bold text-slate-900 text-sm">{v}</div>
    </div>
  );
}

function ScoreBadge({ total, band }: { total: number; band: 'cold' | 'warming' | 'warm' | 'hot' | 'top' }) {
  const hex = bandHex(band);
  return (
    <div className="relative w-14 h-14">
      <svg viewBox="0 0 36 36" className="absolute inset-0 -rotate-90">
        <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgb(241,245,249)" strokeWidth="3" />
        <circle
          cx="18"
          cy="18"
          r="15.9"
          fill="none"
          strokeWidth="3"
          strokeLinecap="round"
          stroke={hex}
          style={{
            strokeDasharray: `${(total / 100) * 100} 100`,
            transition: 'stroke-dasharray 300ms',
          }}
        />
      </svg>
      <div className={`absolute inset-0 flex items-center justify-center font-display font-extrabold text-base ${bandTextColor(band)}`}>
        {total}
      </div>
    </div>
  );
}

/** Compact card used inside the split-view list. Hover-syncs with the map. */
function SplitCard({
  row: p,
  score,
  hoveredKey,
  selected,
  setSelected,
  onHover,
}: {
  row: OffMarketRow;
  score: ReturnType<typeof dealScore>;
  hoveredKey: string | null;
  selected: Set<string>;
  setSelected: React.Dispatch<React.SetStateAction<Set<string>>>;
  onHover: (k: string | null) => void;
}) {
  const isHovered = hoveredKey === p.parcel_key;
  return (
    <div
      onMouseEnter={() => onHover(p.parcel_key)}
      onMouseLeave={() => onHover(null)}
      className={`card p-3 transition-all relative scroll-mt-20 ${
        selected.has(p.parcel_key) ? 'ring-2 ring-brand-300 border-brand-400' : ''
      } ${isHovered ? 'border-brand-500 shadow-brand' : 'hover:border-brand-300'}`}
      data-parcel-key={p.parcel_key}
    >
      <input
        type="checkbox"
        checked={selected.has(p.parcel_key)}
        onChange={(e) => {
          e.stopPropagation();
          setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(p.parcel_key)) next.delete(p.parcel_key);
            else next.add(p.parcel_key);
            return next;
          });
        }}
        className="absolute top-3 right-3 w-4 h-4 accent-brand-500 z-10"
        aria-label="Select for bulk action"
        onClick={(e) => e.stopPropagation()}
      />
      <Link
        to={`/property/${encodeURIComponent(p.parcel_key)}`}
        className="flex items-center gap-3"
      >
        <div className="shrink-0">
          <ScoreBadge total={score.total} band={score.band} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className={`pill text-[10px] uppercase tracking-wider ${bandTextColor(score.band)} bg-slate-100 border border-slate-200`}>
              {score.band}
            </span>
            {p.owner_state && p.owner_state !== p.state && (
              <span className="text-[10px] text-slate-500">owner {p.owner_state}</span>
            )}
          </div>
          <div className="mt-1 font-display font-bold text-sm text-slate-900 truncate">
            {p.address.replace(/^\d+\s/, '••• ')}
          </div>
          <div className="text-[11px] text-slate-500 truncate">
            {[p.city, p.state, p.zip].filter(Boolean).join(', ')}
          </div>
        </div>
      </Link>
    </div>
  );
}
