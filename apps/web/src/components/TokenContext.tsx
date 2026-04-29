import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import { getBalance, BalanceSummary } from '../lib/tokens';

interface TokenCtx {
  balance: number;
  summary: BalanceSummary | null;
  /** Optimistic local update — call after a server response that includes a new balance. */
  setBalance: (n: number) => void;
  /** Force a full re-fetch from /tokens/balance. */
  refresh: () => Promise<void>;
  loading: boolean;
}

const Ctx = createContext<TokenCtx | null>(null);

export function useTokens(): TokenCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('useTokens must be used within TokenProvider');
  return v;
}

export function TokenProvider({ children }: { children: ReactNode }) {
  const [summary, setSummary] = useState<BalanceSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const s = await getBalance();
      setSummary(s);
    } catch {
      // Network blip — keep last known balance.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setBalance = useCallback((n: number) => {
    setSummary((prev) =>
      prev ? { ...prev, balance: n } : { user_id: '', balance: n, lifetime_purchased: 0, lifetime_spent: 0 },
    );
  }, []);

  const value: TokenCtx = {
    balance: summary?.balance ?? 0,
    summary,
    setBalance,
    refresh,
    loading,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
