import { Link } from 'react-router-dom';
import { Coins, ArrowRight, X } from 'lucide-react';

interface Props {
  required: number;
  balance: number;
  action: string;
  onClose: () => void;
}

const ACTION_LABEL: Record<string, string> = {
  skip_trace_standard: 'Standard owner lookup',
  skip_trace_pro: 'Pro owner lookup',
  mailer_postcard: 'Postcard mailer',
};

export default function InsufficientTokensModal({ required, balance, action, onClose }: Props) {
  const short = required - balance;
  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-900/40 backdrop-blur-sm p-0 sm:p-6 animate-fade-in"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl animate-slide-up"
      >
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
          <div className="font-display font-bold text-slate-900 inline-flex items-center gap-2">
            <Coins className="w-4 h-4 text-amber-500" /> Out of tokens
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5">
          <p className="text-slate-700">
            <span className="font-semibold">{ACTION_LABEL[action] || action}</span> needs{' '}
            <strong className="text-amber-600">{required.toLocaleString()}</strong> token
            {required === 1 ? '' : 's'}. You have <strong>{balance.toLocaleString()}</strong> —
            short by <strong className="text-rose-600">{short.toLocaleString()}</strong>.
          </p>

          <div className="mt-4 grid grid-cols-2 gap-2">
            <Stat label="Required" value={required} accent="amber" />
            <Stat label="You have" value={balance} accent="slate" />
          </div>

          <Link
            to="/tokens"
            onClick={onClose}
            className="btn-primary w-full justify-center mt-5"
          >
            Buy more tokens <ArrowRight className="w-4 h-4" />
          </Link>
          <button onClick={onClose} className="btn-ghost w-full justify-center mt-2 text-sm">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: number; accent: 'amber' | 'slate' }) {
  const cls =
    accent === 'amber'
      ? 'border-amber-200 bg-amber-50 text-amber-700'
      : 'border-slate-200 bg-slate-50 text-slate-700';
  return (
    <div className={`rounded-xl border px-3 py-2 ${cls}`}>
      <div className="text-[10px] uppercase tracking-wider font-bold opacity-70">{label}</div>
      <div className="font-display font-extrabold text-2xl tabular-nums">
        {value.toLocaleString()}
      </div>
    </div>
  );
}
