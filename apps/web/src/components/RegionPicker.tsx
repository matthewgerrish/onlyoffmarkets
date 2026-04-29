import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, MapPin, X } from 'lucide-react';

/** All 50 states + DC, with full names + region tagging. */
export const ALL_US_STATES: { code: string; name: string; region: Region }[] = [
  // Northeast
  { code: 'CT', name: 'Connecticut',     region: 'northeast' },
  { code: 'ME', name: 'Maine',           region: 'northeast' },
  { code: 'MA', name: 'Massachusetts',   region: 'northeast' },
  { code: 'NH', name: 'New Hampshire',   region: 'northeast' },
  { code: 'NJ', name: 'New Jersey',      region: 'northeast' },
  { code: 'NY', name: 'New York',        region: 'northeast' },
  { code: 'PA', name: 'Pennsylvania',    region: 'northeast' },
  { code: 'RI', name: 'Rhode Island',    region: 'northeast' },
  { code: 'VT', name: 'Vermont',         region: 'northeast' },
  // Mid-Atlantic
  { code: 'DE', name: 'Delaware',        region: 'mid_atlantic' },
  { code: 'DC', name: 'D.C.',            region: 'mid_atlantic' },
  { code: 'MD', name: 'Maryland',        region: 'mid_atlantic' },
  { code: 'VA', name: 'Virginia',        region: 'mid_atlantic' },
  { code: 'WV', name: 'West Virginia',   region: 'mid_atlantic' },
  // Southeast
  { code: 'AL', name: 'Alabama',         region: 'southeast' },
  { code: 'AR', name: 'Arkansas',        region: 'southeast' },
  { code: 'FL', name: 'Florida',         region: 'southeast' },
  { code: 'GA', name: 'Georgia',         region: 'southeast' },
  { code: 'KY', name: 'Kentucky',        region: 'southeast' },
  { code: 'LA', name: 'Louisiana',       region: 'southeast' },
  { code: 'MS', name: 'Mississippi',     region: 'southeast' },
  { code: 'NC', name: 'North Carolina',  region: 'southeast' },
  { code: 'SC', name: 'South Carolina',  region: 'southeast' },
  { code: 'TN', name: 'Tennessee',       region: 'southeast' },
  // Midwest
  { code: 'IL', name: 'Illinois',        region: 'midwest' },
  { code: 'IN', name: 'Indiana',         region: 'midwest' },
  { code: 'IA', name: 'Iowa',            region: 'midwest' },
  { code: 'KS', name: 'Kansas',          region: 'midwest' },
  { code: 'MI', name: 'Michigan',        region: 'midwest' },
  { code: 'MN', name: 'Minnesota',       region: 'midwest' },
  { code: 'MO', name: 'Missouri',        region: 'midwest' },
  { code: 'NE', name: 'Nebraska',        region: 'midwest' },
  { code: 'ND', name: 'North Dakota',    region: 'midwest' },
  { code: 'OH', name: 'Ohio',            region: 'midwest' },
  { code: 'SD', name: 'South Dakota',    region: 'midwest' },
  { code: 'WI', name: 'Wisconsin',       region: 'midwest' },
  // Texas / South-Central
  { code: 'OK', name: 'Oklahoma',        region: 'south_central' },
  { code: 'TX', name: 'Texas',           region: 'south_central' },
  // Mountain
  { code: 'AZ', name: 'Arizona',         region: 'mountain' },
  { code: 'CO', name: 'Colorado',        region: 'mountain' },
  { code: 'ID', name: 'Idaho',           region: 'mountain' },
  { code: 'MT', name: 'Montana',         region: 'mountain' },
  { code: 'NV', name: 'Nevada',          region: 'mountain' },
  { code: 'NM', name: 'New Mexico',      region: 'mountain' },
  { code: 'UT', name: 'Utah',            region: 'mountain' },
  { code: 'WY', name: 'Wyoming',         region: 'mountain' },
  // West Coast / Pacific
  { code: 'AK', name: 'Alaska',          region: 'pacific' },
  { code: 'CA', name: 'California',      region: 'west_coast' },
  { code: 'HI', name: 'Hawaii',          region: 'pacific' },
  { code: 'OR', name: 'Oregon',          region: 'west_coast' },
  { code: 'WA', name: 'Washington',      region: 'west_coast' },
];

export type Region =
  | 'northeast' | 'mid_atlantic' | 'southeast' | 'midwest'
  | 'south_central' | 'mountain' | 'west_coast' | 'pacific';

export const REGION_LABELS: Record<Region, string> = {
  northeast:     'Northeast',
  mid_atlantic:  'Mid-Atlantic',
  southeast:     'Southeast',
  midwest:       'Midwest',
  south_central: 'South Central',
  mountain:      'Mountain',
  west_coast:    'West Coast',
  pacific:       'Pacific',
};

const REGION_ORDER: Region[] = [
  'west_coast', 'pacific', 'mountain', 'south_central',
  'midwest', 'southeast', 'mid_atlantic', 'northeast',
];

interface Props {
  selected: string[]; // 2-letter state codes
  onChange: (codes: string[]) => void;
  /** Optional state→count from coverage so we can show counts inline */
  counts?: Record<string, number>;
}

/** Multi-select region/state picker. Click a region header to toggle the
 *  whole region; click an individual state to toggle just that state. */
export default function RegionPicker({ selected, onChange, counts }: Props) {
  const [open, setOpen] = useState<Region[]>(['west_coast', 'mountain']);
  const [draft, setDraft] = useState<Set<string>>(new Set(selected));

  useEffect(() => setDraft(new Set(selected)), [selected]);

  const toggleRegion = (r: Region) => {
    setOpen((prev) => (prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]));
  };

  const statesIn = (r: Region) => ALL_US_STATES.filter((s) => s.region === r).map((s) => s.code);

  const regionState = (r: Region): 'all' | 'some' | 'none' => {
    const codes = statesIn(r);
    const inSel = codes.filter((c) => draft.has(c));
    if (inSel.length === 0) return 'none';
    if (inSel.length === codes.length) return 'all';
    return 'some';
  };

  const setRegion = (r: Region, target: boolean) => {
    setDraft((prev) => {
      const next = new Set(prev);
      for (const c of statesIn(r)) (target ? next.add(c) : next.delete(c));
      return next;
    });
  };

  const toggleState = (code: string) => {
    setDraft((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  const apply = () => onChange(Array.from(draft).sort());
  const clearAll = () => setDraft(new Set());

  const allCount = ALL_US_STATES.length;
  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden bg-white">
      <div className="px-3 py-2 border-b border-slate-100 flex items-center justify-between gap-2">
        <div className="inline-flex items-center gap-2 text-xs">
          <MapPin className="w-3.5 h-3.5 text-brand-500" />
          <span className="font-bold text-slate-700">
            {draft.size === 0 ? 'All states' : `${draft.size} of ${allCount} selected`}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {draft.size > 0 && (
            <button
              type="button"
              onClick={clearAll}
              className="text-[11px] text-slate-500 hover:text-rose-600 inline-flex items-center gap-1"
            >
              <X className="w-3 h-3" /> Clear
            </button>
          )}
          <button
            type="button"
            onClick={apply}
            className="text-[11px] font-semibold text-brand-600 hover:text-brand-700 ml-2"
          >
            Apply
          </button>
        </div>
      </div>

      <div className="max-h-[420px] overflow-y-auto">
        {REGION_ORDER.map((r) => {
          const codes = statesIn(r);
          const rState = regionState(r);
          const isOpen = open.includes(r);
          const totalInRegion = codes.reduce((sum, c) => sum + (counts?.[c] ?? 0), 0);
          return (
            <div key={r} className="border-b border-slate-100 last:border-b-0">
              <div className="px-3 py-2 flex items-center justify-between gap-2">
                <label className="inline-flex items-center gap-2 cursor-pointer flex-1">
                  <input
                    type="checkbox"
                    checked={rState === 'all'}
                    ref={(el) => { if (el) el.indeterminate = rState === 'some'; }}
                    onChange={(e) => setRegion(r, e.target.checked)}
                    className="accent-brand-500"
                  />
                  <span className="font-semibold text-sm text-slate-900">{REGION_LABELS[r]}</span>
                  {totalInRegion > 0 && (
                    <span className="text-xs font-mono text-slate-400">{totalInRegion}</span>
                  )}
                </label>
                <button
                  type="button"
                  onClick={() => toggleRegion(r)}
                  className="text-slate-400 hover:text-slate-700"
                  aria-label={isOpen ? 'Collapse' : 'Expand'}
                >
                  {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
              </div>
              {isOpen && (
                <div className="grid grid-cols-2 gap-x-2 gap-y-1 px-3 pb-3 pt-1">
                  {codes.map((c) => {
                    const meta = ALL_US_STATES.find((s) => s.code === c)!;
                    const n = counts?.[c];
                    return (
                      <label
                        key={c}
                        className="flex items-center justify-between gap-2 text-xs text-slate-700 cursor-pointer hover:bg-slate-50 rounded px-1 py-0.5"
                      >
                        <span className="inline-flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={draft.has(c)}
                            onChange={() => toggleState(c)}
                            className="accent-brand-500"
                          />
                          <span className="text-[11px] font-mono text-slate-400 w-6">{c}</span>
                          <span className="truncate">{meta.name}</span>
                        </span>
                        {n !== undefined && n > 0 && (
                          <span className="font-mono text-[10px] text-slate-400">{n}</span>
                        )}
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
