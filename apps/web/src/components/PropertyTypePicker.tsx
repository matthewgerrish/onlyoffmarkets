import { Home, Building2, Building, Trees, Briefcase, Truck, Layers, Box } from 'lucide-react';
import type { PropertyType } from '../lib/api';

const TYPES: { value: PropertyType | ''; label: string; icon: any }[] = [
  { value: '',              label: 'Any',          icon: Layers },
  { value: 'single_family', label: 'House',        icon: Home },
  { value: 'condo',         label: 'Condo',        icon: Building2 },
  { value: 'townhome',      label: 'Townhome',     icon: Building },
  { value: 'multi_family',  label: 'Multi-family', icon: Building },
  { value: 'land',          label: 'Land',         icon: Trees },
  { value: 'commercial',    label: 'Commercial',   icon: Briefcase },
  { value: 'manufactured',  label: 'Manufactured', icon: Truck },
  { value: 'other',         label: 'Other',        icon: Box },
];

interface Props {
  value: PropertyType | '';
  onChange: (v: PropertyType | '') => void;
  counts?: Record<string, number>;
}

export default function PropertyTypePicker({ value, onChange, counts }: Props) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {TYPES.map(({ value: v, label, icon: Icon }) => {
        const isActive = v === value;
        const n = v ? counts?.[v] : undefined;
        return (
          <button
            key={v || 'any'}
            onClick={() => onChange(v as any)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold inline-flex items-center gap-1.5 transition-colors border ${
              isActive
                ? 'bg-brand-500 text-white border-brand-500'
                : 'bg-white text-slate-700 border-slate-200 hover:border-brand-300'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
            {n !== undefined && (
              <span className={`text-[10px] font-mono ${isActive ? 'text-white/80' : 'text-slate-400'}`}>
                {n}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
