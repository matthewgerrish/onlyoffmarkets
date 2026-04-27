import Seo from '../components/Seo';

const sources = [
  { name: 'County recorder NOD / preforeclosure filings', method: 'Per-county scrapers', coverage: 'Top 100 metros (expanding)', notes: 'Public county recorder data.' },
  { name: 'Trustee / sheriff sale schedules', method: 'County clerk + statewide aggregators', coverage: 'National', notes: 'Public, structured.' },
  { name: 'Tax-delinquent rolls', method: 'County treasurer sites', coverage: 'National (annual + quarterly refresh)', notes: 'Some counties require FOIA.' },
  { name: 'Probate filings', method: 'County superior court PACER-equivalents', coverage: 'National (slow refresh)', notes: 'Often paywalled at source.' },
  { name: 'For sale by owner (FSBO)', method: 'Public RSS feeds and ToS-allowed sources', coverage: 'National', notes: 'We honor robots.txt and source ToS.' },
  { name: 'Bank-owned (REO)', method: 'HomePath, HomeSteps, bank portals', coverage: 'National', notes: 'Stable, structured feeds.' },
  { name: 'Auction listings', method: 'Auction.com, Hubzu, Xome', coverage: 'National', notes: 'Public listings.' },
  { name: 'Absentee owners', method: 'Assessor mailing-address vs property-address mismatch', coverage: 'National', notes: 'Top-of-funnel signal.' },
  { name: 'Code violations', method: 'Major-city code-enforcement portals', coverage: 'Top 100 cities', notes: 'Strong distress signal.' },
  { name: 'Wholesaler assignments', method: 'Partner APIs and direct intake', coverage: 'National (paid sources)', notes: 'High-quality, attribution preserved.' },
];

export default function Sources() {
  return (
    <>
      <Seo title="Data sources" description="What we ingest, how we ingest it, and our compliance posture." />
      <div className="container-page py-12">
        <h1 className="font-display text-4xl font-extrabold text-slate-900">data sources</h1>
        <p className="mt-3 text-slate-600 max-w-2xl">
          Every signal in OnlyOffMarkets links back to a public-record or opt-in source.
          We do not scrape MLS data. We honor robots.txt and source terms of service.
        </p>

        <div className="mt-8 card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 text-left">
              <tr>
                <th className="p-4 font-semibold">Source</th>
                <th className="p-4 font-semibold">Method</th>
                <th className="p-4 font-semibold">Coverage</th>
                <th className="p-4 font-semibold">Notes</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.name} className="border-t border-slate-100">
                  <td className="p-4 font-semibold text-slate-900">{s.name}</td>
                  <td className="p-4 text-slate-600">{s.method}</td>
                  <td className="p-4 text-slate-600">{s.coverage}</td>
                  <td className="p-4 text-slate-500">{s.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-10 card p-6 bg-brand-50 border-brand-100">
          <h2 className="font-display font-bold text-slate-900">What we don't do</h2>
          <ul className="mt-3 list-disc list-inside text-sm text-slate-700 space-y-1">
            <li>We never claim a property is "for sale" unless its source confirms it.</li>
            <li>We never filter or rank by Fair Housing protected class.</li>
            <li>We never email anyone who hasn't opted in.</li>
            <li>We never expose owner personal data on free tiers.</li>
          </ul>
        </div>
      </div>
    </>
  );
}
