import { useEffect, useState } from 'react';

interface Props {
  /** Inclusive max of the slider track (the "$X+" cap). */
  max?: number;
  /** Step size for the slider. */
  step?: number;
  value: { min: number | null; max: number | null };
  onChange: (v: { min: number | null; max: number | null }) => void;
}

const DEFAULT_MAX = 2_000_000;
const DEFAULT_STEP = 25_000;

function fmt(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M`;
  if (n >= 1_000)     return `$${Math.round(n / 1_000)}k`;
  return `$${n}`;
}

/**
 * Two-thumb price range slider, accessible via two stacked native ranges.
 * Internally tracks raw numbers; only emits to parent on commit (mouseup) so
 * dragging doesn't spam network requests.
 */
export default function PriceRange({
  max = DEFAULT_MAX,
  step = DEFAULT_STEP,
  value,
  onChange,
}: Props) {
  const [lo, setLo] = useState<number>(value.min ?? 0);
  const [hi, setHi] = useState<number>(value.max ?? max);

  useEffect(() => {
    setLo(value.min ?? 0);
    setHi(value.max ?? max);
  }, [value.min, value.max, max]);

  function commit(nextLo = lo, nextHi = hi) {
    const minOut = nextLo > 0 ? nextLo : null;
    const maxOut = nextHi < max ? nextHi : null;
    if (minOut !== value.min || maxOut !== value.max) {
      onChange({ min: minOut, max: maxOut });
    }
  }

  const loPct = (lo / max) * 100;
  const hiPct = (hi / max) * 100;

  return (
    <div>
      <div className="flex items-center justify-between text-xs text-slate-700 font-semibold">
        <span>{fmt(lo)}</span>
        <span>{hi >= max ? `${fmt(max)}+` : fmt(hi)}</span>
      </div>

      <div className="relative h-6 mt-2">
        {/* Track */}
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-1 rounded-full bg-slate-200" />
        {/* Active range */}
        <div
          className="absolute top-1/2 -translate-y-1/2 h-1 rounded-full bg-brand-500"
          style={{ left: `${loPct}%`, right: `${100 - hiPct}%` }}
        />
        {/* Lo thumb */}
        <input
          type="range"
          min={0}
          max={max}
          step={step}
          value={lo}
          onChange={(e) => {
            const v = Math.min(Number(e.target.value), hi - step);
            setLo(v);
          }}
          onMouseUp={() => commit()}
          onTouchEnd={() => commit()}
          className="absolute inset-0 w-full bg-transparent appearance-none pointer-events-auto pr-thumb"
          aria-label="Minimum price"
        />
        {/* Hi thumb */}
        <input
          type="range"
          min={0}
          max={max}
          step={step}
          value={hi}
          onChange={(e) => {
            const v = Math.max(Number(e.target.value), lo + step);
            setHi(v);
          }}
          onMouseUp={() => commit()}
          onTouchEnd={() => commit()}
          className="absolute inset-0 w-full bg-transparent appearance-none pointer-events-auto pr-thumb"
          aria-label="Maximum price"
        />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <NumberCell
          label="Min"
          value={value.min}
          placeholder="No min"
          max={hi - step}
          onCommit={(v) => {
            const next = v ?? 0;
            setLo(next);
            commit(next, hi);
          }}
        />
        <NumberCell
          label="Max"
          value={value.max}
          placeholder="No max"
          max={max}
          onCommit={(v) => {
            const next = v ?? max;
            setHi(next);
            commit(lo, next);
          }}
        />
      </div>

      <style>{`
        /* Native range inputs styled to look like invisible thumb-only */
        .pr-thumb { -webkit-appearance: none; height: 24px; }
        .pr-thumb::-webkit-slider-runnable-track { background: transparent; height: 24px; }
        .pr-thumb::-moz-range-track { background: transparent; height: 24px; }
        .pr-thumb::-webkit-slider-thumb {
          -webkit-appearance: none; appearance: none;
          height: 18px; width: 18px; border-radius: 50%;
          background: #fff; border: 2px solid #1d6cf2;
          box-shadow: 0 2px 6px rgba(15,31,61,0.18);
          cursor: pointer; pointer-events: auto;
          margin-top: 0;
        }
        .pr-thumb::-moz-range-thumb {
          height: 18px; width: 18px; border-radius: 50%;
          background: #fff; border: 2px solid #1d6cf2;
          box-shadow: 0 2px 6px rgba(15,31,61,0.18);
          cursor: pointer; pointer-events: auto;
        }
      `}</style>
    </div>
  );
}

function NumberCell({
  label,
  value,
  placeholder,
  max,
  onCommit,
}: {
  label: string;
  value: number | null;
  placeholder: string;
  max: number;
  onCommit: (v: number | null) => void;
}) {
  const [text, setText] = useState<string>(value != null ? String(value) : '');
  useEffect(() => {
    setText(value != null ? String(value) : '');
  }, [value]);
  return (
    <label className="block text-[10px] uppercase tracking-wider font-bold text-slate-500">
      {label}
      <input
        type="number"
        inputMode="numeric"
        placeholder={placeholder}
        value={text}
        min={0}
        max={max}
        step={1000}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => {
          const n = Number(text);
          if (!text) onCommit(null);
          else if (Number.isFinite(n) && n >= 0) onCommit(Math.min(n, max));
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
        }}
        className="input w-full mt-1 text-sm font-mono"
      />
    </label>
  );
}
