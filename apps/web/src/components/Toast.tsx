import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

type ToastKind = 'success' | 'error' | 'info';
interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastCtx {
  push: (message: string, kind?: ToastKind) => void;
  success: (m: string) => void;
  error: (m: string) => void;
  info: (m: string) => void;
}

const Ctx = createContext<ToastCtx | null>(null);

export function useToast(): ToastCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('useToast must be used within ToastProvider');
  return v;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const remove = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback((message: string, kind: ToastKind = 'success') => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => remove(id), 4000);
  }, [remove]);

  const value: ToastCtx = {
    push,
    success: (m) => push(m, 'success'),
    error: (m) => push(m, 'error'),
    info: (m) => push(m, 'info'),
  };

  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onClose={() => remove(t.id)} />
        ))}
      </div>
    </Ctx.Provider>
  );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const [leaving, setLeaving] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setLeaving(true), 3700);
    return () => clearTimeout(t);
  }, []);

  const Icon = toast.kind === 'success' ? CheckCircle2 : toast.kind === 'error' ? AlertTriangle : Info;
  const accent =
    toast.kind === 'success'
      ? 'text-emerald-600 bg-emerald-50'
      : toast.kind === 'error'
      ? 'text-rose-600 bg-rose-50'
      : 'text-brand-600 bg-brand-50';

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 bg-white border border-slate-200 rounded-2xl shadow-brand-lg px-4 py-3 min-w-[260px] max-w-sm ${
        leaving ? 'opacity-0 translate-x-2 transition-all duration-200' : 'animate-slide-in-right'
      }`}
      role="status"
    >
      <div className={`w-8 h-8 rounded-full inline-flex items-center justify-center shrink-0 ${accent}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 text-sm text-slate-800 pt-1">{toast.message}</div>
      <button
        type="button"
        onClick={onClose}
        aria-label="Dismiss"
        className="text-slate-400 hover:text-slate-700 -mr-1 -mt-1 p-1"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
