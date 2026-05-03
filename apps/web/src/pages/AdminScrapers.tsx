import { useEffect, useMemo, useState } from 'react';
import {
  Activity, Database, Lock, Play, RefreshCw, ShieldAlert, X,
  ChevronRight, Key, Loader2,
} from 'lucide-react';
import Seo from '../components/Seo';
import { useToast } from '../components/Toast';
import {
  getScraperHealth, getScraperHistory, runPipeline,
  getAdminToken, setAdminToken, clearAdminToken,
  ScraperHealthRow, ScraperRun,
} from '../lib/admin';

type Filter = 'all' | 'green' | 'yellow' | 'red' | 'never';

export default function AdminScrapers() {
  const [token, setToken] = useState<string>(getAdminToken() || '');
  const [tokenInput, setTokenInput] = useState('');
  const [rows, setRows] = useState<ScraperHealthRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState<string | null>(null);
  const [openHistory, setOpenHistory] = useState<ScraperRun[] | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const toast = useToast();

  const refresh = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const h = await getScraperHealth(14);
      setRows(h);
    } catch (e) {
      setError((e as Error).message);
      if ((e as Error).message.toLowerCase().includes('bad admin')) {
        clearAdminToken();
        setToken('');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Auto-poll every 30s while page is open + we're authed
  useEffect(() => {
    if (!token) return;
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const onSaveToken = (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) return;
    setAdminToken(tokenInput.trim());
    setToken(tokenInput.trim());
    setTokenInput('');
  };

  const onRun = async (slug?: string) => {
    setRunning(slug || 'all');
    try {
      await runPipeline(slug ? [slug] : undefined);
      toast.success(slug ? `Triggered ${slug}` : 'Triggered all scrapers');
      // Run is long; refresh in 5s to show pending state
      setTimeout(() => void refresh(), 5000);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setRunning(null);
    }
  };

  const onOpen = async (slug: string) => {
    setOpen(slug);
    setOpenHistory(null);
    try {
      const h = await getScraperHistory(slug, 30);
      setOpenHistory(h);
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  // Sort + filter
  const filtered = useMemo(() => {
    if (!rows) return null;
    const STATE_RANK = { red: 0, yellow: 1, never: 2, green: 3 };
    const out = rows.slice().sort(
      (a, b) => (STATE_RANK[a.state] ?? 9) - (STATE_RANK[b.state] ?? 9),
    );
    return out.filter((r) => {
      if (filter !== 'all' && r.state !== filter) return false;
      if (search && !r.slug.includes(search.toLowerCase()) && !r.source_class.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [rows, filter, search]);

  const counts = useMemo(() => {
    if (!rows) return null;
    return rows.reduce(
      (acc, r) => {
        acc[r.state] = (acc[r.state] || 0) + 1;
        acc.total += 1;
        acc.persisted += r.total_persisted;
        return acc;
      },
      { total: 0, persisted: 0 } as Record<string, number>,
    );
  }, [rows]);

  // Token gate
  if (!token) {
    return (
      <>
        <Seo title="Admin · Scrapers" />
        <section className="container-page py-20 max-w-md">
          <div className="card p-6">
            <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-brand-50 text-brand-500 mb-4">
              <Lock className="w-5 h-5" />
            </div>
            <h1 className="font-display text-xl font-extrabold text-brand-navy">Admin token required</h1>
            <p className="mt-2 text-sm text-slate-600">
              Paste the value of your <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">ADMIN_TOKEN</code>{' '}
              Fly secret. Stored locally in your browser.
            </p>
            <form onSubmit={onSaveToken} className="mt-4">
              <div className="relative">
                <Key className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="password"
                  autoFocus
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="Admin token"
                  className="w-full bg-white border border-slate-200 rounded-full pl-9 pr-4 py-2.5 text-sm
                    text-slate-900 placeholder:text-slate-400
                    focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
              </div>
              <button type="submit" className="btn-primary w-full justify-center mt-3">
                Sign in to admin
              </button>
            </form>
          </div>
        </section>
      </>
    );
  }

  return (
    <>
      <Seo title="Admin · Scrapers" />

      <section className="container-page py-8">
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">Pipeline</p>
            <h1 className="mt-1 font-display text-3xl font-extrabold text-brand-navy inline-flex items-center gap-2">
              <Activity className="w-6 h-6 text-brand-500" /> Scraper health
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Last 14 days. Click a row for run history.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => refresh()} className="btn-outline text-sm" disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              Refresh
            </button>
            <button onClick={() => onRun()} className="btn-primary text-sm" disabled={!!running}>
              {running === 'all' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Run all
            </button>
            <button
              onClick={() => { clearAdminToken(); setToken(''); }}
              className="btn-ghost text-xs text-slate-500"
            >
              <X className="w-3.5 h-3.5" /> Sign out admin
            </button>
          </div>
        </div>

        {counts && (
          <div className="mt-6 grid grid-cols-2 sm:grid-cols-5 gap-2">
            <Stat label="Registered" v={counts.total} accent="slate" />
            <Stat label="Persisted (14d)" v={counts.persisted} accent="brand" />
            <Stat label="Green" v={counts.green || 0} accent="emerald" />
            <Stat label="Yellow" v={counts.yellow || 0} accent="amber" />
            <Stat label="Red / Never" v={(counts.red || 0) + (counts.never || 0)} accent="rose" />
          </div>
        )}

        {error && (
          <div className="mt-4 card p-4 bg-rose-50 border-rose-200 text-rose-700 text-sm inline-flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        <div className="mt-6 flex gap-2 flex-wrap items-center">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter by slug or name…"
            className="input flex-1 min-w-[200px] max-w-xs"
          />
          <div className="inline-flex bg-slate-100 rounded-full p-0.5 text-xs font-semibold">
            {(['all', 'green', 'yellow', 'red', 'never'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-full capitalize ${
                  filter === f ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {filtered === null ? (
          <div className="mt-6 card p-10 text-center text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin mx-auto" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="mt-6 card p-10 text-center text-slate-400">
            No scrapers match. {filter !== 'all' && `(filter: ${filter})`}
          </div>
        ) : (
          <div className="mt-6 card overflow-x-auto">
            <table className="w-full text-sm min-w-[820px]">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left p-3">State</th>
                  <th className="text-left p-3">Slug</th>
                  <th className="text-left p-3">Source</th>
                  <th className="text-right p-3">Runs</th>
                  <th className="text-right p-3">Scraped</th>
                  <th className="text-right p-3">Persisted</th>
                  <th className="text-right p-3">Errors</th>
                  <th className="text-right p-3">Last run</th>
                  <th className="text-right p-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr
                    key={r.slug}
                    onClick={() => onOpen(r.slug)}
                    className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer"
                  >
                    <td className="p-3"><StateDot state={r.state} /></td>
                    <td className="p-3 font-mono text-xs text-slate-700">{r.slug}</td>
                    <td className="p-3">
                      <div className="text-slate-900">{r.source_class}</div>
                      {!r.registered && (
                        <div className="text-[10px] text-rose-500">deleted from registry</div>
                      )}
                    </td>
                    <td className="p-3 text-right tabular-nums">{r.runs}</td>
                    <td className="p-3 text-right tabular-nums text-slate-500">{r.total_scraped.toLocaleString()}</td>
                    <td className={`p-3 text-right tabular-nums font-bold ${r.total_persisted ? 'text-emerald-600' : 'text-slate-400'}`}>
                      {r.total_persisted.toLocaleString()}
                    </td>
                    <td className={`p-3 text-right tabular-nums ${r.total_errors ? 'text-rose-600' : 'text-slate-400'}`}>
                      {r.total_errors}
                    </td>
                    <td className="p-3 text-right text-xs text-slate-500 whitespace-nowrap">
                      {r.last_run ? formatHoursAgo(r.hours_since_run) : '—'}
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={(e) => { e.stopPropagation(); void onRun(r.slug); }}
                        disabled={!!running}
                        className="text-[11px] text-brand-600 hover:text-brand-700 font-semibold inline-flex items-center gap-1"
                      >
                        {running === r.slug ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Play className="w-3 h-3" />
                        )}
                        Run
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {open && (
        <HistoryDrawer
          slug={open}
          history={openHistory}
          onClose={() => { setOpen(null); setOpenHistory(null); }}
        />
      )}
    </>
  );
}

function StateDot({ state }: { state: string }) {
  const cfg: Record<string, { dot: string; label: string; bg: string; text: string }> = {
    green:  { dot: 'bg-emerald-500', label: 'Active',  bg: 'bg-emerald-50',  text: 'text-emerald-700' },
    yellow: { dot: 'bg-amber-500',   label: 'Empty',   bg: 'bg-amber-50',    text: 'text-amber-700'   },
    red:    { dot: 'bg-rose-500',    label: 'Stale',   bg: 'bg-rose-50',     text: 'text-rose-700'    },
    never:  { dot: 'bg-slate-400',   label: 'Never',   bg: 'bg-slate-100',   text: 'text-slate-600'   },
  };
  const c = cfg[state] || cfg.never;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}

function Stat({ label, v, accent }: { label: string; v: number; accent: 'slate' | 'brand' | 'emerald' | 'amber' | 'rose' }) {
  const cls = {
    slate: 'border-slate-200 bg-slate-50 text-slate-700',
    brand: 'border-brand-200 bg-brand-50 text-brand-700',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    rose: 'border-rose-200 bg-rose-50 text-rose-700',
  }[accent];
  return (
    <div className={`rounded-xl border px-3 py-2 ${cls}`}>
      <div className="text-[10px] uppercase font-bold tracking-wider opacity-70">{label}</div>
      <div className="font-display font-extrabold text-2xl tabular-nums">{v.toLocaleString()}</div>
    </div>
  );
}

function formatHoursAgo(h: number | null): string {
  if (h === null) return '—';
  if (h < 1) return `${Math.round(h * 60)}m ago`;
  if (h < 24) return `${Math.round(h)}h ago`;
  return `${Math.round(h / 24)}d ago`;
}

function HistoryDrawer({ slug, history, onClose }: { slug: string; history: ScraperRun[] | null; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex" onClick={onClose}>
      <div className="flex-1 bg-slate-900/30 backdrop-blur-sm animate-fade-in" />
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-xl bg-white border-l border-slate-200 shadow-2xl h-full overflow-y-auto animate-slide-in-right"
      >
        <div className="sticky top-0 z-10 bg-white border-b border-slate-100 px-5 py-3 flex items-center justify-between">
          <h2 className="font-display font-bold text-slate-900 inline-flex items-center gap-2">
            <Database className="w-4 h-4 text-brand-500" />
            <span className="font-mono text-sm">{slug}</span>
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-5">
          {history === null ? (
            <div className="text-center py-10 text-slate-400">
              <Loader2 className="w-5 h-5 animate-spin mx-auto" />
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-10 text-slate-400 text-sm">
              No runs yet. Click "Run" to trigger.
            </div>
          ) : (
            <ol className="space-y-2">
              {history.map((r) => (
                <li key={r.id} className="card p-3">
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <div className="flex items-center gap-2">
                      <StateDot state={
                        r.status === 'error' ? 'red'
                          : r.persisted === 0 ? 'yellow'
                          : 'green'
                      } />
                      <span className="text-xs text-slate-500 font-mono">
                        {r.started_at ? new Date(r.started_at).toLocaleString() : '—'}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 font-mono">
                      {r.elapsed_s != null ? `${r.elapsed_s.toFixed(1)}s` : '—'}
                    </div>
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <div className="text-[10px] text-slate-400 uppercase">Scraped</div>
                      <div className="font-bold text-slate-900 tabular-nums">{r.scraped}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-400 uppercase">Persisted</div>
                      <div className={`font-bold tabular-nums ${r.persisted ? 'text-emerald-600' : 'text-slate-400'}`}>
                        {r.persisted}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-400 uppercase">Errors</div>
                      <div className={`font-bold tabular-nums ${r.errors ? 'text-rose-600' : 'text-slate-400'}`}>
                        {r.errors}
                      </div>
                    </div>
                  </div>
                  {r.note && (
                    <div className="mt-2 text-[11px] text-rose-600 bg-rose-50 border border-rose-100 rounded px-2 py-1 font-mono break-all">
                      {r.note}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}

// Compact arrow used elsewhere in the codebase; importing keeps the
// bundle-tree honest even though we don't render it directly here.
void ChevronRight;
