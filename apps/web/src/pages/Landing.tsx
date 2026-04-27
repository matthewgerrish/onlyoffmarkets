import { Link } from 'react-router-dom';
import { ArrowRight, Radar, MapPin, Bell, Database, ShieldCheck } from 'lucide-react';
import Seo from '../components/Seo';
import { LogoMark } from '../components/Logo';
import { SOURCE_LABELS } from '../lib/sources';

export default function Landing() {
  return (
    <>
      <Seo
        title="Every off-market lead in one feed"
        description="OnlyOffMarkets aggregates preforeclosures, tax delinquencies, probate, FSBO, REO and more — public-record signals from all 50 states."
      />

      <section className="relative overflow-hidden bg-gradient-to-b from-brand-50/60 to-white">
        <div className="container-page relative pt-20 pb-24 lg:pt-28 lg:pb-32">
          <div className="grid lg:grid-cols-[1.2fr_1fr] gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-slate-200 text-xs text-slate-600 mb-6 shadow-sm">
                <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
                <span>12,847 signals ingested in the last 24h</span>
              </div>
              <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-brand-navy leading-[1.02]">
                Every off-market lead<br />
                <span className="text-brand-500">in one feed.</span>
              </h1>
              <p className="mt-6 text-lg text-slate-600 max-w-xl">
                Preforeclosures, tax delinquencies, probate filings, FSBO, REO, auctions, code violations.
                Public-record signals from all 50 states — with email alerts the moment they hit.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/search" className="btn-primary">
                  Explore the feed <ArrowRight className="w-4 h-4" />
                </Link>
                <Link to="/sources" className="btn-outline">See data sources</Link>
              </div>
              <p className="mt-4 text-xs text-slate-500">
                Signals, not listings. We never claim a property is for sale unless its source confirms it.
              </p>
            </div>

            <div className="relative flex items-center justify-center">
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(29,108,242,0.25),transparent_60%)]" />
              <LogoMark size={260} className="relative drop-shadow-[0_24px_48px_rgba(10,107,214,0.35)]" />
            </div>
          </div>

          <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Counties tracked', value: '247' },
              { label: 'Active signals', value: '1.2M' },
              { label: 'Source feeds', value: '42' },
              { label: 'Avg lead age', value: '< 18h' },
            ].map((s) => (
              <div key={s.label} className="card p-5">
                <div className="font-display font-bold text-3xl text-slate-900">{s.value}</div>
                <div className="text-xs text-slate-500 mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="container-page py-20">
        <h2 className="font-display text-3xl sm:text-4xl font-extrabold text-brand-navy">
          Built for investors who hate paying retail.
        </h2>
        <div className="mt-10 grid md:grid-cols-3 gap-5">
          {[
            { icon: Radar, title: 'Every distress signal', body: 'NODs, trustee sales, tax rolls, probate, FSBO, REO — pulled from public records and structured into one schema.' },
            { icon: MapPin, title: 'Search any geography', body: 'Filter by state, metro, county, ZIP, or draw a polygon. PostGIS-backed, fast even on 100k+ signals.' },
            { icon: Bell, title: 'Alerts that fire fast', body: 'Get an email the moment a new signal matches your saved search. Daily digest or instant.' },
            { icon: Database, title: 'Transparent sources', body: 'Every signal links back to its public-record origin. No mystery scoring, no black boxes.' },
            { icon: ShieldCheck, title: 'Compliance-first', body: 'No MLS scraping, no protected-class filtering, no spam. We respect ToS and Fair Housing.' },
            { icon: ArrowRight, title: 'Fair pricing', body: '$29/mo for one metro, $99/mo nationwide. Cancel anytime. No per-lead surcharges.' },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="card p-6 hover:border-brand-300 hover:shadow-brand transition-all">
              <div className="w-10 h-10 rounded-full bg-brand-50 text-brand-600 inline-flex items-center justify-center">
                <Icon className="w-5 h-5" />
              </div>
              <h3 className="mt-4 font-display font-bold text-slate-900">{title}</h3>
              <p className="mt-2 text-sm text-slate-600">{body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="container-page py-16 border-t border-slate-100">
        <h2 className="font-display text-2xl font-bold text-slate-900">Sources we ingest</h2>
        <p className="mt-2 text-sm text-slate-600">All public-record or opt-in. Full source list and methodology on the <Link to="/sources" className="text-brand-600 hover:underline">Sources page</Link>.</p>
        <div className="mt-6 flex flex-wrap gap-2">
          {Object.values(SOURCE_LABELS).map((s) => (
            <span key={s} className="pill bg-slate-100 text-slate-700 border border-slate-200">{s}</span>
          ))}
        </div>
      </section>
    </>
  );
}
