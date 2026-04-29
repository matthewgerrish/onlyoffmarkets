import { useEffect, useState } from 'react';
import { getCoverage, CoverageSummary } from '../lib/api';

interface Props {
  selected: string;
  onSelect: (state: string) => void;
}

/** Horizontal scrollable pill row of states with counts, ordered by count desc.
 *  Click "All" to clear, click a state to filter. */
export default function BrowseStates({ selected, onSelect }: Props) {
  const [cov, setCov] = useState<CoverageSummary | null>(null);
  useEffect(() => {
    getCoverage().then(setCov).catch(() => {});
  }, []);

  if (!cov) return null;
  const states = Object.entries(cov.by_state).sort((a, b) => b[1] - a[1]);

  return (
    <div className="px-4 py-2 border-b border-slate-100 flex gap-1.5 overflow-x-auto whitespace-nowrap scrollbar-thin">
      <button
        onClick={() => onSelect('')}
        className={`px-3 py-1 rounded-full text-xs font-semibold inline-flex items-center gap-1.5 shrink-0 transition-colors ${
          selected === '' ? 'bg-brand-500 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
        }`}
      >
        All
        <span className={`text-[10px] font-mono ${selected === '' ? 'text-white/80' : 'text-slate-500'}`}>
          {cov.total_parcels}
        </span>
      </button>
      {states.map(([code, count]) => (
        <button
          key={code}
          onClick={() => onSelect(code)}
          className={`px-3 py-1 rounded-full text-xs font-semibold inline-flex items-center gap-1.5 shrink-0 transition-colors ${
            selected === code ? 'bg-brand-500 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          }`}
        >
          {code}
          <span className={`text-[10px] font-mono ${selected === code ? 'text-white/80' : 'text-slate-500'}`}>
            {count}
          </span>
        </button>
      ))}
    </div>
  );
}
