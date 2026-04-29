import { Bed, Bath, Ruler } from 'lucide-react';

interface Props {
  minBeds: number | null;
  setMinBeds: (n: number | null) => void;
  minBaths: number | null;
  setMinBaths: (n: number | null) => void;
  minSqft: number | null;
  setMinSqft: (n: number | null) => void;
  maxSqft: number | null;
  setMaxSqft: (n: number | null) => void;
}

const BED_OPTS = [null, 1, 2, 3, 4, 5];
const BATH_OPTS = [null, 1, 1.5, 2, 2.5, 3];

export default function BedBathSqft({
  minBeds, setMinBeds,
  minBaths, setMinBaths,
  minSqft, setMinSqft,
  maxSqft, setMaxSqft,
}: Props) {
  return (
    <div className="space-y-4">
      {/* Beds */}
      <div>
        <div className="flex items-center justify-between text-xs font-semibold text-slate-600 mb-2">
          <span className="inline-flex items-center gap-1.5">
            <Bed className="w-3.5 h-3.5 text-brand-500" /> Bedrooms
          </span>
          <span className="font-mono text-slate-500">
            {minBeds === null ? 'any' : `${minBeds}+`}
          </span>
        </div>
        <PillRow
          options={BED_OPTS}
          value={minBeds}
          onChange={setMinBeds}
          format={(v) => (v === null ? 'Any' : `${v}+`)}
        />
      </div>

      {/* Baths */}
      <div>
        <div className="flex items-center justify-between text-xs font-semibold text-slate-600 mb-2">
          <span className="inline-flex items-center gap-1.5">
            <Bath className="w-3.5 h-3.5 text-brand-500" /> Bathrooms
          </span>
          <span className="font-mono text-slate-500">
            {minBaths === null ? 'any' : `${minBaths}+`}
          </span>
        </div>
        <PillRow
          options={BATH_OPTS}
          value={minBaths}
          onChange={setMinBaths}
          format={(v) => (v === null ? 'Any' : `${v}+`)}
        />
      </div>

      {/* Sqft */}
      <div>
        <div className="flex items-center justify-between text-xs font-semibold text-slate-600 mb-2">
          <span className="inline-flex items-center gap-1.5">
            <Ruler className="w-3.5 h-3.5 text-brand-500" /> Square feet
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <SqftCell label="Min sqft" value={minSqft} placeholder="No min" onChange={setMinSqft} />
          <SqftCell label="Max sqft" value={maxSqft} placeholder="No max" onChange={setMaxSqft} />
        </div>
      </div>
    </div>
  );
}

function PillRow({
  options,
  value,
  onChange,
  format,
}: {
  options: (number | null)[];
  value: number | null;
  onChange: (v: number | null) => void;
  format: (v: number | null) => string;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt, i) => {
        const isActive = (opt === null && value === null) || opt === value;
        return (
          <button
            key={i}
            type="button"
            onClick={() => onChange(opt)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
              isActive
                ? 'bg-brand-500 text-white border-brand-500'
                : 'bg-white text-slate-700 border-slate-200 hover:border-brand-300'
            }`}
          >
            {format(opt)}
          </button>
        );
      })}
    </div>
  );
}

function SqftCell({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string;
  value: number | null;
  placeholder: string;
  onChange: (v: number | null) => void;
}) {
  return (
    <label className="block text-[10px] uppercase tracking-wider font-bold text-slate-500">
      {label}
      <input
        type="number"
        inputMode="numeric"
        placeholder={placeholder}
        defaultValue={value ?? ''}
        min={0}
        step={100}
        onBlur={(e) => {
          const t = e.target.value.trim();
          if (!t) onChange(null);
          else {
            const n = Number(t);
            if (Number.isFinite(n) && n >= 0) onChange(n);
          }
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
        }}
        className="input w-full mt-1 text-sm font-mono"
      />
    </label>
  );
}
