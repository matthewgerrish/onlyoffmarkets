import { useEffect, useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Bookmark, Trash2, Send, Loader2, Search as SearchIcon,
  MapPin, Target, Building2, Calendar,
} from 'lucide-react';
import Seo from '../components/Seo';
import { useToast } from '../components/Toast';
import { useAuth } from '../components/AuthContext';
import { listWatchlist, removeFromWatchlist, WatchlistItem } from '../lib/watchlist';

type Sort = 'recent' | 'score' | 'adu' | 'address';

export default function Watchlist() {
  const [items, setItems] = useState<WatchlistItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState<Sort>('recent');
  const [removing, setRemoving] = useState<string | null>(null);
  const toast = useToast();
  const { isAuthed, openLogin } = useAuth();
  const nav = useNavigate();

  useEffect(() => {
    listWatchlist()
      .then(setItems)
      .catch((e) => setError(e.message));
  }, []);

  const filtered = useMemo(() => {
    if (!items) return null;
    let out = items.slice();
    if (filter.trim()) {
      const q = filter.toLowerCase();
      out = out.filter(
        (x) => x.address.toLowerCase().includes(q) ||
               (x.city || '').toLowerCase().includes(q) ||
               (x.state || '').toLowerCase().includes(q),
      );
    }
    out.sort((a, b) => {
      switch (sort) {
        case 'score':   return (b.deal_score ?? 0) - (a.deal_score ?? 0);
        case 'adu':     return (b.adu_score  ?? 0) - (a.adu_score  ?? 0);
        case 'address': return a.address.localeCompare(b.address);
        case 'recent':
        default:        return (b.saved_at || '').localeCompare(a.saved_at || '');
      }
    });
    return out;
  }, [items, filter, sort]);

  const onRemove = async (key: string) => {
    setRemoving(key);
    try {
      await removeFromWatchlist(key);
      setItems((prev) => prev?.filter((x) => x.parcel_key !== key) || null);
      toast.info('Removed from watchlist');
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setRemoving(null);
    }
  };

  return (
    <>
      <Seo title="Watchlist · OnlyOffMarkets" />

      {/* Banner */}
      <section className="relative bg-gradient-to-br from-brand-50 via-white to-amber-50 border-b border-slate-100">
        <div className="container-page py-10 flex items-end justify-between gap-6 flex-wrap">
          <div>
            <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">
              Your pipeline
            </p>
            <h1 className="mt-1 font-display text-4xl font-extrabold text-brand-navy inline-flex items-center gap-3">
              <Bookmark className="w-7 h-7 text-amber-500" /> Watchlist
            </h1>
            <p className="mt-2 text-slate-600 max-w-xl">
              Every Recon you save lands here. Re-score, take notes, and queue
              postcards in one click.
            </p>
          </div>
          {items && items.length > 0 && (
            <div className="text-sm text-slate-500">
              <strong className="text-brand-navy">{items.length}</strong> saved
            </div>
          )}
        </div>
      </section>

      <section className="container-page py-8">
        {/* Auth gate */}
        {!isAuthed && (
          <div className="card p-6 mb-6 bg-amber-50 border-amber-200 text-amber-800 flex items-start gap-3">
            <Bookmark className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <div className="font-display font-bold text-amber-900">
                Sign in to keep your watchlist on every device
              </div>
              <div className="text-sm mt-0.5">
                You can save anonymously now (tied to this browser), but signing
                in moves your list to your email so you don't lose it.
              </div>
              <button onClick={openLogin} className="btn-primary mt-3 text-xs !py-2">
                Sign in
              </button>
            </div>
          </div>
        )}

        {/* Filters */}
        {items && items.length > 0 && (
          <div className="flex gap-2 flex-wrap items-center mb-5">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <SearchIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter by address or city…"
                className="input pl-9 w-full"
              />
            </div>
            <div className="inline-flex bg-slate-100 rounded-full p-0.5 text-xs font-semibold">
              {([
                { v: 'recent',  l: 'Recent' },
                { v: 'score',   l: 'Score' },
                { v: 'adu',     l: 'ADU' },
                { v: 'address', l: 'A–Z' },
              ] as const).map((s) => (
                <button
                  key={s.v}
                  onClick={() => setSort(s.v as Sort)}
                  className={`px-3 py-1 rounded-full ${
                    sort === s.v ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500'
                  }`}
                >
                  {s.l}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Loading */}
        {items === null && !error && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="card p-5 animate-fade-in"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="skeleton w-12 h-12 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <div className="skeleton h-3.5 w-3/4" />
                    <div className="skeleton h-3 w-1/2" />
                  </div>
                </div>
                <div className="skeleton h-3 w-full" />
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="card p-4 text-sm text-rose-700 bg-rose-50 border-rose-200">
            {error}
          </div>
        )}

        {/* Empty */}
        {items && items.length === 0 && !error && (
          <div className="card p-12 text-center relative overflow-hidden">
            <div className="absolute inset-x-0 top-0 h-32 bg-[radial-gradient(ellipse_at_top,rgba(29,108,242,0.10),transparent_70%)] pointer-events-none" />
            <div className="relative">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-amber-50 text-amber-500 mb-4 animate-pop-in">
                <Bookmark className="w-6 h-6" />
              </div>
              <h3 className="font-display text-xl font-extrabold text-brand-navy">
                Nothing on watch yet
              </h3>
              <p className="mt-2 text-sm text-slate-500 max-w-md mx-auto">
                Run a Recon, hit <strong className="text-slate-700">Save</strong>,
                and your pipeline starts here. Sortable, exportable, mailer-ready.
              </p>
              <Link to="/analyzer" className="btn-primary mt-5">
                <Target className="w-4 h-4" /> Run your first Recon
              </Link>
            </div>
          </div>
        )}

        {/* Cards */}
        {filtered && filtered.length > 0 && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((it, i) => (
              <WatchlistCard
                key={it.parcel_key}
                item={it}
                index={i}
                removing={removing === it.parcel_key}
                onRemove={() => onRemove(it.parcel_key)}
                onMail={() => nav(`/mailers?parcels=${encodeURIComponent(it.parcel_key)}`)}
                onRecon={() => nav(`/analyzer?address=${encodeURIComponent(it.address)}`)}
              />
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function WatchlistCard({
  item, index, removing, onRemove, onMail, onRecon,
}: {
  item: WatchlistItem; index: number; removing: boolean;
  onRemove: () => void; onMail: () => void; onRecon: () => void;
}) {
  const dHex = bandHex(item.deal_band);
  const aHex = aduHex(item.adu_band);
  return (
    <div
      className="card card-hover p-5 flex flex-col animate-fade-in-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start gap-3">
        {/* Mini deal score badge */}
        <div className="relative w-12 h-12 shrink-0">
          <svg viewBox="0 0 36 36" className="absolute inset-0 -rotate-90">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgb(241,245,249)" strokeWidth="3" />
            <circle
              cx="18" cy="18" r="15.9" fill="none" strokeWidth="3" strokeLinecap="round"
              stroke={dHex}
              style={{ strokeDasharray: `${item.deal_score ?? 0} 100` }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center font-display font-extrabold text-sm" style={{ color: dHex }}>
            {item.deal_score ?? '—'}
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <div className="font-display font-bold text-slate-900 truncate" title={item.address}>
            {item.address}
          </div>
          <div className="text-xs text-slate-500 truncate inline-flex items-center gap-1 mt-0.5">
            <MapPin className="w-3 h-3" />
            {[item.city, item.state, item.zip].filter(Boolean).join(', ') || 'Location TBD'}
          </div>
          <div className="mt-2 flex items-center gap-1.5 flex-wrap">
            {item.deal_band && (
              <span className="pill text-[10px] uppercase tracking-wider font-bold"
                style={{ color: dHex, backgroundColor: dHex + '15', borderColor: dHex + '40', borderWidth: 1 }}>
                {item.deal_band}
              </span>
            )}
            {item.adu_band && item.adu_score && item.adu_score > 0 && (
              <span className="inline-flex items-center gap-1 pill text-[10px] uppercase tracking-wider font-bold"
                style={{ color: aHex, backgroundColor: aHex + '15', borderColor: aHex + '40', borderWidth: 1 }}>
                <Building2 className="w-3 h-3" /> ADU {item.adu_score}
              </span>
            )}
          </div>
        </div>
      </div>

      {item.notes && (
        <div className="mt-3 text-xs text-slate-600 italic bg-slate-50 rounded-lg px-2.5 py-1.5 border border-slate-100">
          {item.notes}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between gap-2 pt-3 border-t border-slate-100">
        <div className="text-[10px] text-slate-400 inline-flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          {item.saved_at ? new Date(item.saved_at).toLocaleDateString() : '—'}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onRecon}
            title="Re-Recon"
            className="inline-flex items-center justify-center w-7 h-7 rounded-full text-slate-500 hover:text-brand-600 hover:bg-brand-50"
          >
            <Target className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onMail}
            title="Send mailer"
            className="inline-flex items-center justify-center w-7 h-7 rounded-full text-slate-500 hover:text-brand-600 hover:bg-brand-50"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onRemove}
            disabled={removing}
            title="Remove"
            className="inline-flex items-center justify-center w-7 h-7 rounded-full text-slate-400 hover:text-rose-600 hover:bg-rose-50 disabled:opacity-40"
          >
            {removing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>
    </div>
  );
}

function bandHex(b: string | null): string {
  switch (b) {
    case 'top':     return '#f43f5e';
    case 'hot':     return '#f97316';
    case 'warm':    return '#f59e0b';
    case 'warming': return '#eab308';
    default:        return '#1d6cf2';
  }
}
function aduHex(b: string | null): string {
  switch (b) {
    case 'excellent': return '#10b981';
    case 'good':      return '#22c55e';
    case 'limited':   return '#eab308';
    default:          return '#94a3b8';
  }
}
