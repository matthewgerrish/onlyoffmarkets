import { useEffect, useMemo, useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  MapPin, Filter, Lock, Loader2, Flame, Send, X,
  ChevronRight,
} from 'lucide-react';
import Seo from '../components/Seo';
import SearchMap from '../components/SearchMap';
import SmartSearch from '../components/SmartSearch';
import BrowseStates from '../components/BrowseStates';
import PropertyTypePicker from '../components/PropertyTypePicker';
import PriceRange from '../components/PriceRange';
import {
  listOffMarket, getPins, getCoverage,
  OffMarketRow, ApiSource, Pin, PropertyType, CoverageSummary,
} from '../lib/api';
import { SOURCE_LABELS, ALL_SOURCES } from '../lib/sources';
import { dealScore, bandHex, bandTextColor, DealScore } from '../lib/score';

type SortMode = 'score' | 'newest';

export default function Search() {
  const [rows, setRows] = useState<OffMarketRow[] | null>(null);
  const [pins, setPins] = useState<Pin[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);

  const [state, setState] = useState<string>('');
  const [propertyType, setPropertyType] = useState<PropertyType | ''>('');
  const [priceRange, setPriceRange] = useState<{ min: number | null; max: number | null }>({ min: null, max: null });
  const [enabledSources, setEnabledSources] = useState<Set<ApiSource>>(new Set(ALL_SOURCES));
  const [minScore, setMinScore] = useState<number>(0);
  const [coverage, setCoverage] = useState<CoverageSummary | null>(null);
  const [sortMode, setSortMode] = useState<SortMode>('score');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [addressQuery, setAddressQuery] = useState('');

  // map bounds (driven by SearchMap onMove)
  const [bounds, setBounds] = useState<[number, number, number, number] | null>(null);
  const [filterToBounds, setFilterToBounds] = useState(true);

  const nav = useNavigate();

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    setError(null);
    listOffMarket({
      state: state || undefined,
      property_type: propertyType || undefined,
      min_value: priceRange.min ?? undefined,
      max_value: priceRange.max ?? undefined,
      limit: 300,
    })
      .then((data) => {
        if (cancelled) return;
        setRows(data.results);
        setCounts(data.counts);
      })
      .catch((e: Error) => !cancelled && setError(e.message));
    // Fetch all pins separately so the map shows every state we cover
    getPins({
      state: state || undefined,
      property_type: propertyType || undefined,
      min_value: priceRange.min ?? undefined,
      max_value: priceRange.max ?? undefined,
    })
      .then((d) => !cancelled && setPins(d.pins))
      .catch(() => {});
    return () => { cancelled = true; };
  }, [state, propertyType, priceRange.min, priceRange.max]);

  // Fetch coverage once for filter counts + browse states
  useEffect(() => {
    getCoverage().then(setCoverage).catch(() => {});
  }, []);

  const scored = useMemo(() => {
    if (!rows) return null;
    return rows.map((r) => ({ row: r, score: dealScore(r) }));
  }, [rows]);

  // Filtered by score + sources (always)
  const filtered = useMemo(() => {
    if (!scored) return [];
    let out = scored.filter(({ row, score }) => {
      if (score.total < minScore) return false;
      if (!row.source_tags.some((t) => enabledSources.has(t))) return false;
      return true;
    });
    if (sortMode === 'score') out = [...out].sort((a, b) => b.score.total - a.score.total);
    else out = [...out].sort((a, b) => new Date(b.row.last_seen).getTime() - new Date(a.row.last_seen).getTime());
    return out;
  }, [scored, enabledSources, minScore, sortMode]);

  // Further restrict to map viewport when toggle on
  const inViewport = useMemo(() => {
    if (!filterToBounds || !bounds) return filtered;
    const [w, s, e, n] = bounds;
    return filtered.filter(({ row }) => {
      if (typeof row.latitude !== 'number' || typeof row.longitude !== 'number') return false;
      return row.longitude >= w && row.longitude <= e && row.latitude >= s && row.latitude <= n;
    });
  }, [filtered, bounds, filterToBounds]);

  // Pins for the map: every parcel with coordinates, filtered by score + sources
  const pinsAsRows = useMemo<OffMarketRow[]>(() => {
    return pins
      .filter((p) => p.source_tags.some((t) => enabledSources.has(t)))
      .map<OffMarketRow>((p) => ({
        parcel_key: p.parcel_key,
        parcel_apn: null,
        address: '',
        city: null,
        county: null,
        state: p.state ?? '',
        zip: null,
        source_tags: p.source_tags,
        default_amount: p.default_amount,
        sale_date: p.sale_date,
        asking_price: p.asking_price,
        lien_amount: p.lien_amount,
        years_delinquent: p.years_delinquent,
        vacancy_months: p.vacancy_months,
        owner_state: p.owner_state,
        owner_name: null,
        latitude: p.latitude,
        longitude: p.longitude,
        estimated_value: p.estimated_value,
        assessed_value: p.assessed_value,
        loan_balance: p.loan_balance,
        property_type: p.property_type,
        estimated_equity: null,
        spread_pct: null,
        adu_ready: 0,
        adu_score: 0,
        first_seen: p.last_seen,
        last_seen: p.last_seen,
      }))
      .filter((r) => {
        const score = dealScore(r);
        return score.total >= minScore;
      });
  }, [pins, enabledSources, minScore]);

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

  // Hover scroll into view
  const listScrollerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!hoveredKey) return;
    const el = listScrollerRef.current?.querySelector<HTMLElement>(`[data-parcel-key="${CSS.escape(hoveredKey)}"]`);
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const parent = listScrollerRef.current!.getBoundingClientRect();
    if (rect.top < parent.top || rect.bottom > parent.bottom) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [hoveredKey]);

  const filterChipsActive =
    (state ? 1 : 0) +
    (minScore > 0 ? 1 : 0) +
    (enabledSources.size < ALL_SOURCES.length ? 1 : 0) +
    (propertyType ? 1 : 0) +
    ((priceRange.min !== null || priceRange.max !== null) ? 1 : 0);

  return (
    <>
      <Seo title="Search off-market signals" />
      <div className="grid lg:grid-cols-[1fr_400px] xl:grid-cols-[1fr_440px] h-[calc(100vh-64px)]">
        {/* Map column */}
        <div className="relative bg-slate-100 min-h-[400px]">
          <SearchMap
            rows={pinsAsRows}
            hoveredKey={hoveredKey}
            onPinHover={setHoveredKey}
            onPinClick={(k) => nav(`/property/${encodeURIComponent(k)}`)}
            onBoundsChange={setBounds}
            height="100%"
            flyToQuery={addressQuery}
            inset
          />

          {/* Floating smart-search top-left */}
          <div className="absolute top-3 left-3 z-10">
            <SmartSearch
              onSelect={(sel) => {
                if (sel.state !== undefined) setState(sel.state || '');
                if (sel.query) setAddressQuery(sel.query);
                else if (sel.zip) setAddressQuery(sel.zip);
                else if (sel.city) setAddressQuery(sel.city);
              }}
            />
          </div>

          {/* Filter chips bar top-center */}
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 hidden md:flex">
            <button
              onClick={() => setFiltersOpen(true)}
              className="bg-white shadow-md border border-slate-200 rounded-full px-3 py-2 text-xs font-semibold text-slate-700 inline-flex items-center gap-2 hover:bg-slate-50"
            >
              <Filter className="w-3.5 h-3.5" /> Filters
              {filterChipsActive > 0 && (
                <span className="bg-brand-500 text-white text-[10px] rounded-full w-5 h-5 inline-flex items-center justify-center">
                  {filterChipsActive}
                </span>
              )}
            </button>
            <label className="bg-white shadow-md border border-slate-200 rounded-full px-3 py-2 text-xs font-semibold text-slate-700 inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={filterToBounds}
                onChange={(e) => setFilterToBounds(e.target.checked)}
                className="accent-brand-500"
              />
              Filter to map area
            </label>
          </div>
        </div>

        {/* Listings column (right) */}
        <aside className="bg-white border-l border-slate-100 flex flex-col h-full overflow-hidden">
          <BrowseStates selected={state} onSelect={setState} />
          <div className="px-4 py-2 border-b border-slate-100">
            <PropertyTypePicker
              value={propertyType}
              onChange={setPropertyType}
              counts={coverage?.by_property_type}
            />
          </div>
          <div className="px-5 py-3 border-b border-slate-100 flex items-end justify-between gap-3">
            <div>
              <h1 className="font-display text-xl font-extrabold text-brand-navy leading-tight">
                Listings in this area
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                {rows === null
                  ? 'Loading…'
                  : `${inViewport.length} of ${pinsAsRows.length} mapped`}
              </p>
            </div>
            <div className="flex bg-slate-100 rounded-full p-0.5 text-[11px] font-semibold">
              <button
                onClick={() => setSortMode('score')}
                className={`px-2.5 py-1 rounded-full ${
                  sortMode === 'score' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500'
                }`}
              >
                Hottest
              </button>
              <button
                onClick={() => setSortMode('newest')}
                className={`px-2.5 py-1 rounded-full ${
                  sortMode === 'newest' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500'
                }`}
              >
                Newest
              </button>
            </div>
          </div>

          <div ref={listScrollerRef} className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {error && (
              <div className="card p-4 text-xs text-rose-600 border-rose-200 bg-rose-50">
                {error}
                <div className="mt-1 text-rose-500">Is the API up?</div>
              </div>
            )}
            {rows === null && !error && (
              <div className="card p-10 flex items-center justify-center text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading…
              </div>
            )}
            {rows !== null && inViewport.length === 0 && !error && (
              <div className="card p-8 text-center text-sm text-slate-500">
                <MapPin className="w-5 h-5 mx-auto mb-2 text-slate-400" />
                {filterToBounds
                  ? 'No properties in current map area. Pan or zoom out.'
                  : 'No signals match your filters.'}
              </div>
            )}
            {inViewport.map(({ row: p, score }) => (
              <ListingCard
                key={p.parcel_key}
                row={p}
                score={score}
                isHovered={hoveredKey === p.parcel_key}
                isSelected={selected.has(p.parcel_key)}
                onHover={setHoveredKey}
                onToggleSelect={() => {
                  setSelected((prev) => {
                    const next = new Set(prev);
                    if (next.has(p.parcel_key)) next.delete(p.parcel_key);
                    else next.add(p.parcel_key);
                    return next;
                  });
                }}
              />
            ))}
          </div>

          <div className="px-4 py-2 border-t border-slate-100 text-[11px] text-slate-500 inline-flex items-center gap-1.5">
            <Lock className="w-3 h-3" /> Free preview — sign in for full addresses
          </div>
        </aside>
      </div>

      {/* Filters drawer */}
      {filtersOpen && (
        <FiltersDrawer
          state={state}
          setState={setState}
          minScore={minScore}
          setMinScore={setMinScore}
          priceRange={priceRange}
          setPriceRange={setPriceRange}
          enabledSources={enabledSources}
          toggleSource={toggleSource}
          counts={counts}
          states={states}
          onClose={() => setFiltersOpen(false)}
          onClearAll={() => {
            setState('');
            setMinScore(0);
            setPriceRange({ min: null, max: null });
            setEnabledSources(new Set(ALL_SOURCES));
          }}
        />
      )}

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

function ListingCard({
  row: p,
  score,
  isHovered,
  isSelected,
  onHover,
  onToggleSelect,
}: {
  row: OffMarketRow;
  score: DealScore;
  isHovered: boolean;
  isSelected: boolean;
  onHover: (k: string | null) => void;
  onToggleSelect: () => void;
}) {
  return (
    <div
      data-parcel-key={p.parcel_key}
      onMouseEnter={() => onHover(p.parcel_key)}
      onMouseLeave={() => onHover(null)}
      className={`card p-3 transition-all relative scroll-mt-2 cursor-pointer ${
        isSelected ? 'ring-2 ring-brand-300 border-brand-400' : ''
      } ${isHovered ? 'border-brand-500 shadow-brand' : 'hover:border-brand-300'}`}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={(e) => {
          e.stopPropagation();
          onToggleSelect();
        }}
        onClick={(e) => e.stopPropagation()}
        className="absolute top-3 right-3 w-4 h-4 accent-brand-500 z-10"
        aria-label="Select for bulk action"
      />
      <Link to={`/property/${encodeURIComponent(p.parcel_key)}`} className="flex items-center gap-3">
        <ScoreBadge total={score.total} band={score.band} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span
              className={`pill text-[10px] uppercase tracking-wider ${bandTextColor(
                score.band
              )} bg-slate-100 border border-slate-200`}
            >
              {score.band}
            </span>
            {p.owner_state && p.owner_state !== p.state && (
              <span className="text-[10px] text-slate-500">owner {p.owner_state}</span>
            )}
            {p.years_delinquent && (
              <span className="text-[10px] text-slate-500">{p.years_delinquent}y delinq</span>
            )}
          </div>
          <div className="mt-1 font-display font-bold text-sm text-slate-900 truncate">
            {p.address.replace(/^\d+\s/, '••• ')}
          </div>
          <div className="text-[11px] text-slate-500 truncate">
            {[p.city, p.state, p.zip].filter(Boolean).join(', ')}
          </div>
          {(p.default_amount || p.lien_amount || p.asking_price) && (
            <div className="mt-1 text-[11px] font-semibold text-slate-700">
              {p.default_amount && <span>Default ${p.default_amount.toLocaleString()}</span>}
              {p.lien_amount && <span>Lien ${p.lien_amount.toLocaleString()}</span>}
              {p.asking_price && <span>Asking ${p.asking_price.toLocaleString()}</span>}
            </div>
          )}
        </div>
        <ChevronRight className="w-4 h-4 text-slate-300 shrink-0" />
      </Link>
    </div>
  );
}

function ScoreBadge({ total, band }: { total: number; band: DealScore['band'] }) {
  const hex = bandHex(band);
  return (
    <div className="relative w-12 h-12 shrink-0">
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
          style={{ strokeDasharray: `${total} 100`, transition: 'stroke-dasharray 300ms' }}
        />
      </svg>
      <div className={`absolute inset-0 flex items-center justify-center font-display font-extrabold text-sm ${bandTextColor(band)}`}>
        {total}
      </div>
    </div>
  );
}

/* ---------- Filters drawer (slides in from the right of the listings column) ---------- */

function FiltersDrawer({
  state,
  setState,
  minScore,
  setMinScore,
  priceRange,
  setPriceRange,
  enabledSources,
  toggleSource,
  counts,
  states,
  onClose,
  onClearAll,
}: {
  state: string;
  setState: (s: string) => void;
  minScore: number;
  setMinScore: (n: number) => void;
  priceRange: { min: number | null; max: number | null };
  setPriceRange: (v: { min: number | null; max: number | null }) => void;
  enabledSources: Set<ApiSource>;
  toggleSource: (s: ApiSource) => void;
  counts: Record<string, number>;
  states: string[];
  onClose: () => void;
  onClearAll: () => void;
}) {
  return (
    <div className="fixed inset-0 z-40 flex" onClick={onClose}>
      <div className="flex-1 bg-slate-900/30 backdrop-blur-sm" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-white border-l border-slate-200 shadow-2xl h-full overflow-y-auto"
      >
        <div className="sticky top-0 z-10 bg-white border-b border-slate-100 px-5 py-3 flex items-center justify-between">
          <h2 className="font-display font-bold text-slate-900 inline-flex items-center gap-2">
            <Filter className="w-4 h-4 text-brand-500" /> Filters
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div className="p-3 -mx-1 rounded-xl bg-gradient-to-br from-brand-50 via-white to-orange-50 border border-slate-100">
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
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
              <span>cold</span>
              <span>warm</span>
              <span>hot</span>
              <span>top</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">State</label>
            <select className="input w-full" value={state} onChange={(e) => setState(e.target.value)}>
              <option value="">All states</option>
              {states.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-2">Price range</label>
            <PriceRange value={priceRange} onChange={setPriceRange} />
            <p className="text-[11px] text-slate-500 mt-2">
              Best price per parcel — asking price preferred, else AVM, else assessed value.
            </p>
          </div>

          <div>
            <div className="text-xs font-semibold text-slate-600 mb-2">Sources</div>
            <div className="flex flex-col gap-2">
              {ALL_SOURCES.map((s) => (
                <label
                  key={s}
                  className="flex items-center justify-between gap-2 text-sm text-slate-700 cursor-pointer"
                >
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
          </div>
        </div>

        <div className="sticky bottom-0 bg-white border-t border-slate-100 px-5 py-3 flex justify-between gap-2">
          <button onClick={onClearAll} className="btn-outline text-sm">Clear all</button>
          <button onClick={onClose} className="btn-primary text-sm">Apply</button>
        </div>
      </div>
    </div>
  );
}
