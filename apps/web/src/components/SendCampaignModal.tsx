import { useEffect, useMemo, useState } from 'react';
import { Send, X, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { sendCampaign } from '../lib/mailers';
import type { MailerTemplate } from '../lib/mailers';
import { listOffMarket, OffMarketRow } from '../lib/api';

interface Props {
  template: MailerTemplate;
  /** If passed, send to that single parcel only and skip the recipient picker */
  fixedParcelKey?: string | null;
  /** If passed, pre-select these parcels and skip the picker step */
  prefilledKeys?: string[];
  onClose: () => void;
}

interface FromAddress {
  name: string;
  address_line1: string;
  address_city: string;
  address_state: string;
  address_zip: string;
}

const STORAGE_KEY = 'oom_mailer_from_v1';

function loadFrom(): FromAddress {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore */
  }
  return { name: '', address_line1: '', address_city: '', address_state: '', address_zip: '' };
}

export default function SendCampaignModal({ template, fixedParcelKey, prefilledKeys, onClose }: Props) {
  const [from, setFrom] = useState<FromAddress>(loadFrom());
  const [campaignName, setCampaignName] = useState(`${template.name} — ${new Date().toLocaleDateString()}`);
  const [stateFilter, setStateFilter] = useState<string>('');
  const [maxRecipients, setMaxRecipients] = useState<number>(prefilledKeys?.length ? Math.max(50, prefilledKeys.length) : 50);
  const [pool, setPool] = useState<OffMarketRow[] | null>(null);
  const initialSelected = fixedParcelKey ? [fixedParcelKey] : (prefilledKeys || []);
  const [selected, setSelected] = useState<Set<string>>(new Set(initialSelected));
  const skipPick = !!fixedParcelKey || (prefilledKeys && prefilledKeys.length > 0);
  const [step, setStep] = useState<'pick' | 'confirm' | 'sent' | 'failed'>(skipPick ? 'confirm' : 'pick');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ sent: number; errors: number; status: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load candidate parcels from the API when picker is active
  useEffect(() => {
    if (skipPick) return;
    setPool(null);
    listOffMarket({ state: stateFilter || undefined, limit: 300 })
      .then((d) => setPool(d.results))
      .catch((e: Error) => setError(e.message));
  }, [stateFilter, skipPick]);

  const filteredPool = useMemo(() => (pool ?? []).slice(0, 200), [pool]);

  const toggleParcel = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else if (next.size < maxRecipients) next.add(key);
      return next;
    });
  };

  const selectVisible = () => {
    const next = new Set(selected);
    for (const r of filteredPool) {
      if (next.size >= maxRecipients) break;
      next.add(r.parcel_key);
    }
    setSelected(next);
  };

  const fromValid = from.name && from.address_line1 && from.address_city && from.address_state.length === 2 && from.address_zip;
  const canSend = fromValid && selected.size > 0 && campaignName;

  const onSend = async () => {
    setSending(true);
    setError(null);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(from));
    try {
      const res = await sendCampaign({
        name: campaignName,
        template_id: template.id,
        parcel_keys: Array.from(selected),
        from_name: from.name,
        from_address_line1: from.address_line1,
        from_address_city: from.address_city,
        from_address_state: from.address_state,
        from_address_zip: from.address_zip,
      });
      setResult({ sent: res.sent_count, errors: res.error_count, status: res.status });
      setStep('sent');
    } catch (e) {
      setError((e as Error).message);
      setStep('failed');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-6 bg-slate-900/40 backdrop-blur-sm">
      <div className="w-full sm:max-w-2xl bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl max-h-[92vh] overflow-y-auto">
        <div className="sticky top-0 z-10 bg-white border-b border-slate-100 px-5 py-3 flex items-center justify-between">
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-wider font-bold text-slate-400">Send campaign</div>
            <h2 className="font-display font-bold text-slate-900 truncate">{template.name}</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1 shrink-0">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {step === 'pick' && (
            <>
              <div className="card p-4 bg-slate-50/40">
                <div className="text-xs font-bold text-slate-600 mb-2">Recipients ({selected.size} / {maxRecipients})</div>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <input
                    className="input uppercase"
                    placeholder="State (e.g. WA)"
                    maxLength={2}
                    value={stateFilter}
                    onChange={(e) => setStateFilter(e.target.value.toUpperCase())}
                  />
                  <input
                    type="number"
                    className="input"
                    min={1}
                    max={500}
                    value={maxRecipients}
                    onChange={(e) => setMaxRecipients(Number(e.target.value) || 50)}
                  />
                </div>
                <button onClick={selectVisible} className="btn-outline text-xs mb-2">
                  Select first {Math.min(filteredPool.length, maxRecipients - selected.size)}
                </button>
                <div className="max-h-64 overflow-y-auto space-y-1.5 -mx-1 px-1">
                  {pool === null && (
                    <div className="text-sm text-slate-400 py-3 inline-flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" /> Loading…
                    </div>
                  )}
                  {filteredPool.map((p) => (
                    <label key={p.parcel_key} className="flex items-center gap-2 text-sm py-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selected.has(p.parcel_key)}
                        onChange={() => toggleParcel(p.parcel_key)}
                        className="accent-brand-500"
                      />
                      <span className="font-mono text-xs text-slate-500 truncate flex-1">
                        {p.address.replace(/^\d+\s/, '••• ')} · {p.city}, {p.state}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  onClick={() => setStep('confirm')}
                  disabled={selected.size === 0}
                  className="btn-primary text-sm disabled:opacity-40"
                >
                  Continue ({selected.size})
                </button>
              </div>
            </>
          )}

          {step === 'confirm' && (
            <>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Campaign name</label>
                <input
                  className="input w-full"
                  value={campaignName}
                  onChange={(e) => setCampaignName(e.target.value)}
                />
              </div>

              <div>
                <div className="text-xs font-bold text-slate-600 mb-2">Return address (you)</div>
                <div className="grid grid-cols-1 gap-2">
                  <input
                    className="input"
                    placeholder="Full name (e.g. Matt Gerrish)"
                    value={from.name}
                    onChange={(e) => setFrom({ ...from, name: e.target.value })}
                  />
                  <input
                    className="input"
                    placeholder="Street address"
                    value={from.address_line1}
                    onChange={(e) => setFrom({ ...from, address_line1: e.target.value })}
                  />
                  <div className="grid grid-cols-3 gap-2">
                    <input
                      className="input col-span-2"
                      placeholder="City"
                      value={from.address_city}
                      onChange={(e) => setFrom({ ...from, address_city: e.target.value })}
                    />
                    <input
                      className="input uppercase"
                      placeholder="ST"
                      maxLength={2}
                      value={from.address_state}
                      onChange={(e) => setFrom({ ...from, address_state: e.target.value.toUpperCase() })}
                    />
                  </div>
                  <input
                    className="input"
                    placeholder="ZIP"
                    maxLength={10}
                    value={from.address_zip}
                    onChange={(e) => setFrom({ ...from, address_zip: e.target.value })}
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Lob requires a deliverable return address. Saved locally for next time.
                </p>
              </div>

              <div className="card p-4 bg-brand-50/60 border-brand-100 text-sm">
                <div className="font-semibold text-brand-navy">Ready to send</div>
                <ul className="mt-1 text-slate-700 space-y-0.5">
                  <li>Template: <strong>{template.name}</strong> ({template.size})</li>
                  <li>Recipients: <strong>{selected.size}</strong></li>
                  <li>Estimated cost: ~${(selected.size * 0.49).toFixed(2)} at $0.49/postcard</li>
                </ul>
              </div>

              {error && (
                <div className="card p-3 text-sm text-rose-700 border-rose-200 bg-rose-50 inline-flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" /> {error}
                </div>
              )}

              <div className="flex justify-between gap-2">
                {!skipPick && (
                  <button onClick={() => setStep('pick')} className="btn-outline text-sm">
                    Back to recipients
                  </button>
                )}
                <button
                  onClick={onSend}
                  disabled={!canSend || sending}
                  className="btn-primary text-sm disabled:opacity-40 ml-auto"
                >
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  {sending ? 'Sending…' : `Send ${selected.size} postcard${selected.size === 1 ? '' : 's'}`}
                </button>
              </div>
            </>
          )}

          {step === 'sent' && result && (
            <div className="text-center py-6">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-emerald-50 text-emerald-600 mb-4">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <h3 className="font-display text-2xl font-extrabold text-brand-navy">Campaign sent</h3>
              <p className="mt-2 text-slate-600">
                <strong>{result.sent}</strong> postcard{result.sent === 1 ? '' : 's'} dispatched.
                {result.errors > 0 && <> <strong className="text-rose-600">{result.errors}</strong> failed.</>}
              </p>
              <p className="mt-3 text-xs text-slate-500">
                See the campaign log on the <strong>Campaigns</strong> tab.
              </p>
              <button onClick={onClose} className="mt-6 btn-primary">Done</button>
            </div>
          )}

          {step === 'failed' && (
            <div className="text-center py-6">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-rose-50 text-rose-600 mb-4">
                <AlertCircle className="w-7 h-7" />
              </div>
              <h3 className="font-display text-2xl font-extrabold text-brand-navy">Send failed</h3>
              <p className="mt-2 text-slate-600 max-w-md mx-auto">{error || 'Unknown error'}</p>
              <button onClick={() => setStep('confirm')} className="mt-6 btn-outline">Try again</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
