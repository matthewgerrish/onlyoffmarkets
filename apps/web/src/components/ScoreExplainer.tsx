import { useEffect, useRef, useState } from 'react';
import { Info, X, Calculator } from 'lucide-react';

export interface BreakdownItem {
  key: string;
  label: string;
  points: number;
  detail?: string;
}

export type ExplainerKind = 'deal' | 'adu';

interface Props {
  kind: ExplainerKind;
  total: number;
  band: string;
  hex: string;
  breakdown: BreakdownItem[];
  /** For deal-score: confidence % (factors fired / factors possible). */
  confidence?: number;
  /** For ADU: extra notes from the scorer (state-law caveats etc.). */
  notes?: string[];
  /** Optional metadata bumper, e.g. "WA · HB 1337" or units possible. */
  meta?: string;
}

const DEAL_BAND_TIERS: Array<{ range: string; band: string; hex: string }> = [
  { range: '85 – 100', band: 'top',      hex: '#f43f5e' },
  { range: '70 – 84',  band: 'hot',      hex: '#f97316' },
  { range: '50 – 69',  band: 'warm',     hex: '#f59e0b' },
  { range: '30 – 49',  band: 'warming',  hex: '#eab308' },
  { range: '0 – 29',   band: 'cold',     hex: '#1d6cf2' },
];

const ADU_BAND_TIERS: Array<{ range: string; band: string; hex: string }> = [
  { range: '80 – 100', band: 'excellent', hex: '#10b981' },
  { range: '60 – 79',  band: 'good',      hex: '#22c55e' },
  { range: '35 – 59',  band: 'limited',   hex: '#eab308' },
  { range: '0 – 34',   band: 'none',      hex: '#94a3b8' },
];

export default function ScoreExplainer({
  kind, total, band, hex, breakdown, confidence, notes, meta,
}: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('click', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('click', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const tiers = kind === 'deal' ? DEAL_BAND_TIERS : ADU_BAND_TIERS;
  const sumOfFactors = breakdown.reduce((s, b) => s + b.points, 0);
  const wasCapped = sumOfFactors !== total;

  return (
    <span ref={ref} className="relative inline-block">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        title="Show the math"
        aria-label="Show calculation"
        className="inline-flex items-center justify-center w-6 h-6 rounded-full text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition-colors"
      >
        <Info className="w-4 h-4" />
      </button>

      {open && (
        <div
          onClick={(e) => e.stopPropagation()}
          className="absolute z-40 right-0 top-full mt-2 w-[340px] sm:w-[380px] bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-fade-in-down"
        >
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <div className="inline-flex items-center gap-2 font-display font-bold text-slate-900 text-sm">
              <Calculator className="w-4 h-4" style={{ color: hex }} />
              {kind === 'deal' ? 'Deal score math' : 'ADU score math'}
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-slate-400 hover:text-slate-700 p-1"
              aria-label="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Result strip */}
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-100">
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-display font-extrabold text-3xl tabular-nums" style={{ color: hex }}>
                {total}
              </span>
              <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                style={{ color: hex, backgroundColor: hex + '15', borderColor: hex + '40', borderWidth: 1 }}>
                {band}
              </span>
            </div>
            {meta && <div className="text-[11px] text-slate-500 mt-1">{meta}</div>}
            {confidence !== undefined && (
              <div className="text-[11px] text-slate-500 mt-1">
                <strong>{confidence}%</strong> confidence — that fraction of the formula's 14 factors
                fired on the data we have. Add a paid source to lift confidence.
              </div>
            )}
          </div>

          {/* Factor breakdown */}
          <div className="px-4 py-3 max-h-72 overflow-y-auto">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
              Factors that fired ({breakdown.length})
            </div>
            {breakdown.length === 0 ? (
              <p className="text-xs text-slate-500 italic">
                No factors fired. {kind === 'deal'
                  ? 'No active distress data on this parcel yet.'
                  : 'Property doesn\'t qualify under WA / CA statewide ADU rules.'}
              </p>
            ) : (
              <ul className="space-y-1.5">
                {breakdown.map((b) => (
                  <li key={b.key + b.label} className="flex items-start justify-between gap-3 text-sm">
                    <div className="min-w-0">
                      <div className="text-slate-700">{b.label}</div>
                      {b.detail && (
                        <div className="text-[11px] text-slate-400 mt-0.5">{b.detail}</div>
                      )}
                    </div>
                    <div className={`font-mono font-bold tabular-nums shrink-0 ${
                      b.points >= 0 ? 'text-slate-900' : 'text-rose-600'
                    }`}>
                      {b.points >= 0 ? '+' : ''}{b.points}
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {/* Math footer */}
            {breakdown.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-500">
                  {breakdown.length} factor{breakdown.length === 1 ? '' : 's'}
                  {wasCapped ? ' · capped at 100' : ''}
                </span>
                <span className="font-mono font-bold text-slate-900 tabular-nums">
                  = {total}
                </span>
              </div>
            )}
          </div>

          {/* Band tier reference */}
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-100">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
              Band tiers
            </div>
            <div className="grid grid-cols-2 gap-1 text-[11px]">
              {tiers.map((t) => (
                <div
                  key={t.band}
                  className={`flex items-center justify-between gap-2 px-2 py-1 rounded ${
                    band === t.band ? 'bg-white border border-slate-200 font-bold' : 'text-slate-500'
                  }`}
                >
                  <span className="inline-flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: t.hex }} />
                    {t.band}
                  </span>
                  <span className="font-mono">{t.range}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Notes */}
          {notes && notes.length > 0 && (
            <div className="px-4 py-3 border-t border-slate-100">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                Notes
              </div>
              {notes.map((n, i) => (
                <p key={i} className="text-[11px] text-slate-500 leading-relaxed">{n}</p>
              ))}
            </div>
          )}

          {/* Source line */}
          <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-100 text-[10px] text-slate-400">
            Math defined in{' '}
            <code className="bg-slate-200/60 px-1 py-0.5 rounded">
              {kind === 'deal' ? 'services/deal_scoring.py' : 'services/adu_scoring.py'}
            </code>
          </div>
        </div>
      )}
    </span>
  );
}
