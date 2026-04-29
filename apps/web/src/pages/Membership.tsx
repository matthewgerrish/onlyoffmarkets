import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Crown, Check, Sparkles, Lock, ArrowRight, Loader2, Settings } from 'lucide-react';
import Seo from '../components/Seo';
import { useToast } from '../components/Toast';
import { useMembership } from '../components/MembershipContext';
import {
  getPlans,
  checkoutMembership,
  openCustomerPortal,
  Plan,
  PlanId,
} from '../lib/billing';

export default function Membership() {
  const { plan, isPaid, isPremium, membership, refresh } = useMembership();
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [stripeLive, setStripeLive] = useState(false);
  const [busy, setBusy] = useState<PlanId | 'portal' | null>(null);
  const [params, setParams] = useSearchParams();
  const toast = useToast();

  useEffect(() => {
    getPlans()
      .then((d) => {
        setPlans(d.plans);
        setStripeLive(d.stripe_live);
      })
      .catch(() => {});
  }, []);

  // Surface success/cancel from Stripe Checkout return URL
  useEffect(() => {
    const status = params.get('status');
    if (status === 'success') {
      toast.success('Membership updated · refreshing your plan…');
      void refresh();
      params.delete('status');
      setParams(params, { replace: true });
    } else if (status === 'cancelled') {
      toast.info('Checkout cancelled');
      params.delete('status');
      setParams(params, { replace: true });
    } else if (status === 'portal_unavailable') {
      toast.info('Customer portal unavailable in mock mode');
      params.delete('status');
      setParams(params, { replace: true });
    }
  }, [params, setParams, toast, refresh]);

  const onSubscribe = async (target: PlanId) => {
    if (target === 'free') return;
    setBusy(target);
    try {
      const r = await checkoutMembership(target);
      window.location.assign(r.url);
    } catch (e) {
      toast.error((e as Error).message || 'Checkout failed');
      setBusy(null);
    }
  };

  const onPortal = async () => {
    setBusy('portal');
    try {
      const r = await openCustomerPortal();
      window.location.assign(r.url);
    } catch (e) {
      toast.error((e as Error).message || 'Could not open portal');
      setBusy(null);
    }
  };

  return (
    <>
      <Seo title="Membership · OnlyOffMarkets" />

      {/* Banner */}
      <section className="relative bg-gradient-to-br from-amber-50 via-white to-brand-50 border-b border-slate-100">
        <div className="container-page py-12">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-slate-200 text-xs font-semibold text-slate-600 shadow-sm mb-4">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Membership
            </div>
            <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-brand-navy leading-[1.05]">
              Pick a plan.<br />
              <span className="text-amber-500">Tokens stay separate.</span>
            </h1>
            <p className="mt-4 text-slate-600 max-w-xl">
              Membership unlocks features. Tokens unlock actions. Premium members
              also get a permanent 5% bonus on every token pack — automatically applied.
            </p>
          </div>

          {membership && (
            <div className="mt-6 inline-flex items-center gap-3 bg-white border border-slate-200 rounded-full px-4 py-2 text-sm shadow-sm animate-fade-in">
              <span className="text-slate-500">Current plan:</span>
              <strong className="text-brand-navy">{membership.plan_meta.label}</strong>
              {membership.cancel_at_period_end && (
                <span className="pill bg-rose-50 text-rose-700 border border-rose-100 text-[10px]">
                  cancels at period end
                </span>
              )}
              {isPaid && (
                <button
                  onClick={onPortal}
                  className="ml-2 inline-flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-semibold"
                  disabled={busy === 'portal'}
                >
                  {busy === 'portal' ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Settings className="w-3.5 h-3.5" />
                  )}
                  Manage
                </button>
              )}
            </div>
          )}
        </div>
      </section>

      {!stripeLive && (
        <div className="container-page pt-6">
          <div className="card p-3 bg-amber-50 border-amber-200 text-amber-800 text-xs flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5" />
            Stripe is in <strong className="mx-1">mock mode</strong>. Subscriptions and
            token purchases are simulated until <code>STRIPE_SECRET_KEY</code> is set.
          </div>
        </div>
      )}

      {/* Plan comparison */}
      <section className="container-page py-10">
        <div className="grid lg:grid-cols-3 gap-5">
          {plans?.map((p, i) => {
            const isCurrent = p.id === plan;
            const isPremiumCard = p.id === 'premium';
            const Icon = p.id === 'premium' ? Crown : p.id === 'standard' ? Sparkles : Lock;
            return (
              <div
                key={p.id}
                className={`card card-hover p-7 flex flex-col relative animate-fade-in-up ${
                  isPremiumCard
                    ? 'border-amber-300 ring-4 ring-amber-100 lg:-translate-y-2'
                    : isCurrent
                    ? 'border-brand-400'
                    : ''
                }`}
                style={{ animationDelay: `${i * 80}ms` }}
              >
                {p.badge && (
                  <span
                    className={`absolute -top-3 left-1/2 -translate-x-1/2 pill text-white shadow-md whitespace-nowrap ${
                      isPremiumCard ? 'bg-amber-500' : 'bg-brand-500'
                    }`}
                  >
                    {p.badge}
                  </span>
                )}
                {isCurrent && (
                  <span className="absolute -top-3 right-4 pill bg-emerald-500 text-white shadow-md whitespace-nowrap">
                    Current
                  </span>
                )}

                <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                  <Icon
                    className={`w-3.5 h-3.5 ${
                      isPremiumCard ? 'text-amber-500' : p.id === 'standard' ? 'text-brand-500' : 'text-slate-400'
                    }`}
                  />
                  {p.label}
                </div>
                <p className="mt-1 text-sm text-slate-500">{p.blurb}</p>

                <div className="mt-4 flex items-baseline gap-1">
                  <span className="font-display text-5xl font-extrabold text-brand-navy">
                    ${p.price_usd.toFixed(p.price_usd % 1 === 0 ? 0 : 2)}
                  </span>
                  <span className="text-slate-500 text-sm">
                    {p.interval === 'month' ? '/mo' : ''}
                  </span>
                </div>

                {p.token_bonus_pct > 0 && (
                  <div className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-100 rounded-full px-2 py-0.5 self-start">
                    +{p.token_bonus_pct}% bonus on every token pack
                  </div>
                )}
                {p.monthly_token_grant > 0 && (
                  <div className="mt-1.5 text-xs text-slate-500">
                    Includes <strong className="text-amber-600">{p.monthly_token_grant} free tokens</strong>{' '}
                    every month
                  </div>
                )}

                <ul className="mt-6 space-y-2 text-sm text-slate-700 flex-1">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <Check
                        className={`w-4 h-4 mt-0.5 shrink-0 ${
                          isPremiumCard ? 'text-amber-500' : 'text-brand-500'
                        }`}
                      />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>

                <button
                  className={`mt-6 ${
                    isPremiumCard ? 'btn-primary' : isCurrent ? 'btn-outline' : 'btn-outline'
                  } disabled:opacity-50`}
                  disabled={isCurrent || busy !== null || p.id === 'free'}
                  onClick={() => onSubscribe(p.id)}
                >
                  {busy === p.id ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Redirecting…
                    </>
                  ) : isCurrent ? (
                    <>Current plan</>
                  ) : p.id === 'free' ? (
                    <>It's free — start using it</>
                  ) : (
                    <>
                      {p.cta} <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* Premium spotlight */}
      <section className="container-page pb-16">
        <div className="card p-6 bg-gradient-to-br from-amber-50 via-white to-amber-50 border-amber-200">
          <div className="grid md:grid-cols-[1fr_1.4fr] gap-6 items-center">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-600 mb-2">
                <Crown className="w-3.5 h-3.5" /> Why Premium pays for itself
              </div>
              <h3 className="font-display text-2xl font-extrabold text-brand-navy">
                Stack the savings.
              </h3>
              <p className="mt-2 text-sm text-slate-600 max-w-md">
                25 free Standard lookups every month equal $5 saved. The
                5% token bonus on a Pro pack alone covers more than a third of the
                subscription. Nationwide search lifts the metro lock so you can
                hunt anywhere a deal pops up.
              </p>
              {!isPremium && (
                <button
                  onClick={() => onSubscribe('premium')}
                  className="mt-4 btn-primary"
                  disabled={busy !== null}
                >
                  Upgrade to Premium <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <Spot label="25 free lookups/mo" sub="$5 retail value" />
              <Spot label="5% token bonus" sub="auto applied at checkout" />
              <Spot label="Nationwide search" sub="no metro lock-in" />
              <Spot label="Bulk skip-trace" sub="batch before mailers" />
              <Spot label="Comp generator" sub="3-mile radius sales" />
              <Spot label="Equity heatmap" sub="map overlay layer" />
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function Spot({ label, sub }: { label: string; sub: string }) {
  return (
    <div className="rounded-xl bg-white border border-amber-100 px-3 py-2 shadow-sm">
      <div className="font-display font-bold text-brand-navy">{label}</div>
      <div className="text-[11px] text-slate-500">{sub}</div>
    </div>
  );
}
