import { useState } from 'react';
import { Phone, Mail as MailIcon, Loader2, Sparkles, Send } from 'lucide-react';
import { lookupOwner, OwnerContact } from '../lib/mailers';
import { Link } from 'react-router-dom';

/** Owner contact card with skip-trace lookup + "Contact" + "Send mailer" actions. */
export default function OwnerContactPanel({ parcelKey }: { parcelKey: string }) {
  const [contact, setContact] = useState<OwnerContact | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onLookup = async () => {
    setLoading(true);
    setError(null);
    try {
      const c = await lookupOwner(parcelKey);
      setContact(c);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-6 bg-gradient-to-br from-brand-50 to-white border-brand-100 text-sm">
      <div className="flex items-center justify-between gap-3">
        <div className="font-display font-bold text-brand-navy inline-flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-500" /> Owner contact data
        </div>
        {contact && (
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 bg-white px-2 py-0.5 rounded-full border border-slate-200">
            via {contact.provider}
          </span>
        )}
      </div>

      {!contact && !loading && (
        <>
          <p className="mt-2 text-slate-600">
            Look up the owner's phone, email, and best mailing address. Costs ~$0.10–0.50/lookup on a paid skip-trace plan.
          </p>
          <button onClick={onLookup} className="mt-4 btn-primary w-full justify-center">
            <Sparkles className="w-4 h-4" /> Lookup owner contact
          </button>
          <Link to="/pricing" className="mt-2 block text-xs text-slate-500 hover:text-brand-600 text-center">
            Free preview · upgrade for unlimited lookups
          </Link>
        </>
      )}

      {loading && (
        <div className="mt-4 flex items-center justify-center text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin mr-2" /> Looking up…
        </div>
      )}

      {error && <div className="mt-3 text-rose-600 text-xs">{error}</div>}

      {contact && (
        <div className="mt-4 space-y-3">
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
                  <li key={i} className="flex items-center justify-between gap-2">
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
                  <li key={i} className="flex items-center justify-between gap-2">
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

          {contact.notes && (
            <p className="text-[11px] text-slate-500 italic">{contact.notes}</p>
          )}

          <Link to={`/mailers?parcel=${encodeURIComponent(parcelKey)}`} className="btn-primary w-full justify-center mt-3">
            <Send className="w-4 h-4" /> Send mailer
          </Link>
        </div>
      )}
    </div>
  );
}
