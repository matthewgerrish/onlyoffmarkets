import { useEffect, useMemo, useRef, useState } from 'react';
import { Search as SearchIcon, X, MapPin, ChevronRight, Clock } from 'lucide-react';
import { getCoverage, CoverageSummary } from '../lib/api';

const RECENT_KEY = 'oom_recent_searches_v1';

interface Suggestion {
  type: 'state' | 'city' | 'zip' | 'recent' | 'free';
  value: string;
  label: string;
  detail?: string;
  count?: number;
  apply: () => void;
}

interface Props {
  /** Notify parent that user selected a result */
  onSelect: (sel: { state?: string; city?: string; zip?: string; query?: string }) => void;
}

export default function SmartSearch({ onSelect }: Props) {
  const [text, setText] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [coverage, setCoverage] = useState<CoverageSummary | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getCoverage().then(setCoverage).catch(() => {});
  }, []);

  // Aggregate facets from global coverage data (independent of current filters)
  const facets = useMemo(() => {
    const states = new Map<string, number>();
    const cities = new Map<string, { count: number; state: string }>();
    if (coverage) {
      for (const [code, count] of Object.entries(coverage.by_state)) {
        states.set(code, count);
      }
      for (const c of coverage.top_cities ?? []) {
        cities.set(`${c.city}, ${c.state}`, { count: c.count, state: c.state });
      }
    }
    return { states, cities };
  }, [coverage]);

  const recents: string[] = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    } catch {
      return [];
    }
  }, [open]);

  const suggestions: Suggestion[] = useMemo(() => {
    const q = text.trim().toLowerCase();
    const out: Suggestion[] = [];

    // No query → recents + top states
    if (!q) {
      for (const r of recents.slice(0, 4)) {
        out.push({
          type: 'recent',
          value: r,
          label: r,
          apply: () => {
            setText(r);
            doSelect({ query: r });
          },
        });
      }
      const topStates = [...facets.states.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
      for (const [st, count] of topStates) {
        out.push({
          type: 'state',
          value: st,
          label: st,
          detail: 'state',
          count,
          apply: () => doSelect({ state: st }),
        });
      }
      return out;
    }

    // ZIP shortcut
    if (/^\d{5}$/.test(q)) {
      out.push({
        type: 'zip',
        value: q,
        label: q,
        detail: 'fly to ZIP',
        apply: () => doSelect({ zip: q, query: q }),
      });
    }

    // 2-letter state shortcut
    if (/^[a-z]{2}$/i.test(q)) {
      const st = q.toUpperCase();
      if (facets.states.has(st)) {
        out.push({
          type: 'state',
          value: st,
          label: st,
          detail: 'state',
          count: facets.states.get(st),
          apply: () => doSelect({ state: st }),
        });
      }
    }

    // Cities matching
    const cityMatches = [...facets.cities.entries()]
      .filter(([k]) => k.toLowerCase().includes(q))
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 6);
    for (const [k, v] of cityMatches) {
      const [city] = k.split(',');
      out.push({
        type: 'city',
        value: k,
        label: k,
        detail: 'city',
        count: v.count,
        apply: () => doSelect({ state: v.state, city: city.trim(), query: k }),
      });
    }

    // States matching by name
    const stateNames: Record<string, string> = {
      AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California',
      CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', FL: 'Florida', GA: 'Georgia',
      HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa',
      KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland',
      MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi',
      MO: 'Missouri', MT: 'Montana', NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire',
      NJ: 'New Jersey', NM: 'New Mexico', NY: 'New York', NC: 'North Carolina',
      ND: 'North Dakota', OH: 'Ohio', OK: 'Oklahoma', OR: 'Oregon', PA: 'Pennsylvania',
      RI: 'Rhode Island', SC: 'South Carolina', SD: 'South Dakota', TN: 'Tennessee',
      TX: 'Texas', UT: 'Utah', VT: 'Vermont', VA: 'Virginia', WA: 'Washington',
      WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming', DC: 'Washington, DC',
    };
    for (const [code, name] of Object.entries(stateNames)) {
      if (name.toLowerCase().includes(q)) {
        const count = facets.states.get(code);
        out.push({
          type: 'state',
          value: code,
          label: `${name} (${code})`,
          detail: count ? `${count} listings` : 'no data yet — fly map',
          count,
          apply: () => doSelect({ state: count ? code : undefined, query: name }),
        });
      }
    }

    // Free-text fly-to fallback if no DB matches
    if (out.length === 0) {
      out.push({
        type: 'free',
        value: q,
        label: text.trim(),
        detail: 'search map',
        apply: () => doSelect({ query: text.trim() }),
      });
    }

    return out.slice(0, 10);
  }, [text, facets, recents]);

  function doSelect(sel: { state?: string; city?: string; zip?: string; query?: string }) {
    // Persist recent
    const label = sel.query || sel.city || sel.zip || sel.state || '';
    if (label) {
      try {
        const cur = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]') as string[];
        const next = [label, ...cur.filter((x) => x !== label)].slice(0, 8);
        localStorage.setItem(RECENT_KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
    }
    setOpen(false);
    setActiveIndex(0);
    onSelect(sel);
  }

  // Close on outside click
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  // Reset active index when suggestion list changes
  useEffect(() => setActiveIndex(0), [text]);

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, suggestions.length - 1));
      setOpen(true);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const s = suggestions[activeIndex];
      if (s) s.apply();
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }

  return (
    <div ref={containerRef} className="relative w-[300px] sm:w-[360px]">
      <div className="flex items-center bg-white rounded-full shadow-md border border-slate-200 px-3 py-2">
        <SearchIcon className="w-4 h-4 text-slate-400 shrink-0" />
        <input
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Search city, ZIP, or state…"
          className="flex-1 bg-transparent border-0 outline-none text-sm text-slate-900 placeholder:text-slate-400 ml-2"
        />
        {text && (
          <button
            onClick={() => {
              setText('');
              setOpen(true);
            }}
            aria-label="Clear"
            className="text-slate-400 hover:text-slate-700"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {open && suggestions.length > 0 && (
        <div className="absolute top-full mt-2 w-full bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden z-20">
          <ul className="max-h-[320px] overflow-y-auto py-1 text-sm">
            {suggestions.map((s, i) => (
              <li key={s.type + s.value + i}>
                <button
                  onMouseEnter={() => setActiveIndex(i)}
                  onClick={() => s.apply()}
                  className={`w-full text-left px-3 py-2 flex items-center gap-2 ${
                    activeIndex === i ? 'bg-brand-50' : 'hover:bg-slate-50'
                  }`}
                >
                  <span className={`w-7 h-7 rounded-full inline-flex items-center justify-center shrink-0 ${
                    s.type === 'recent' ? 'bg-slate-100 text-slate-400'
                      : s.type === 'state' ? 'bg-brand-100 text-brand-700'
                      : s.type === 'city'  ? 'bg-emerald-100 text-emerald-700'
                      : s.type === 'zip'   ? 'bg-amber-100 text-amber-700'
                      : 'bg-slate-100 text-slate-500'
                  }`}>
                    {s.type === 'recent' ? <Clock className="w-3.5 h-3.5" /> : <MapPin className="w-3.5 h-3.5" />}
                  </span>
                  <span className="flex-1 min-w-0 truncate">
                    <span className="font-semibold text-slate-900">{s.label}</span>
                    {s.detail && (
                      <span className="ml-2 text-xs text-slate-500 capitalize">{s.detail}</span>
                    )}
                  </span>
                  {s.count !== undefined && (
                    <span className="text-xs font-mono text-slate-400">{s.count}</span>
                  )}
                  <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
