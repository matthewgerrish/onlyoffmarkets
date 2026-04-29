import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Coins, Check, Sparkles, Send, History, ArrowRight, Loader2, Crown } from 'lucide-react';
import Seo from '../components/Seo';
import { useTokens } from '../components/TokenContext';
import { useToast } from '../components/Toast';
import { useMembership } from '../components/MembershipContext';
import {
  getPackages,
  getTransactions,
  PackagesResponse,
  TokenTransaction,
} from '../lib/tokens';
import { checkoutTokens } from '../lib/billing';

export default function Tokens() {
  const { summary, refresh, balance } = useTokens();
  const { isPremium, bonusPct } = useMembership();
  const toast = useToast();
  const [data, setData] = useState<PackagesResponse | null>(null);
  const [tx, setTx] = useState<TokenTransaction[] | null>(null);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [params, setParams] = useSearchParams();

  useEffect(() => {
    getPackages().then(setData).catch(() => {});
    getTransactions(20).then(setTx).catch(() => {});
  }, []);

  // Surface ?status=success / cancelled returning from Stripe
  useEffect(() => {
    const status = params.get('status');
    if (status === 'success') {
      toast.success('Purchase complete · tokens credited');
      void refresh();
      getTransactions(20).then(setTx).catch(() => {});
      params.delete('status');
      setParams(params, { replace: true });
    } else if (status === 'cancelled') {
      toast.info('Checkout cancelled');
      params.delete('status');
      setParams(params, { replace: true });
    }
  }, [params, setParams, toast, refresh]);

  const onBuy = async (pkgId: string) => {
    setPurchasing(pkgId);
    try {
      const r = await checkoutTokens(pkgId);
      window.location.assign(r.url);
    } catch (e) {
      toast.error((e as Error).message || 'Checkout failed');
      setPurchasing(null);
    }
  };

  return (
    <>
      <Seo title="Tokens · OnlyOffMarkets" />

      {/* Banner */}
      <section className="relative bg-gradient-to-br from-amber-50 via-white to-brand-50 border-b border-slate-100">
        <div className="container-page py-12 grid lg:grid-cols-[1.4fr_1fr] gap-10 items-center">
          <div className="animate-fade-in-up">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-amber-200 text-xs text-amber-700 font-semibold shadow-sm mb-4">
              <Coins className="w-3.5 h-3.5" /> One credit, two services
            </div>
            <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-brand-navy leading-[1.05]">
              Tokens.<br />
              <span className="text-amber-500">Pay only when you use it.</span>
            </h1>
            <p className="mt-4 text-slate-600 max-w-xl">
              One token = $0.20. Spend tokens on owner contact lookups and direct-mail
              postcards — no monthly minimum, no per-feature subscription.
            </p>
          </div>

          <div className="card p-6 animate-fade-in-up" style={{ animationDelay: '120ms' }}>
            <div className="text-xs uppercase tracking-wider font-bold text-slate-400">
              Current balance
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="font-display font-extrabold text-5xl text-amber-500 tabular-nums">
                {balance.toLocaleString()}
              </span>
              <span className="text-slate-500 text-sm">tokens</span>
            </div>
            {summary && (
              <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                <Stat label="Lifetime purchased" v={summary.lifetime_purchased} />
                <Stat label="Lifetime spent" v={summary.lifetime_spent} />
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Action costs */}
      {data && (
        <section className="container-page py-10">
          <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">What tokens unlock</p>
          <div className="mt-3 grid sm:grid-cols-3 gap-3">
            {data.actions.map((a) => {
              const Icon = a.key === 'mailer_postcard' ? Send : Sparkles;
              return (
                <div key={a.key} className="card card-hover p-4 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-amber-50 text-amber-600 inline-flex items-center justify-center">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-display font-bold text-slate-900 text-sm">{a.label}</div>
                    <div className="text-xs text-slate-500">
                      {a.tokens} token{a.tokens === 1 ? '' : 's'} · ${(a.tokens * data.token_usd).toFixed(2)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Packages */}
      <section className="container-page pb-12">
        <div className="flex items-end justify-between gap-4 flex-wrap mb-6">
          <div>
            <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">Buy tokens</p>
            <h2 className="mt-1 font-display text-2xl sm:text-3xl font-extrabold text-brand-navy">
              Pick a pack
            </h2>
          </div>
          <p className="text-xs text-slate-400 max-w-md">
            Volume discounts up to 18%. Tokens never expire. Mock purchases for
            now — Stripe is hooked up next.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {data?.packages.map((p, i) => {
            const isPopular = p.badge === 'Most popular';
            return (
              <div
                key={p.id}
                className={`card card-hover p-5 flex flex-col relative animate-fade-in-up ${
                  isPopular ? 'border-amber-300 ring-4 ring-amber-100' : ''
                }`}
                style={{ animationDelay: `${i * 70}ms` }}
              >
                {p.badge && (
                  <span
                    className={`absolute -top-2.5 left-1/2 -translate-x-1/2 pill text-white shadow-md ${
                      p.badge === 'Best value' ? 'bg-emerald-500' : 'bg-amber-500'
                    }`}
                  >
                    {p.badge}
                  </span>
                )}
                <div className="text-xs uppercase font-bold tracking-wider text-slate-400">
                  {p.label}
                </div>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="font-display font-extrabold text-3xl text-brand-navy tabular-nums">
                    {p.tokens.toLocaleString()}
                  </span>
                  <span className="text-slate-500 text-xs">tokens</span>
                </div>
                <div className="mt-1 flex items-baseline gap-1">
                  <span className="font-display font-bold text-xl text-slate-900">
                    ${p.price_usd.toFixed(2)}
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    ${p.per_token_usd.toFixed(3)}/tok
                  </span>
                </div>
                {p.discount_pct > 0 ? (
                  <div className="mt-1 text-[11px] font-mono font-bold text-emerald-600">
                    Save {p.discount_pct}%
                  </div>
                ) : (
                  <div className="mt-1 text-[11px] text-slate-400">Standard rate</div>
                )}
                {bonusPct > 0 && (
                  <div className="mt-1 text-[11px] font-bold text-amber-600 inline-flex items-center gap-1">
                    <Crown className="w-3 h-3" /> +{Math.floor((p.tokens * bonusPct) / 100)} bonus
                    tokens (Premium)
                  </div>
                )}
                <button
                  className={`mt-5 ${isPopular ? 'btn-primary' : 'btn-outline'} w-full justify-center`}
                  disabled={purchasing !== null}
                  onClick={() => onBuy(p.id)}
                >
                  {purchasing === p.id ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Charging…
                    </>
                  ) : (
                    <>
                      Buy <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* History */}
      <section className="container-page pb-20">
        <div className="flex items-end justify-between gap-4 mb-4">
          <div>
            <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">History</p>
            <h2 className="mt-1 font-display text-xl font-extrabold text-brand-navy inline-flex items-center gap-2">
              <History className="w-4 h-4" /> Recent activity
            </h2>
          </div>
        </div>

        {tx === null && (
          <div className="card overflow-hidden">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="px-4 py-4 flex gap-4 border-b border-slate-100 last:border-0 animate-fade-in"
                style={{ animationDelay: `${i * 70}ms` }}
              >
                {Array.from({ length: 4 }).map((__, j) => (
                  <div key={j} className="skeleton h-3.5 flex-1" />
                ))}
              </div>
            ))}
          </div>
        )}

        {tx && tx.length === 0 && (
          <div className="card p-10 text-center text-slate-400 text-sm">
            <Coins className="w-5 h-5 mx-auto mb-2 opacity-40" />
            No transactions yet. Buy a starter pack to get going.
          </div>
        )}

        {tx && tx.length > 0 && (
          <div className="card overflow-x-auto">
            <table className="w-full text-sm min-w-[640px]">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="text-left p-3 font-semibold">When</th>
                  <th className="text-left p-3 font-semibold">Action</th>
                  <th className="text-right p-3 font-semibold">Tokens</th>
                  <th className="text-left p-3 font-semibold">Note</th>
                </tr>
              </thead>
              <tbody>
                {tx.map((t) => {
                  const positive = t.amount > 0;
                  return (
                    <tr key={t.id} className="border-t border-slate-100">
                      <td className="p-3 text-xs text-slate-500 font-mono whitespace-nowrap">
                        {t.created_at ? new Date(t.created_at).toLocaleString() : '—'}
                      </td>
                      <td className="p-3">
                        <span
                          className={`pill text-[10px] uppercase ${
                            t.kind === 'purchase'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                              : t.kind === 'refund'
                              ? 'bg-amber-50 text-amber-700 border border-amber-100'
                              : 'bg-slate-100 text-slate-600 border border-slate-200'
                          }`}
                        >
                          {t.kind}
                        </span>{' '}
                        <span className="text-slate-700">{t.action_key || t.package_id || '—'}</span>
                      </td>
                      <td
                        className={`p-3 text-right font-mono font-bold tabular-nums ${
                          positive ? 'text-emerald-600' : 'text-rose-600'
                        }`}
                      >
                        {positive ? '+' : ''}
                        {t.amount}
                      </td>
                      <td className="p-3 text-xs text-slate-500">{t.note || ''}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {!isPremium && (
        <section className="container-page pb-12">
          <div className="card p-6 bg-gradient-to-br from-amber-50 via-white to-amber-50 border-amber-200 flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="font-display font-bold text-brand-navy inline-flex items-center gap-2">
                <Crown className="w-4 h-4 text-amber-500" /> Premium adds 5% to every pack.
              </div>
              <p className="text-sm text-slate-600 mt-1 max-w-xl">
                100 → 105 tokens. 500 → 525. 2000 → 2100. Plus 25 free Standard
                lookups every month, nationwide search, and bulk skip-trace.
              </p>
            </div>
            <Link to="/membership" className="btn-primary">
              Go Premium · $29.95/mo <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
      )}

      <section className="container-page pb-16">
        <div className="card p-6 bg-gradient-to-br from-brand-50 via-white to-amber-50 flex items-center justify-between gap-4 flex-wrap">
          <div>
            <div className="font-display font-bold text-brand-navy inline-flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-500" /> Tokens never expire.
            </div>
            <p className="text-sm text-slate-600 mt-1 max-w-xl">
              Use them for owner lookups today, mailers next month — your call.
              Volume discounts kick in automatically on bigger packs.
            </p>
          </div>
          <Link to="/search" className="btn-primary">
            Find a property to lookup <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </>
  );
}

function Stat({ label, v }: { label: string; v: number }) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2 border border-slate-100">
      <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">{label}</div>
      <div className="font-display font-extrabold text-slate-900 tabular-nums">
        {v.toLocaleString()}
      </div>
    </div>
  );
}
