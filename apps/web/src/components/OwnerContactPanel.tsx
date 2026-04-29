import { useEffect, useState } from 'react';
import {
  Phone,
  Mail as MailIcon,
  Loader2,
  Sparkles,
  Send,
  Crown,
  Zap,
  Check,
  Coins,
} from 'lucide-react';
import {
  lookupOwner,
  getSkipTracePricing,
  isInsufficientTokens,
  OwnerContact,
  SkipTraceTier,
  SkipTraceTierInfo,
} from '../lib/mailers';
import { ACTION_TOKEN_COST } from '../lib/tokens';
import { Link } from 'react-router-dom';
import { useToast } from './Toast';
import { useTokens } from './TokenContext';
import InsufficientTokensModal from './InsufficientTokensModal';

interface Insufficient {
  required: number;
  balance: number;
  action: string;
}

/** Owner contact card with tier picker (Standard / Pro) — priced in tokens. */
export default function OwnerContactPanel({ parcelKey }: { parcelKey: string }) {
  const [contact, setContact] = useState<OwnerContact | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tier, setTier] = useState<SkipTraceTier>('standard');
  const [tiers, setTiers] = useState<SkipTraceTierInfo[] | null>(null);
  const [insufficient, setInsufficient] = useState<Insufficient | null>(null);
  const toast = useToast();
  const { balance, setBalance, refresh } = useTokens();

  useEffect(() => {
    getSkipTracePricing()
      .then((d) => setTiers(d.tiers))
      .catch(() => {
        setTiers([
          {
            tier: 'standard',
            label: 'Standard',
            provider_label: 'BatchData',
            advertised_usd: 0.2,
            markup_pct: 100,
            match_rate_pct: 70,
            description: '~70% match rate. Best ROI for solo investors.',
          },
          {
            tier: 'pro',
            label: 'Pro',
            provider_label: 'TLOxp',
            advertised_usd: 0.6,
            markup_pct: 20,
            match_rate_pct: 92,
            description: 'TransUnion-backed, ~92% match rate.',
          },
        ]);
      });
  }, []);

  const tokenCost = ACTION_TOKEN_COST[`skip_trace_${tier}`] ?? (tier === 'pro' ? 3 : 1);
  const cantAfford = balance < tokenCost;

  const onLookup = async () => {
    setLoading(true);
    setError(null);
    try {
      const c = await lookupOwner(parcelKey, tier);
      setContact(c);
      if (typeof c.tokens?.balance === 'number') setBalance(c.tokens.balance);
      toast.success(`Owner contact found · ${c.tokens?.spent ?? tokenCost} token(s) spent`);
    } catch (e) {
      if (isInsufficientTokens(e)) {
        setInsufficient({ required: e.required, balance: e.balance, action: e.action });
        setBalance(e.balance);
      } else {
        setError((e as Error).message);
        toast.error('Owner lookup failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const selected = tiers?.find((t) => t.tier === tier);

  return (
    <div className="card p-6 bg-gradient-to-br from-brand-50 to-white border-brand-100 text-sm">
      <div className="flex items-center justify-between gap-3">
        <div className="font-display font-bold text-brand-navy inline-flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-500" /> Owner contact data
        </div>
        {contact?.billing && (
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 bg-white px-2 py-0.5 rounded-full border border-slate-200">
            via {contact.billing.provider_label}
          </span>
        )}
      </div>

      {!contact && !loading && (
        <>
          {tiers && (
            <div className="mt-4 grid grid-cols-2 gap-2">
              {tiers.map((t) => {
                const isActive = t.tier === tier;
                const Icon = t.tier === 'pro' ? Crown : Zap;
                const cost = ACTION_TOKEN_COST[`skip_trace_${t.tier}`] ?? (t.tier === 'pro' ? 3 : 1);
                return (
                  <button
                    key={t.tier}
                    type="button"
                    onClick={() => setTier(t.tier)}
                    className={`relative text-left rounded-xl border-2 px-3 py-2.5 transition-all active:scale-[0.98] ${
                      isActive
                        ? 'border-brand-500 bg-white shadow-brand'
                        : 'border-slate-200 bg-white/60 hover:border-brand-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                        <Icon
                          className={`w-3.5 h-3.5 ${
                            t.tier === 'pro' ? 'text-amber-500' : 'text-brand-500'
                          }`}
                        />
                        {t.label}
                      </div>
                      {isActive && <Check className="w-3.5 h-3.5 text-brand-500" />}
                    </div>
                    <div className="mt-1.5 flex items-baseline gap-1">
                      <span className="font-display font-extrabold text-brand-navy text-lg leading-none inline-flex items-center gap-1">
                        <Coins className="w-3.5 h-3.5 text-amber-500" /> {cost}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        token{cost === 1 ? '' : 's'}
                      </span>
                    </div>
                    <div className="mt-1 text-[10px] text-slate-500">
                      {t.match_rate_pct}% match · {t.provider_label}
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {selected && (
            <p className="mt-3 text-xs text-slate-500 leading-relaxed">{selected.description}</p>
          )}

          <button
            onClick={onLookup}
            className="mt-4 btn-primary w-full justify-center disabled:opacity-60"
            disabled={cantAfford && balance > 0 ? false : false}
            // we don't disable — we let server respond w/ 402 and surface the modal,
            // but show a hint when we already know we're short
          >
            <Sparkles className="w-4 h-4" />
            Lookup · {tokenCost} token{tokenCost === 1 ? '' : 's'}
          </button>

          {cantAfford ? (
            <Link
              to="/tokens"
              className="mt-2 block text-xs text-rose-500 hover:text-rose-700 text-center font-semibold"
            >
              Balance {balance} — buy more tokens →
            </Link>
          ) : (
            <Link
              to="/tokens"
              className="mt-2 block text-xs text-slate-500 hover:text-brand-600 text-center"
            >
              Balance: {balance} tokens · history →
            </Link>
          )}
        </>
      )}

      {loading && (
        <div className="mt-4 flex items-center justify-center text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin mr-2" /> Looking up via{' '}
          {selected?.provider_label || 'provider'}…
        </div>
      )}

      {error && <div className="mt-3 text-rose-600 text-xs">{error}</div>}

      {contact && (
        <div className="mt-4 space-y-3 animate-fade-in-up">
          {contact.owner_name && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-bold">Owner</div>
              <div className="font-display font-bold text-slate-900">{contact.owner_name}</div>
            </div>
          )}

          {contact.phones.length > 0 && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-bold">Phones</div>
              <ul className="mt-1 space-y-1">
                {contact.phones.map((p, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between gap-2 animate-fade-in-up"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <a
                      href={`tel:${p.number.replace(/\D/g, '')}`}
                      className="inline-flex items-center gap-2 text-slate-900 font-semibold hover:text-brand-600"
                    >
                      <Phone className="w-3.5 h-3.5 text-brand-500" /> {p.number}
                    </a>
                    <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono">
                      {p.type} · {p.confidence}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {contact.emails.length > 0 && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-bold">Emails</div>
              <ul className="mt-1 space-y-1">
                {contact.emails.map((e, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between gap-2 animate-fade-in-up"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <a
                      href={`mailto:${e.address}`}
                      className="inline-flex items-center gap-2 text-slate-900 font-semibold hover:text-brand-600 break-all"
                    >
                      <MailIcon className="w-3.5 h-3.5 text-brand-500" /> {e.address}
                    </a>
                    <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono shrink-0">
                      {e.confidence}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {contact.mailing_address && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                Best mailing address
              </div>
              <div className="text-slate-900 font-semibold">{contact.mailing_address}</div>
            </div>
          )}

          {contact.tokens && (
            <div className="text-[10px] font-mono text-slate-500 bg-white/70 border border-slate-100 rounded-lg px-2.5 py-1.5 inline-flex items-center gap-2">
              <Coins className="w-3 h-3 text-amber-500" />
              <span className="text-slate-700 font-semibold">
                {contact.tokens.spent} token{contact.tokens.spent === 1 ? '' : 's'} spent
              </span>
              {typeof contact.tokens.balance === 'number' && (
                <span>· {contact.tokens.balance} left</span>
              )}
            </div>
          )}

          {contact.notes && (
            <p className="text-[11px] text-slate-500 italic">{contact.notes}</p>
          )}

          <Link
            to={`/mailers?parcel=${encodeURIComponent(parcelKey)}`}
            className="btn-primary w-full justify-center mt-3"
          >
            <Send className="w-4 h-4" /> Send mailer
          </Link>
        </div>
      )}

      {insufficient && (
        <InsufficientTokensModal
          required={insufficient.required}
          balance={insufficient.balance}
          action={insufficient.action}
          onClose={() => {
            setInsufficient(null);
            void refresh();
          }}
        />
      )}
    </div>
  );
}
