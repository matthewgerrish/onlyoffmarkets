type Tier = 'cold' | 'warming' | 'warm' | 'hot' | 'top';

const styles: Record<Tier, string> = {
  cold: 'bg-brand-50 text-brand-700 border border-brand-100',
  warming: 'bg-amber-50 text-amber-700 border border-amber-100',
  warm: 'bg-orange-50 text-orange-700 border border-orange-100',
  hot: 'bg-rose-50 text-rose-700 border border-rose-100',
  top: 'bg-pink-50 text-pink-700 border border-pink-100',
};

const labels: Record<Tier, string> = {
  cold: 'Cold',
  warming: 'Warming',
  warm: 'Warm',
  hot: 'Hot',
  top: 'Top deal',
};

export default function SignalPill({ tier }: { tier: Tier }) {
  return <span className={`pill ${styles[tier]}`}>{labels[tier]}</span>;
}
