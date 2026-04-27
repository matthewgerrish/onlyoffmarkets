import { useState } from 'react';
import { Bell, Trash2, Plus } from 'lucide-react';
import Seo from '../components/Seo';

interface Alert {
  id: string;
  scope: string;
  sources: string[];
  minEquity: number;
  cadence: 'instant' | 'daily' | 'weekly';
}

const seed: Alert[] = [
  { id: 'a1', scope: 'Pierce County, WA', sources: ['Preforeclosure', 'Tax delinquent'], minEquity: 40, cadence: 'daily' },
  { id: 'a2', scope: 'Maricopa County, AZ', sources: ['Trustee sale'], minEquity: 30, cadence: 'instant' },
];

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>(seed);
  const remove = (id: string) => setAlerts((a) => a.filter((x) => x.id !== id));

  return (
    <>
      <Seo title="Email alerts" />
      <div className="container-page py-12">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="font-display text-4xl font-extrabold text-slate-900 inline-flex items-center gap-3">
              <Bell className="w-7 h-7 text-brand-500" /> alerts
            </h1>
            <p className="text-slate-600 mt-2">Get an email the moment a new signal matches your saved search.</p>
          </div>
          <button className="btn-primary">
            <Plus className="w-4 h-4" /> New alert
          </button>
        </div>

        <div className="mt-8 space-y-3">
          {alerts.length === 0 && (
            <div className="card p-12 text-center text-slate-400">No alerts yet.</div>
          )}
          {alerts.map((a) => (
            <div key={a.id} className="card p-5 flex items-center justify-between gap-4">
              <div>
                <div className="font-display font-bold text-slate-900">{a.scope}</div>
                <div className="text-sm text-slate-500 mt-1">
                  {a.sources.join(' · ')} · ≥ {a.minEquity}% equity ·{' '}
                  <span className="text-brand-600 font-semibold">{a.cadence}</span>
                </div>
              </div>
              <button onClick={() => remove(a.id)} className="btn-ghost text-slate-400 hover:text-rose-500">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
