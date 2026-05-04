import { useEffect, useRef, useState } from 'react';
import { Search, MapPin, Clock, Loader2, ArrowUpRight } from 'lucide-react';

interface MapboxFeature {
  id: string;
  place_name: string;
  text: string;
  center: [number, number];
  place_type: string[];
  context?: Array<{ id: string; text: string; short_code?: string }>;
}

interface Props {
  /** Controlled input value. */
  value: string;
  onChange: (v: string) => void;
  /** Fired when user picks a suggestion or hits Enter. */
  onSelect: (place: string) => void;
  /** Disable the submit button (e.g. while analyzing). */
  busy?: boolean;
  /** Placeholder text. */
  placeholder?: string;
}

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined;
const RECENT_KEY = 'oom_recent_addresses_v1';
const RECENT_LIMIT = 6;

/** Live address autocomplete with recent-search history.
 *  Falls back to a plain input if VITE_MAPBOX_TOKEN isn't set — the
 *  experience degrades but never breaks. */
export default function AddressAutocomplete({
  value, onChange, onSelect, busy, placeholder,
}: Props) {
  const [features, setFeatures] = useState<MapboxFeature[]>([]);
  const [recents, setRecents] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(-1);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<number | null>(null);

  // Hydrate recent searches
  useEffect(() => {
    try {
      const raw = localStorage.getItem(RECENT_KEY);
      if (raw) setRecents(JSON.parse(raw));
    } catch { /* noop */ }
  }, []);

  // Outside click → close
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [open]);

  // Debounced Mapbox query
  useEffect(() => {
    if (!MAPBOX_TOKEN) return;
    const q = value.trim();
    if (q.length < 4) {
      setFeatures([]);
      return;
    }
    setLoading(true);
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(async () => {
      try {
        const url = new URL(
          `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(q)}.json`,
        );
        url.searchParams.set('access_token', MAPBOX_TOKEN);
        url.searchParams.set('autocomplete', 'true');
        url.searchParams.set('country', 'us');
        url.searchParams.set('types', 'address,postcode,place');
        url.searchParams.set('limit', '6');
        const r = await fetch(url.toString());
        const data = await r.json();
        setFeatures((data.features || []) as MapboxFeature[]);
      } catch {
        setFeatures([]);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [value]);

  const commit = (text: string) => {
    if (!text.trim()) return;
    saveRecent(text);
    setRecents(loadRecents());
    setOpen(false);
    setHighlight(-1);
    onChange(text);
    onSelect(text);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open) return;
    const list = features.length ? features.map((f) => f.place_name) : recents;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, list.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, -1));
    } else if (e.key === 'Enter') {
      if (highlight >= 0 && list[highlight]) {
        e.preventDefault();
        commit(list[highlight]);
      }
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  const showRecents = !value.trim() && recents.length > 0;
  const showSuggestions = features.length > 0;
  const showDropdown = open && (showRecents || showSuggestions);

  return (
    <div ref={wrapRef} className="relative">
      <form
        onSubmit={(e) => { e.preventDefault(); commit(value); }}
      >
        <div className="relative">
          <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => { onChange(e.target.value); setOpen(true); setHighlight(-1); }}
            onFocus={() => setOpen(true)}
            onKeyDown={onKeyDown}
            placeholder={placeholder || '123 Main St, Seattle WA 98101'}
            autoComplete="off"
            spellCheck={false}
            className="w-full bg-white border border-slate-200 rounded-full pl-12 pr-32 py-4 text-base
              text-slate-900 placeholder:text-slate-400 shadow-brand
              focus:outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
          />
          <button
            type="submit"
            disabled={busy || !value.trim()}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 btn-primary !px-5 !py-2.5 text-sm disabled:opacity-50"
          >
            {busy ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Scanning…
              </>
            ) : (
              <>Recon →</>
            )}
          </button>
        </div>
      </form>

      {showDropdown && (
        <div className="absolute z-50 left-0 right-0 mt-2 bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-hidden animate-fade-in-down">
          {showSuggestions ? (
            <div className="py-1.5">
              <div className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 inline-flex items-center gap-1.5">
                <MapPin className="w-3 h-3" /> Suggestions
                {loading && <Loader2 className="w-3 h-3 animate-spin ml-1" />}
              </div>
              {features.map((f, i) => (
                <button
                  key={f.id}
                  type="button"
                  onMouseEnter={() => setHighlight(i)}
                  onMouseDown={(e) => { e.preventDefault(); commit(f.place_name); }}
                  className={`w-full flex items-start gap-3 px-4 py-2.5 text-left text-sm transition-colors ${
                    highlight === i ? 'bg-brand-50 text-brand-700' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <MapPin className="w-4 h-4 mt-0.5 shrink-0 text-slate-400" />
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold truncate">{f.text}</div>
                    <div className="text-xs text-slate-500 truncate">{f.place_name}</div>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-slate-300 shrink-0 mt-1" />
                </button>
              ))}
            </div>
          ) : showRecents ? (
            <div className="py-1.5">
              <div className="flex items-center justify-between px-4 py-1.5">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 inline-flex items-center gap-1.5">
                  <Clock className="w-3 h-3" /> Recent
                </div>
                <button
                  type="button"
                  onClick={() => { localStorage.removeItem(RECENT_KEY); setRecents([]); }}
                  className="text-[10px] text-slate-400 hover:text-rose-500"
                >
                  Clear
                </button>
              </div>
              {recents.map((r, i) => (
                <button
                  key={r + i}
                  type="button"
                  onMouseEnter={() => setHighlight(i)}
                  onMouseDown={(e) => { e.preventDefault(); commit(r); }}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors ${
                    highlight === i ? 'bg-brand-50 text-brand-700' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <Clock className="w-4 h-4 shrink-0 text-slate-400" />
                  <span className="truncate flex-1">{r}</span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                </button>
              ))}
            </div>
          ) : null}
        </div>
      )}

      {!MAPBOX_TOKEN && open && value.trim().length >= 3 && (
        <div className="mt-2 text-[11px] text-slate-400 px-2">
          Live suggestions disabled — set <code>VITE_MAPBOX_TOKEN</code> on Vercel to enable.
        </div>
      )}
    </div>
  );
}

function loadRecents(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveRecent(v: string) {
  try {
    const cur = loadRecents();
    const next = [v, ...cur.filter((x) => x !== v)].slice(0, RECENT_LIMIT);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch { /* noop */ }
}
