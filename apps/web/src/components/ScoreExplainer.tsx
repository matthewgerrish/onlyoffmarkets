import { useEffect, useRef, useState } from 'react';
import { Info, X, Sigma, FileCode2, Sparkles } from 'lucide-react';

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

const DEAL_BAND_TIERS: Array<{ low: number; high: number; band: string; hex: string }> = [
  { low:  0, high: 29,  band: 'cold',     hex: '#1d6cf2' },
  { low: 30, high: 49,  band: 'warming',  hex: '#eab308' },
  { low: 50, high: 69,  band: 'warm',     hex: '#f59e0b' },
  { low: 70, high: 84,  band: 'hot',      hex: '#f97316' },
  { low: 85, high: 100, band: 'top',      hex: '#f43f5e' },
];

const ADU_BAND_TIERS: Array<{ low: number; high: number; band: string; hex: string }> = [
  { low:  0, high: 34,  band: 'none',      hex: '#94a3b8' },
  { low: 35, high: 59,  band: 'limited',   hex: '#eab308' },
  { low: 60, high: 79,  band: 'good',      hex: '#22c55e' },
  { low: 80, high: 100, band: 'excellent', hex: '#10b981' },
];

export default function ScoreExplainer({
  kind, total, band, hex, breakdown, confidence, notes, meta,
}: Props) {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Two-stage mount so the entrance animation is reliably triggered
  // (instead of being skipped by React's render dedupe).
  useEffect(() => {
    if (!open) { setMounted(false); return; }
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, [open]);

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
  // Largest absolute factor for normalizing the mini-bar widths.
  const maxAbs = breakdown.reduce((m, b) => Math.max(m, Math.abs(b.points)), 0) || 1;

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
          className={`absolute z-40 right-0 top-full mt-2 w-[360px] sm:w-[420px] bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden transition-all duration-200 ease-out origin-top-right ${
            mounted ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-95 -translate-y-1'
          }`}
        >
          {/* Hero — gradient halo with the score front and center */}
          <div
            className="relative px-5 pt-5 pb-4 border-b border-slate-100 overflow-hidden"
            style={{
              backgroundImage: `radial-gradient(420px 220px at 100% 0%, ${hex}25, transparent 60%)`,
            }}
          >
            <button
              onClick={() => setOpen(false)}
              className="absolute top-3 right-3 text-slate-400 hover:text-slate-700 p-1 rounded-full hover:bg-white/60"
              aria-label="Close"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500 inline-flex items-center gap-1.5">
              <Sigma className="w-3 h-3" style={{ color: hex }} />
              {kind === 'deal' ? 'Deal score math' : 'ADU score math'}
            </div>

            <div className="mt-2 flex items-end justify-between gap-3">
              <div className="flex items-baseline gap-3">
                <span
                  className="font-display font-extrabold tabular-nums leading-none"
                  style={{ color: hex, fontSize: 56 }}
                >
                  {total}
                </span>
                <div className="text-slate-400 text-sm font-medium pb-1">/ 100</div>
              </div>
              <div
                className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider shadow-sm"
                style={{
                  background: hex,
                  color: '#fff',
                  boxShadow: `0 6px 20px -8px ${hex}`,
                }}
              >
                {band}
              </div>
            </div>

            {meta && (
              <div className="mt-2 text-xs text-slate-600 inline-flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 text-slate-400" />
                {meta}
              </div>
            )}

            {confidence !== undefined && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-[11px] font-semibold mb-1">
                  <span className="text-slate-600 inline-flex items-center gap-1">
                    Data confidence
                  </span>
                  <span className="text-slate-900 tabular-nums">{confidence}%</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700 ease-out"
                    style={{
                      width: mounted ? `${confidence}%` : '0%',
                      background: `linear-gradient(90deg, ${hex}, ${hex}aa)`,
                    }}
                  />
                </div>
                <div className="mt-1 text-[10px] text-slate-400 leading-relaxed">
                  Fraction of the formula's 14 factors that fired on the data we have.
                  Add a paid source to lift confidence.
                </div>
              </div>
            )}
          </div>

          {/* Factor list with mini-bars */}
          <div className="px-5 py-4 max-h-72 overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                Factors that fired
              </div>
              <div className="text-[11px] font-mono font-bold text-slate-500 tabular-nums">
                {breakdown.length}
              </div>
            </div>

            {breakdown.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/40 px-3 py-4 text-center">
                <div className="text-xs text-slate-500 italic">
                  {kind === 'deal'
                    ? 'No active distress data on this parcel yet. Add a paid source key to fill in the formula.'
                    : 'Property doesn\'t qualify under WA / CA statewide ADU rules.'}
                </div>
              </div>
            ) : (
              <ul className="space-y-2.5">
                {breakdown.map((b) => {
                  const positive = b.points >= 0;
                  const pct = Math.max(8, Math.round((Math.abs(b.points) / maxAbs) * 100));
                  return (
                    <li key={b.key + b.label} className="group">
                      <div className="flex items-center justify-between gap-3 text-sm">
                        <div className="min-w-0 flex-1">
                          <div className="text-slate-800 font-medium truncate">{b.label}</div>
                          {b.detail && (
                            <div className="text-[10px] text-slate-400 mt-0.5 truncate">
                              {b.detail}
                            </div>
                          )}
                        </div>
                        <div
                          className={`font-mono font-extrabold tabular-nums shrink-0 ${
                            positive ? 'text-slate-900' : 'text-rose-600'
                          }`}
                        >
                          {positive ? '+' : ''}{b.points}
                        </div>
                      </div>
                      <div className="mt-1.5 h-1 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-700 ease-out"
                          style={{
                            width: mounted ? `${pct}%` : '0%',
                            background: positive
                              ? `linear-gradient(90deg, ${hex}, ${hex}99)`
                              : 'linear-gradient(90deg, #f43f5e, #f43f5eaa)',
                          }}
                        />
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

            {breakdown.length > 0 && (
              <div className="mt-4 pt-3 border-t border-dashed border-slate-200 flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-500 inline-flex items-center gap-1.5">
                  <Sigma className="w-3.5 h-3.5 text-slate-400" />
                  Sum of factors
                  {wasCapped && (
                    <span className="ml-1 text-[10px] font-bold uppercase tracking-wider text-amber-600 bg-amber-50 border border-amber-100 rounded-full px-1.5 py-0.5">
                      capped
                    </span>
                  )}
                </span>
                <span className="font-mono font-extrabold text-slate-900 tabular-nums">
                  = {total}
                </span>
              </div>
            )}
          </div>

          {/* Band tier — gradient spectrum bar */}
          <div className="px-5 py-4 bg-slate-50 border-t border-slate-100">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400 mb-2.5">
              <span>Band tiers</span>
              <span className="text-slate-500 tabular-nums normal-case tracking-normal font-mono">
                you're at {total}
              </span>
            </div>

            {/* Spectrum bar */}
            <div className="relative h-7 rounded-full bg-white border border-slate-200 overflow-hidden flex">
              {tiers.map((t) => {
                const span = t.high - t.low + 1;
                const flexPct = (span / 101) * 100;
                const isCurrent = total >= t.low && total <= t.high;
                return (
                  <div
                    key={t.band}
                    style={{
                      flexBasis: `${flexPct}%`,
                      background: t.hex + (isCurrent ? '40' : '20'),
                    }}
                    className="h-full"
                  />
                );
              })}
              {/* Position marker */}
              <div
                className="absolute top-0 bottom-0 transition-all duration-700 ease-out"
                style={{
                  left: mounted ? `${(total / 100) * 100}%` : '0%',
                  width: 2,
                  background: hex,
                  transform: 'translateX(-1px)',
                  boxShadow: `0 0 0 3px ${hex}30`,
                }}
              />
            </div>

            {/* Tier legend */}
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-3 text-[11px]">
              {[...tiers].reverse().map((t) => {
                const isCurrent = total >= t.low && total <= t.high;
                return (
                  <div
                    key={t.band}
                    className={`flex items-center justify-between gap-2 px-2 py-1 rounded-md transition-colors ${
                      isCurrent ? 'bg-white border border-slate-200 font-bold text-slate-900' : 'text-slate-500'
                    }`}
                  >
                    <span className="inline-flex items-center gap-1.5 capitalize">
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: t.hex }} />
                      {t.band}
                    </span>
                    <span className="font-mono tabular-nums">{t.low}-{t.high}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Notes */}
          {notes && notes.length > 0 && (
            <div className="px-5 py-4 border-t border-slate-100">
              <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400 mb-2">
                Notes
              </div>
              {notes.map((n, i) => (
                <p
                  key={i}
                  className="text-[11px] text-slate-600 leading-relaxed pl-3 border-l-2 italic"
                  style={{ borderColor: hex }}
                >
                  {n}
                </p>
              ))}
            </div>
          )}

          {/* Source pointer */}
          <div className="px-5 py-3 bg-slate-50/80 border-t border-slate-100 flex items-center gap-2">
            <FileCode2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="text-[10px] text-slate-500">
              Math defined in{' '}
              <code className="bg-white border border-slate-200 px-1.5 py-0.5 rounded text-slate-700 font-mono">
                {kind === 'deal' ? 'services/deal_scoring.py' : 'services/adu_scoring.py'}
              </code>
            </span>
          </div>
        </div>
      )}
    </span>
  );
}
