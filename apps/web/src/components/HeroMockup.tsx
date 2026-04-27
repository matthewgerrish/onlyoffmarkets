import { Bell, MapPin } from 'lucide-react';
import SignalPill from './SignalPill';

/**
 * A faux product preview shown next to the landing hero — a signal feed card
 * floating over a soft gradient. Pure presentation, no API calls.
 */
export default function HeroMockup() {
  return (
    <div className="relative w-full max-w-[440px] mx-auto select-none">
      {/* Glow */}
      <div className="absolute -inset-12 bg-[radial-gradient(ellipse_at_center,rgba(29,108,242,0.25),transparent_70%)] pointer-events-none" />

      {/* Faux app frame */}
      <div className="relative bg-white border border-slate-200 rounded-2xl shadow-2xl shadow-brand-500/10 overflow-hidden">
        {/* Top window chrome */}
        <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-slate-100 bg-slate-50/60">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-300" />
          <span className="w-2.5 h-2.5 rounded-full bg-amber-300" />
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-300" />
          <span className="ml-2 text-[10px] font-mono text-slate-400 truncate">onlyoffmarkets.com/search</span>
        </div>

        {/* Header strip */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <div className="text-[11px] font-bold text-brand-navy">signal feed</div>
          <span className="text-[10px] text-slate-500 inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            live
          </span>
        </div>

        {/* Cards */}
        <div className="p-3 space-y-2.5">
          <Card
            tier="top"
            equity="78% equity"
            address="••• MAGNOLIA AVE"
            location="Atlanta, GA · Fulton County"
            tags={['Tax delinquent', 'Code violation', 'Vacant']}
            stat={{ label: 'Lien', value: '$9,840' }}
          />
          <Card
            tier="hot"
            equity="62% equity"
            address="••• S ASOTIN ST"
            location="Tacoma, WA · Pierce County"
            tags={['Preforeclosure (NOD)', 'Absentee owner']}
            stat={{ label: 'Default', value: '$14,210' }}
          />
          <Card
            tier="warm"
            equity="41% equity"
            address="••• E SELLS DR"
            location="Scottsdale, AZ · Maricopa County"
            tags={['Trustee sale']}
            stat={{ label: 'Sale', value: 'Jun 4' }}
          />
        </div>

        {/* Footer strip */}
        <div className="px-4 py-2.5 bg-slate-50/60 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
          <span className="inline-flex items-center gap-1.5">
            <Bell className="w-3 h-3 text-brand-500" /> 3 new alerts in last 24h
          </span>
          <span className="font-mono">8 / 1.2M</span>
        </div>
      </div>

      {/* Floating notification chip */}
      <div className="absolute -bottom-4 -right-3 bg-brand-navy text-white rounded-full px-3 py-2 text-[11px] font-semibold shadow-xl flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
        New NOD in Pierce County
      </div>
    </div>
  );
}

function Card({
  tier,
  equity,
  address,
  location,
  tags,
  stat,
}: {
  tier: 'cold' | 'warming' | 'warm' | 'hot' | 'top';
  equity: string;
  address: string;
  location: string;
  tags: string[];
  stat: { label: string; value: string };
}) {
  return (
    <div className="border border-slate-200 hover:border-brand-300 rounded-xl p-3 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <SignalPill tier={tier} />
            <span className="text-[10px] font-semibold text-slate-500">{equity}</span>
          </div>
          <div className="mt-1.5 font-display font-bold text-sm text-slate-900 truncate">
            {address}
          </div>
          <div className="text-[11px] text-slate-500 inline-flex items-center gap-1 truncate">
            <MapPin className="w-3 h-3 shrink-0" /> {location}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {tags.map((t) => (
              <span key={t} className="pill bg-brand-50 text-brand-700 border border-brand-100 text-[10px] py-0">
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-[10px] text-slate-400">{stat.label}</div>
          <div className="font-display font-bold text-sm text-slate-900">{stat.value}</div>
        </div>
      </div>
    </div>
  );
}
