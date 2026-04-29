import { useEffect, useState } from 'react';
import { Bell, Trash2, Plus, MapPin, Filter, Zap, Mail as MailIcon, X } from 'lucide-react';
import Seo from '../components/Seo';
import { ALL_SOURCES, SOURCE_LABELS } from '../lib/sources';
import type { ApiSource } from '../lib/api';
import { useToast } from '../components/Toast';

interface Alert {
  id: string;
  scope: string;
  state: string | null;
  county: string | null;
  sources: ApiSource[];
  minScore: number;
  cadence: 'instant' | 'daily' | 'weekly';
  email: string;
  created_at: string;
}

const STORAGE_KEY = 'oom_alerts_v1';

const seed: Alert[] = [
  { id: 'a1', scope: 'Pierce County, WA', state: 'WA', county: 'Pierce',
    sources: ['preforeclosure', 'tax-lien'], minScore: 40, cadence: 'daily',
    email: 'matt-gerrish@hotmail.com', created_at: new Date().toISOString() },
  { id: 'a2', scope: 'Maricopa County, AZ', state: 'AZ', county: 'Maricopa',
    sources: ['auction'], minScore: 30, cadence: 'instant',
    email: 'matt-gerrish@hotmail.com', created_at: new Date().toISOString() },
];

function loadAlerts(): Alert[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore */
  }
  return seed;
}

function saveAlerts(alerts: Alert[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(alerts));
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showForm, setShowForm] = useState(false);
  const toast = useToast();

  useEffect(() => {
    setAlerts(loadAlerts());
  }, []);

  const remove = (id: string) => {
    const next = alerts.filter((x) => x.id !== id);
    setAlerts(next);
    saveAlerts(next);
    toast.info('Alert removed');
  };

  const addAlert = (a: Omit<Alert, 'id' | 'created_at'>) => {
    const next: Alert[] = [
      { ...a, id: 'a_' + Math.random().toString(36).slice(2, 10), created_at: new Date().toISOString() },
      ...alerts,
    ];
    setAlerts(next);
    saveAlerts(next);
    setShowForm(false);
    toast.success(`Alert saved · ${a.cadence} cadence`);
  };

  return (
    <>
      <Seo title="Email alerts" />

      {/* Banner */}
      <div className="relative bg-gradient-to-br from-brand-navy via-brand-700 to-brand-500 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.15),transparent_55%)]" />
        <div className="container-page relative py-10">
          <div className="flex items-center justify-between gap-6 flex-wrap">
            <div>
              <h1 className="font-display text-4xl font-extrabold inline-flex items-center gap-3">
                <Bell className="w-8 h-8" /> alerts
              </h1>
              <p className="mt-2 text-white/80 max-w-2xl">
                Get an email the moment a new signal matches your saved search.
                Daily digest or instant.
              </p>
            </div>
            <button onClick={() => setShowForm(true)} className="btn-primary">
              <Plus className="w-4 h-4" /> New alert
            </button>
          </div>
        </div>
      </div>

      <div className="container-page py-8">
        {alerts.length === 0 && (
          <div className="card p-12 text-center text-slate-400">
            <Bell className="w-6 h-6 mx-auto mb-2 opacity-40" />
            No alerts yet. Click <strong className="text-slate-700">New alert</strong> to start.
          </div>
        )}

        <div className="space-y-3">
          {alerts.map((a) => (
            <div key={a.id} className="card p-5 flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <MapPin className="w-4 h-4 text-brand-500" />
                  <span className="font-display font-bold text-slate-900">{a.scope}</span>
                  <span className={`pill ${
                    a.cadence === 'instant' ? 'bg-rose-50 text-rose-700 border border-rose-100' :
                    a.cadence === 'daily' ? 'bg-amber-50 text-amber-700 border border-amber-100' :
                    'bg-slate-100 text-slate-600 border border-slate-200'
                  }`}>{a.cadence}</span>
                </div>
                <div className="mt-2 text-sm text-slate-600 inline-flex items-center gap-3 flex-wrap">
                  <span className="inline-flex items-center gap-1">
                    <Filter className="w-3.5 h-3.5 text-slate-400" /> ≥ {a.minScore} score
                  </span>
                  <span className="inline-flex items-center gap-1 text-slate-500">
                    {a.sources.length === ALL_SOURCES.length
                      ? 'all sources'
                      : `${a.sources.length} source${a.sources.length === 1 ? '' : 's'}`}
                  </span>
                  <span className="inline-flex items-center gap-1 text-slate-500">
                    <MailIcon className="w-3.5 h-3.5" /> {a.email}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {a.sources.slice(0, 6).map((s) => (
                    <span key={s} className="pill bg-brand-50 text-brand-700 border border-brand-100">
                      {SOURCE_LABELS[s]}
                    </span>
                  ))}
                  {a.sources.length > 6 && (
                    <span className="pill bg-slate-100 text-slate-600 border border-slate-200">
                      +{a.sources.length - 6} more
                    </span>
                  )}
                </div>
              </div>
              <button onClick={() => remove(a.id)} className="btn-ghost text-slate-400 hover:text-rose-500">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {showForm && <NewAlertModal onClose={() => setShowForm(false)} onSave={addAlert} />}
    </>
  );
}

function NewAlertModal({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (a: Omit<Alert, 'id' | 'created_at'>) => void;
}) {
  const [state, setState] = useState('');
  const [county, setCounty] = useState('');
  const [minScore, setMinScore] = useState(40);
  const [cadence, setCadence] = useState<'instant' | 'daily' | 'weekly'>('daily');
  const [email, setEmail] = useState('');
  const [enabledSources, setEnabledSources] = useState<Set<ApiSource>>(new Set(ALL_SOURCES));

  const toggle = (s: ApiSource) => {
    setEnabledSources((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  const submit = () => {
    const scope = county && state ? `${county} County, ${state}` : state ? state : 'All states';
    onSave({
      scope,
      state: state || null,
      county: county || null,
      sources: Array.from(enabledSources),
      minScore,
      cadence,
      email,
    });
  };

  const valid = email.includes('@') && enabledSources.size > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-6 bg-slate-900/40 backdrop-blur-sm">
      <div className="w-full sm:max-w-xl bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl max-h-[92vh] overflow-y-auto">
        <div className="sticky top-0 z-10 bg-white border-b border-slate-100 px-5 py-3 flex items-center justify-between">
          <h2 className="font-display font-bold text-slate-900 inline-flex items-center gap-2">
            <Zap className="w-4 h-4 text-brand-500" /> New alert
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">State</label>
              <input
                className="input w-full uppercase"
                maxLength={2}
                placeholder="WA"
                value={state}
                onChange={(e) => setState(e.target.value.toUpperCase())}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">County (optional)</label>
              <input
                className="input w-full"
                placeholder="Pierce"
                value={county}
                onChange={(e) => setCounty(e.target.value)}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between text-xs font-semibold text-slate-600 mb-1">
              <span>Min deal score</span>
              <span className="font-mono text-brand-600">≥ {minScore}</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full accent-brand-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Cadence</label>
            <div className="grid grid-cols-3 gap-2">
              {(['instant', 'daily', 'weekly'] as const).map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setCadence(c)}
                  className={`py-2 rounded-full text-sm font-semibold border transition-colors capitalize ${
                    cadence === c
                      ? 'bg-brand-500 text-white border-brand-500'
                      : 'bg-white border-slate-200 text-slate-700 hover:border-brand-300'
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Email</label>
            <input
              type="email"
              className="input w-full"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-600">Sources ({enabledSources.size}/{ALL_SOURCES.length})</span>
              <button
                type="button"
                onClick={() =>
                  setEnabledSources(
                    enabledSources.size === ALL_SOURCES.length ? new Set() : new Set(ALL_SOURCES)
                  )
                }
                className="text-xs text-brand-600 font-semibold hover:underline"
              >
                {enabledSources.size === ALL_SOURCES.length ? 'Clear all' : 'Select all'}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              {ALL_SOURCES.map((s) => (
                <label key={s} className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enabledSources.has(s)}
                    onChange={() => toggle(s)}
                    className="accent-brand-500"
                  />
                  {SOURCE_LABELS[s]}
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="sticky bottom-0 bg-white border-t border-slate-100 px-5 py-3 flex justify-end gap-2">
          <button onClick={onClose} className="btn-outline text-sm">Cancel</button>
          <button onClick={submit} disabled={!valid} className="btn-primary text-sm disabled:opacity-40">
            Save alert
          </button>
        </div>
      </div>
    </div>
  );
}
