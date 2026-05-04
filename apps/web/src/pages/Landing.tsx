import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight, Radar, MapPin, Bell, Database, ShieldCheck,
  Gavel, Receipt, Scale, Home, Building2, FileX, Mail, Wand2, Search as SearchIcon,
} from 'lucide-react';
import Seo from '../components/Seo';
import HeroMockup from '../components/HeroMockup';
import { getCoverage, CoverageSummary } from '../lib/api';

function compactNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`.replace('.0k', 'k');
  return String(n);
}

export default function Landing() {
  const [cov, setCov] = useState<CoverageSummary | null>(null);
  useEffect(() => {
    getCoverage().then(setCov).catch(() => {});
  }, []);

  return (
    <>
      <Seo
        title="Every off-market lead in one feed"
        description="OnlyOffMarkets aggregates preforeclosures, tax delinquencies, probate, FSBO, REO and more — public-record signals from all 50 states."
      />

      {/* HERO */}
      <section className="relative overflow-hidden bg-gradient-to-b from-brand-50/60 via-white to-white">
        <div className="absolute inset-x-0 top-0 h-[520px] bg-[radial-gradient(ellipse_at_top,rgba(29,108,242,0.15),transparent_70%)] pointer-events-none" />
        <div className="container-page relative pt-16 pb-20 lg:pt-24 lg:pb-28">
          <div className="grid lg:grid-cols-[1.1fr_1fr] gap-12 lg:gap-16 items-center">
            <div className="animate-fade-in-up">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-slate-200 text-xs text-slate-600 mb-6 shadow-sm animate-pop-in" style={{ animationDelay: '120ms' }}>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-medium">12,847 signals ingested in the last 24h</span>
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
                <Link to="/analyzer" className="btn-outline">
                  Recon any address →
                </Link>
              </div>
              <p className="mt-4 text-xs text-slate-500">
                Signals, not listings. We never claim a property is for sale unless its source confirms it.
              </p>
            </div>

            <div className="relative animate-fade-in-up" style={{ animationDelay: '180ms' }}>
              <HeroMockup />
            </div>
          </div>

          {/* Stats strip — live from /off-market/_/coverage */}
          <div className="mt-16 lg:mt-20 grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
            {[
              { label: 'Active signals', value: cov ? compactNumber(cov.total_parcels) : '—' },
              { label: 'States covered', value: cov ? String(cov.states_covered) : '—' },
              { label: 'Source feeds', value: '19' },
              { label: 'Avg lead age', value: '< 24h' },
            ].map((s, i) => (
              <div
                key={s.label}
                className="card card-hover p-5 animate-fade-in-up"
                style={{ animationDelay: `${260 + i * 80}ms` }}
              >
                <div className="font-display font-bold text-3xl text-brand-navy">{s.value}</div>
                <div className="text-xs text-slate-500 mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="container-page py-20 border-t border-slate-100">
        <div className="max-w-2xl">
          <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">How it works</p>
          <h2 className="mt-2 font-display text-3xl sm:text-4xl font-extrabold text-brand-navy">
            From public record to your inbox in under 24 hours.
          </h2>
        </div>
        <div className="mt-12 grid md:grid-cols-3 gap-5">
          {[
            {
              step: '01',
              title: 'We ingest the records',
              body: 'Every county recorder, treasurer, court, and licensed feed — pulled into a single canonical schema. 1 req/sec, robots.txt respected.',
            },
            {
              step: '02',
              title: 'We dedupe by parcel',
              body: 'A property in pre-foreclosure AND vacant AND probate is one record with three flags — not three duplicates. APN-keyed.',
            },
            {
              step: '03',
              title: 'You search or get alerts',
              body: 'Filter by state, metro, county, ZIP, equity %, source. Save the filter. Get an email the moment a new match hits.',
            },
          ].map(({ step, title, body }, i) => (
            <div
              key={step}
              className="card card-hover p-6 relative overflow-hidden animate-fade-in-up"
              style={{ animationDelay: `${i * 90}ms` }}
            >
              <div className="absolute -right-6 -top-6 font-display font-extrabold text-7xl text-brand-50 select-none">
                {step}
              </div>
              <div className="relative">
                <div className="text-xs font-mono font-bold text-brand-500">{step}</div>
                <h3 className="mt-2 font-display font-bold text-slate-900">{title}</h3>
                <p className="mt-2 text-sm text-slate-600">{body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* SOURCES GRID */}
      <section className="bg-slate-50/60 border-y border-slate-100">
        <div className="container-page py-20">
          <div className="flex items-end justify-between gap-4 flex-wrap">
            <div className="max-w-2xl">
              <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">Coverage</p>
              <h2 className="mt-2 font-display text-3xl sm:text-4xl font-extrabold text-brand-navy">
                Ten sources, one schema.
              </h2>
              <p className="mt-3 text-slate-600">
                Every signal links back to its public-record origin. Methodology and legal posture on the{' '}
                <Link to="/sources" className="text-brand-600 hover:underline font-semibold">Sources page</Link>.
              </p>
            </div>
          </div>

          <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
            {[
              { icon: Gavel,      title: 'Preforeclosure',   sub: 'NOD / NTS filings' },
              { icon: Scale,      title: 'Trustee sales',    sub: 'Sheriff & auction' },
              { icon: Receipt,    title: 'Tax delinquent',   sub: 'County treasurer' },
              { icon: FileX,      title: 'Probate',          sub: 'Superior court' },
              { icon: Home,       title: 'FSBO',             sub: 'RSS + opt-in feeds' },
              { icon: Building2,  title: 'Bank-owned (REO)', sub: 'HomePath / HomeSteps' },
              { icon: Mail,       title: 'Absentee owners',  sub: 'Assessor mismatch' },
              { icon: ShieldCheck,title: 'Code violations',  sub: 'City enforcement' },
              { icon: Wand2,      title: 'Wholesaler',       sub: 'Partner APIs' },
              { icon: SearchIcon, title: 'Motivated seller', sub: 'Stale-DOM heuristic' },
            ].map(({ icon: Icon, title, sub }, i) => (
              <div
                key={title}
                className="card card-hover p-4 flex items-start gap-3 animate-fade-in-up"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <div className="w-9 h-9 rounded-lg bg-brand-50 text-brand-600 inline-flex items-center justify-center shrink-0">
                  <Icon className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="font-display font-bold text-sm text-slate-900">{title}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* WHY US */}
      <section className="container-page py-20">
        <div className="max-w-2xl">
          <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">Why investors switch</p>
          <h2 className="mt-2 font-display text-3xl sm:text-4xl font-extrabold text-brand-navy">
            Built for investors who hate paying retail.
          </h2>
        </div>
        <div className="mt-10 grid md:grid-cols-3 gap-5">
          {[
            { icon: Radar, title: 'Every distress signal', body: 'NODs, trustee sales, tax rolls, probate, FSBO, REO — pulled from public records and structured into one schema.' },
            { icon: MapPin, title: 'Search any geography', body: 'Filter by state, metro, county, ZIP, or draw a polygon. PostGIS-backed, fast even on 100k+ signals.' },
            { icon: Bell, title: 'Alerts that fire fast', body: 'Get an email the moment a new signal matches your saved search. Daily digest or instant.' },
            { icon: Database, title: 'Transparent sources', body: 'Every signal links back to its public-record origin. No mystery scoring, no black boxes.' },
            { icon: ShieldCheck, title: 'Compliance-first', body: 'No MLS scraping, no protected-class filtering, no spam. We respect ToS and Fair Housing.' },
            { icon: ArrowRight, title: 'Fair pricing', body: '$29/mo for one metro, $99/mo nationwide. Cancel anytime. No per-lead surcharges.' },
          ].map(({ icon: Icon, title, body }, i) => (
            <div
              key={title}
              className="card card-hover p-6 animate-fade-in-up"
              style={{ animationDelay: `${i * 70}ms` }}
            >
              <div className="w-10 h-10 rounded-full bg-brand-50 text-brand-600 inline-flex items-center justify-center">
                <Icon className="w-5 h-5" />
              </div>
              <h3 className="mt-4 font-display font-bold text-slate-900">{title}</h3>
              <p className="mt-2 text-sm text-slate-600">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="container-page pb-24">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-navy via-brand-700 to-brand-500 px-8 py-14 sm:px-14 sm:py-16 text-white">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.18),transparent_50%)]" />
          <div className="relative grid lg:grid-cols-[1.4fr_1fr] gap-8 items-center">
            <div>
              <h2 className="font-display text-3xl sm:text-4xl font-extrabold leading-tight">
                Stop chasing list-prices.<br />
                Start where the deals are.
              </h2>
              <p className="mt-4 text-white/80 max-w-lg">
                Free preview of the feed. No credit card. Upgrade when you want full addresses,
                instant alerts, and CSV exports.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row lg:flex-col gap-3 lg:items-end">
              <Link
                to="/search"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full bg-white text-brand-navy font-semibold hover:bg-brand-50 transition-colors"
              >
                Browse the live feed <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/pricing"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full bg-white/10 text-white font-semibold border border-white/30 hover:bg-white/15 transition-colors"
              >
                See pricing
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
