import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Filter, Lock, Loader2 } from 'lucide-react';
import Seo from '../components/Seo';
import SignalPill from '../components/SignalPill';
import { listOffMarket, OffMarketRow, ApiSource } from '../lib/api';
import { SOURCE_LABELS, ALL_SOURCES, tierFor } from '../lib/sources';

export default function Search() {
  const [rows, setRows] = useState<OffMarketRow[] | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);

  const [state, setState] = useState<string>('');
  const [enabledSources, setEnabledSources] = useState<Set<ApiSource>>(new Set(ALL_SOURCES));

  // Re-fetch from API whenever the state filter changes (server-side filter).
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

  // Source filter happens client-side on whatever the state-filtered set returned.
  const filtered = useMemo(() => {
    if (!rows) return [];
    return rows.filter((r) => r.source_tags.some((t) => enabledSources.has(t)));
  }, [rows, enabledSources]);

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
            <h1 className="font-display text-3xl font-extrabold text-slate-900">signal feed</h1>
            <p className="text-sm text-slate-500 mt-1">
              {rows === null
                ? 'Loading…'
                : `${filtered.length} of ${rows.length} properties match`}
            </p>
          </div>
          <div className="text-xs text-slate-500 inline-flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-full">
            <Lock className="w-3 h-3" /> Free preview — sign in for full addresses & contact data
          </div>
        </div>

        <div className="mt-6 grid lg:grid-cols-[300px_1fr] gap-6">
          <aside className="card p-5 h-fit lg:sticky lg:top-20">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-4">
              <Filter className="w-4 h-4 text-brand-500" /> Filters
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

          <div className="space-y-3">
            {error && (
              <div className="card p-6 text-sm text-rose-600 border-rose-200 bg-rose-50">
                Failed to load signals: {error}
                <div className="mt-2 text-xs text-rose-500">Is the API running on port 8001?</div>
              </div>
            )}

            {rows === null && !error && (
              <div className="card p-12 flex items-center justify-center text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading signals…
              </div>
            )}

            {rows !== null && filtered.length === 0 && !error && (
              <div className="card p-12 text-center text-slate-400">No signals match. Loosen your filters.</div>
            )}

            {filtered.map((p) => {
              const tier = tierFor(p.source_tags);
              return (
                <Link
                  key={p.parcel_key}
                  to={`/property/${encodeURIComponent(p.parcel_key)}`}
                  className="card p-5 block hover:border-brand-400 hover:shadow-brand transition-all"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <SignalPill tier={tier} />
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
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
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
