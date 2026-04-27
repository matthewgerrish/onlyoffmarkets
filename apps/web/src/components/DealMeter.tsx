import { Flame } from 'lucide-react';
import { DealScore, bandColor, bandTextColor } from '../lib/score';

/** Compact horizontal meter for use inside a card. */
export function DealMeter({ score, size = 'md' }: { score: DealScore; size?: 'sm' | 'md' }) {
  const w = size === 'sm' ? 'w-20' : 'w-28';
  return (
    <div className={`inline-flex items-center gap-2 ${size === 'sm' ? 'text-[11px]' : 'text-xs'}`}>
      <div className={`relative h-1.5 ${w} bg-slate-100 rounded-full overflow-hidden`}>
        <div
          className={`absolute inset-y-0 left-0 ${bandColor(score.band)} transition-all rounded-full`}
          style={{ width: `${score.total}%` }}
        />
      </div>
      <span className={`font-display font-bold ${bandTextColor(score.band)}`}>
        {score.total}
      </span>
    </div>
  );
}

/** Big version for property detail — vertical stack with breakdown rows. */
export function DealMeterDetail({ score }: { score: DealScore }) {
  return (
    <div>
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wider font-bold text-slate-400">Deal score</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className={`font-display font-extrabold text-5xl ${bandTextColor(score.band)}`}>
              {score.total}
            </span>
            <span className="text-slate-400 text-sm">/ 100</span>
          </div>
        </div>
        <div
          className={`inline-flex items-center gap-1.5 ${bandTextColor(score.band)} text-sm font-semibold uppercase tracking-wider`}
        >
          <Flame className="w-4 h-4" />
          {score.band}
        </div>
      </div>

      <div className="mt-3 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${bandColor(score.band)} transition-all`}
          style={{ width: `${score.total}%` }}
        />
      </div>

      {score.breakdown.length > 0 && (
        <ul className="mt-5 space-y-1.5">
          {score.breakdown.map((b) => (
            <li
              key={b.key + b.label}
              className="flex items-center justify-between gap-3 text-sm"
            >
              <span className="text-slate-600">
                {b.label}
                {b.detail && (
                  <span className="text-slate-400 ml-1.5">— {b.detail}</span>
                )}
              </span>
              <span className="font-mono font-bold text-slate-900 tabular-nums">+{b.points}</span>
            </li>
          ))}
          <li className="border-t border-slate-100 pt-2 flex items-center justify-between gap-3 text-sm">
            <span className="text-slate-500 font-semibold">Total</span>
            <span
              className={`font-mono font-extrabold tabular-nums ${bandTextColor(score.band)}`}
            >
              {score.total}
            </span>
          </li>
        </ul>
      )}
    </div>
  );
}
