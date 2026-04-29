import { Link } from 'react-router-dom';
import { Coins } from 'lucide-react';
import { useTokens } from './TokenContext';

/** Header-bar token balance pill. Click → /tokens. */
export default function TokenBadge({ compact = false }: { compact?: boolean }) {
  const { balance, loading } = useTokens();
  return (
    <Link
      to="/tokens"
      title="Token wallet"
      className={`inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-gradient-to-br from-amber-50 to-white text-amber-700 font-semibold transition-all hover:-translate-y-0.5 hover:shadow-sm ${
        compact ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm'
      }`}
    >
      <Coins className={compact ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
      <span className="font-mono tabular-nums">
        {loading ? '—' : balance.toLocaleString()}
      </span>
      {!compact && <span className="text-amber-600/80 font-normal">tokens</span>}
    </Link>
  );
}
