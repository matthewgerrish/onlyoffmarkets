import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import { getMembership, Membership, PlanId } from '../lib/billing';

interface MembershipCtx {
  membership: Membership | null;
  plan: PlanId;
  isPremium: boolean;
  isPaid: boolean;
  bonusPct: number;
  refresh: () => Promise<void>;
  loading: boolean;
}

const Ctx = createContext<MembershipCtx | null>(null);

export function useMembership(): MembershipCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('useMembership must be used within MembershipProvider');
  return v;
}

export function MembershipProvider({ children }: { children: ReactNode }) {
  const [membership, setMembership] = useState<Membership | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const m = await getMembership();
      setMembership(m);
    } catch {
      // Network blip — keep last known.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Re-fetch when the user returns from Stripe Checkout — landing on a
  // ?status=success URL is a strong signal something changed.
  useEffect(() => {
    const onPop = () => {
      const sp = new URLSearchParams(window.location.search);
      if (sp.get('status') === 'success') void refresh();
    };
    window.addEventListener('popstate', onPop);
    onPop();
    return () => window.removeEventListener('popstate', onPop);
  }, [refresh]);

  const plan: PlanId = (membership?.plan as PlanId) || 'free';
  const value: MembershipCtx = {
    membership,
    plan,
    isPremium: plan === 'premium',
    isPaid: plan !== 'free',
    bonusPct: membership?.plan_meta?.token_bonus_pct ?? 0,
    refresh,
    loading,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
