import { Link } from 'react-router-dom';
import {
  ShieldCheck, Eye, Scale, Mail, Database, Lock, ArrowRight,
} from 'lucide-react';
import Seo from '../components/Seo';

const principles = [
  {
    icon: Database,
    title: 'Public records only',
    body: 'We do not scrape MLS data. Where source ToS prohibits scraping, we use licensed feeds or RSS — not workarounds.',
  },
  {
    icon: Scale,
    title: 'No Fair Housing violations',
    body: 'We never filter, rank, or infer based on race, family status, religion, or any protected class. Period.',
  },
  {
    icon: Mail,
    title: 'TCPA / CAN-SPAM compliant',
    body: 'Email alerts only fire to opted-in users. One-click unsubscribe on every email. No purchased lists.',
  },
  {
    icon: Eye,
    title: 'Signals, not listings',
    body: "We never claim a property is for sale unless its source confirms it. Every record links back to its origin.",
  },
  {
    icon: Lock,
    title: 'Owner data protected',
    body: 'Personal owner data is only on paid tiers, never redistributed, and removed on request within 72h.',
  },
  {
    icon: ShieldCheck,
    title: 'Robots.txt respected',
    body: 'Our scrapers exit if a source disallows access and identify themselves with a polite User-Agent.',
  },
];

export default function About() {
  return (
    <>
      <Seo title="About & compliance" />

      <div className="relative bg-gradient-to-br from-brand-navy via-brand-700 to-brand-500 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.15),transparent_55%)]" />
        <div className="container-page relative py-12">
          <h1 className="font-display text-4xl sm:text-5xl font-extrabold">about</h1>
          <p className="mt-3 text-white/85 max-w-2xl text-lg">
            OnlyOffMarkets aggregates public-record distress signals — preforeclosures,
            tax delinquencies, probate filings, code violations — into one searchable
            feed for real estate investors and agents.
          </p>
        </div>
      </div>

      <section className="container-page py-12">
        <div className="max-w-3xl">
          <p className="text-xs font-bold text-brand-500 uppercase tracking-wider">Our promise</p>
          <h2 className="mt-2 font-display text-3xl font-extrabold text-brand-navy">
            Operate cleanly. Tell on ourselves.
          </h2>
          <p className="mt-3 text-slate-600">
            Off-market data attracts cowboys. We try to do the opposite.
            Here's exactly what we do and don't do.
          </p>
        </div>

        <div className="mt-10 grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {principles.map(({ icon: Icon, title, body }) => (
            <div key={title} className="card p-6 hover:border-brand-300 hover:shadow-brand transition-all">
              <div className="w-10 h-10 rounded-full bg-brand-50 text-brand-600 inline-flex items-center justify-center">
                <Icon className="w-5 h-5" />
              </div>
              <h3 className="mt-3 font-display font-bold text-slate-900">{title}</h3>
              <p className="mt-2 text-sm text-slate-600">{body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="container-page py-12 border-t border-slate-100">
        <div className="card p-7 bg-gradient-to-br from-brand-50 to-white border-brand-100 max-w-3xl">
          <h2 className="font-display text-2xl font-bold text-brand-navy">Questions, removals, or partnerships?</h2>
          <p className="mt-2 text-slate-700">
            Email <a href="mailto:hello@onlyoffmarkets.com" className="text-brand-600 hover:underline font-semibold">hello@onlyoffmarkets.com</a>.
            We respond within one business day. For owner-record removals, include
            the property address and we'll process within 72 hours.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/sources" className="btn-outline">
              <Database className="w-4 h-4" /> See full source list
            </Link>
            <Link to="/pricing" className="btn-primary">
              View pricing <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
