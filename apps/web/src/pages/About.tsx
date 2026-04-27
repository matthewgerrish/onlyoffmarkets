import Seo from '../components/Seo';

export default function About() {
  return (
    <>
      <Seo title="About & compliance" />
      <div className="container-page py-12 max-w-3xl">
        <h1 className="font-display text-4xl font-extrabold text-slate-900">about</h1>
        <p className="mt-4 text-slate-600">
          OnlyOffMarkets aggregates public-record distress signals — preforeclosures, tax delinquencies, probate filings,
          code violations — into one searchable feed for real estate investors and agents.
        </p>

        <h2 className="mt-12 font-display text-2xl font-bold text-slate-900">Our compliance posture</h2>
        <ul className="mt-4 space-y-3 text-slate-700 text-sm">
          <li><strong className="text-slate-900">Public records only.</strong> We do not scrape MLS data. Where source ToS prohibits scraping, we use licensed feeds or RSS.</li>
          <li><strong className="text-slate-900">No Fair Housing violations.</strong> We never filter, rank, or infer based on protected classes.</li>
          <li><strong className="text-slate-900">TCPA / CAN-SPAM compliant.</strong> Alerts only fire to opted-in users. One-click unsubscribe on every email.</li>
          <li><strong className="text-slate-900">Signals, not listings.</strong> We never claim a property is for sale unless its source confirms it.</li>
          <li><strong className="text-slate-900">Owner data protected.</strong> Personal owner data is only available on paid tiers and is not redistributed.</li>
        </ul>
      </div>
    </>
  );
}
