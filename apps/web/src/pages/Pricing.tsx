import { Fragment } from 'react';
import { Check, Minus, ShieldCheck, RefreshCw, ArrowRight } from 'lucide-react';
import Seo from '../components/Seo';
import { Link } from 'react-router-dom';

const tiers = [
  {
    name: 'Free',
    price: '$0',
    cadence: 'forever',
    blurb: 'Get a feel for the data before you commit.',
    features: [
      'Browse partial addresses',
      '50 signal previews / month',
      'Daily email digest',
      'Public-record sources only',
    ],
    cta: 'Start free',
    highlight: false,
  },
  {
    name: 'Metro',
    price: '$29',
    cadence: 'per month',
    blurb: 'Pick one metro and own it.',
    features: [
      'Full addresses + ownership history',
      'One metro area',
      'Unlimited saved alerts',
      'Instant alerts',
      'Export to CSV',
    ],
    cta: 'Pick a metro',
    highlight: true,
  },
  {
    name: 'Nationwide',
    price: '$99',
    cadence: 'per month',
    blurb: 'All 50 states. API access. The lot.',
    features: [
      'Everything in Metro',
      'All 50 states',
      'Polygon search',
      'API access (1k req/day)',
      'Priority support',
    ],
    cta: 'Go nationwide',
    highlight: false,
  },
];

type Cell = boolean | string;

const compare: { section: string; rows: { label: string; free: Cell; metro: Cell; nation: Cell }[] }[] = [
  {
    section: 'Coverage',
    rows: [
      { label: 'Geographic scope', free: '1 metro preview', metro: '1 metro', nation: 'All 50 states' },
      { label: 'Signal types', free: 'Public records only', metro: 'All 10 sources', nation: 'All 10 sources' },
      { label: 'Counties tracked', free: '247', metro: '247', nation: '247' },
    ],
  },
  {
    section: 'Search & filters',
    rows: [
      { label: 'State / metro / county / ZIP', free: true, metro: true, nation: true },
      { label: 'Equity %, price, source filters', free: true, metro: true, nation: true },
      { label: 'Map polygon search', free: false, metro: false, nation: true },
      { label: 'Saved searches', free: '1', metro: 'Unlimited', nation: 'Unlimited' },
    ],
  },
  {
    section: 'Alerts',
    rows: [
      { label: 'Daily email digest', free: true, metro: true, nation: true },
      { label: 'Instant alerts', free: false, metro: true, nation: true },
      { label: 'Webhook delivery', free: false, metro: false, nation: true },
    ],
  },
  {
    section: 'Data access',
    rows: [
      { label: 'Full address visible', free: false, metro: true, nation: true },
      { label: 'Owner mailing address', free: false, metro: true, nation: true },
      { label: 'Ownership history', free: false, metro: true, nation: true },
      { label: 'CSV export', free: false, metro: 'Up to 500/mo', nation: 'Unlimited' },
      { label: 'REST API access', free: false, metro: false, nation: '1,000 req/day' },
    ],
  },
  {
    section: 'Support',
    rows: [
      { label: 'Email support', free: true, metro: true, nation: true },
      { label: 'Priority response', free: false, metro: false, nation: true },
    ],
  },
];

const faq = [
  {
    q: 'Can I switch between Metro and Nationwide?',
    a: 'Yes — upgrade or downgrade anytime from your account page. Pro-rated, no contract.',
  },
  {
    q: 'Do you scrape MLS / Zillow / Redfin?',
    a: 'No. We only ingest public-record sources (county recorders, treasurers, courts) and licensed APIs (ATTOM, InvestorLift). Where a source ToS prohibits scraping, we use their RSS or skip them.',
  },
  {
    q: 'Are alerts real-time?',
    a: 'Most county records refresh nightly, so "instant" means your alert fires within minutes of our scrape pipeline ingesting a new record. End-to-end latency is typically <24h from filing to your inbox.',
  },
  {
    q: 'What\'s your refund policy?',
    a: '14-day money-back guarantee on any paid tier, no questions asked. Just email us.',
  },
  {
    q: 'Will you ever sell or share my data?',
    a: 'Never. Your saved searches, alert history, and account info stay with you.',
  },
];

export default function Pricing() {
  return (
    <>
      <Seo title="Pricing" description="$29 metro · $99 nationwide. Cancel anytime." />

      {/* Hero */}
      <section className="container-page pt-16 pb-12 text-center max-w-3xl mx-auto">
        <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">Pricing</p>
        <h1 className="mt-2 font-display text-5xl font-extrabold text-brand-navy">
          Fair, flat pricing.
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          No per-lead surcharges. No annual lock-ins. Cancel anytime.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-4 text-sm text-slate-600">
          <span className="inline-flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-brand-500" /> 14-day money-back
          </span>
          <span className="inline-flex items-center gap-1.5">
            <RefreshCw className="w-4 h-4 text-brand-500" /> Switch tiers anytime
          </span>
        </div>
      </section>

      {/* Tiers */}
      <section className="container-page pb-16">
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {tiers.map((t, i) => (
            <div
              key={t.name}
              className={`card card-hover p-7 flex flex-col relative animate-fade-in-up ${
                t.highlight ? 'border-brand-500 ring-4 ring-brand-100 shadow-brand md:-translate-y-2' : ''
              }`}
              style={{ animationDelay: `${i * 80}ms` }}
            >
              {t.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 pill bg-brand-500 text-white shadow-md whitespace-nowrap">
                  Most popular
                </div>
              )}
              <h3 className="font-display text-xl font-bold text-brand-navy">{t.name}</h3>
              <p className="text-sm text-slate-500 mt-1">{t.blurb}</p>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="font-display text-5xl font-extrabold text-brand-navy">{t.price}</span>
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
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Comparison table */}
      <section className="container-page py-16 border-t border-slate-100">
        <div className="text-center max-w-2xl mx-auto">
          <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">What you get</p>
          <h2 className="mt-2 font-display text-3xl sm:text-4xl font-extrabold text-brand-navy">
            Plan comparison
          </h2>
        </div>
        <div className="mt-10 card overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left p-4 font-semibold text-slate-500"> </th>
                <th className="p-4 text-center font-display font-bold text-brand-navy w-[18%]">Free</th>
                <th className="p-4 text-center font-display font-bold text-brand-navy w-[18%] bg-brand-50/40">
                  Metro
                </th>
                <th className="p-4 text-center font-display font-bold text-brand-navy w-[18%]">Nationwide</th>
              </tr>
            </thead>
            <tbody>
              {compare.map((section) => (
                <Fragment key={section.section}>
                  <tr className="bg-slate-50/40">
                    <td colSpan={4} className="p-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider">
                      {section.section}
                    </td>
                  </tr>
                  {section.rows.map((row) => (
                    <tr key={row.label} className="border-b border-slate-100 last:border-b-0">
                      <td className="p-4 text-slate-700">{row.label}</td>
                      <td className="p-4 text-center"><CellRender v={row.free} /></td>
                      <td className="p-4 text-center bg-brand-50/40"><CellRender v={row.metro} /></td>
                      <td className="p-4 text-center"><CellRender v={row.nation} /></td>
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* FAQ */}
      <section className="container-page py-16 border-t border-slate-100">
        <div className="text-center max-w-2xl mx-auto">
          <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">Questions</p>
          <h2 className="mt-2 font-display text-3xl sm:text-4xl font-extrabold text-brand-navy">
            Frequently asked
          </h2>
        </div>
        <div className="mt-10 max-w-3xl mx-auto space-y-3">
          {faq.map((f, i) => (
            <details key={i} className="card p-5 group">
              <summary className="font-display font-bold text-slate-900 cursor-pointer list-none flex items-center justify-between gap-4">
                {f.q}
                <span className="text-brand-500 text-xl font-light group-open:rotate-45 transition-transform">+</span>
              </summary>
              <p className="mt-3 text-sm text-slate-600">{f.a}</p>
            </details>
          ))}
        </div>
        <div className="mt-12 text-center">
          <p className="text-sm text-slate-500">
            Still have questions?{' '}
            <Link to="/about" className="text-brand-600 hover:underline font-semibold">
              Read the about page
            </Link>{' '}
            or email{' '}
            <a href="mailto:hello@onlyoffmarkets.com" className="text-brand-600 hover:underline font-semibold">
              hello@onlyoffmarkets.com
            </a>
            .
          </p>
        </div>
      </section>
    </>
  );
}

function CellRender({ v }: { v: Cell }) {
  if (v === true) return <Check className="w-5 h-5 text-brand-500 inline-block" />;
  if (v === false) return <Minus className="w-5 h-5 text-slate-300 inline-block" />;
  return <span className="text-slate-700 font-semibold">{v}</span>;
}
