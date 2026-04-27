import { Check } from 'lucide-react';
import Seo from '../components/Seo';

const tiers = [
  {
    name: 'Free',
    price: '$0',
    cadence: 'forever',
    features: ['Browse partial addresses', '50 signal previews / month', 'Daily email digest', 'Public-record sources only'],
    cta: 'Start free',
    highlight: false,
  },
  {
    name: 'Metro',
    price: '$29',
    cadence: 'per month',
    features: ['Full addresses + ownership history', 'One metro area', 'Unlimited saved alerts', 'Instant alerts', 'Export to CSV'],
    cta: 'Pick a metro',
    highlight: true,
  },
  {
    name: 'Nationwide',
    price: '$99',
    cadence: 'per month',
    features: ['Everything in Metro', 'All 50 states', 'Polygon search', 'API access (1k req/day)', 'Priority support'],
    cta: 'Go nationwide',
    highlight: false,
  },
];

export default function Pricing() {
  return (
    <>
      <Seo title="Pricing" description="$29 metro · $99 nationwide. Cancel anytime." />
      <div className="container-page py-16">
        <div className="text-center max-w-2xl mx-auto">
          <h1 className="font-display text-5xl font-extrabold text-slate-900">fair, flat pricing.</h1>
          <p className="mt-4 text-lg text-slate-600">No per-lead surcharges. No annual lock-ins. Cancel anytime.</p>
        </div>

        <div className="mt-14 grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {tiers.map((t) => (
            <div
              key={t.name}
              className={`card p-7 flex flex-col ${
                t.highlight ? 'border-brand-500 ring-4 ring-brand-100 shadow-brand' : ''
              }`}
            >
              {t.highlight && (
                <div className="pill bg-brand-500 text-white mb-3 self-start">Most popular</div>
              )}
              <h3 className="font-display text-xl font-bold text-slate-900">{t.name}</h3>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="font-display text-5xl font-extrabold text-slate-900">{t.price}</span>
                <span className="text-slate-500 text-sm">{t.cadence}</span>
              </div>
              <ul className="mt-6 space-y-2.5 text-sm text-slate-700 flex-1">
                {t.features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-brand-500 mt-0.5 shrink-0" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <button className={`mt-6 ${t.highlight ? 'btn-primary' : 'btn-outline'}`}>
                {t.cta}
              </button>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
