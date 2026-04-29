import { Link } from 'react-router-dom';
import { Crown, Sparkles, Lock } from 'lucide-react';
import { useMembership } from './MembershipContext';

/** Header pill for the user's current plan. Click → /membership. */
export default function MembershipBadge({ compact = false }: { compact?: boolean }) {
  const { plan, loading } = useMembership();
  if (loading) return null;

  const cfg = {
    free: {
      label: 'Free',
      Icon: Lock,
      cls: 'border-slate-200 bg-white text-slate-600',
    },
    standard: {
      label: 'Standard',
      Icon: Sparkles,
      cls: 'border-brand-200 bg-gradient-to-br from-brand-50 to-white text-brand-700',
    },
    premium: {
      label: 'Premium',
      Icon: Crown,
      cls: 'border-amber-200 bg-gradient-to-br from-amber-50 to-white text-amber-700',
    },
  }[plan];

  const Icon = cfg.Icon;
  return (
    <Link
      to="/membership"
      title="Membership"
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold transition-all hover:-translate-y-0.5 hover:shadow-sm ${cfg.cls} ${
        compact ? 'px-2 py-1 text-[11px]' : 'px-2.5 py-1 text-xs'
      }`}
    >
      <Icon className={compact ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      <span>{cfg.label}</span>
    </Link>
  );
}
