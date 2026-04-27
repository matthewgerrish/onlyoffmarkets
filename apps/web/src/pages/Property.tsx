import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, MapPin, Calendar, ExternalLink, Loader2 } from 'lucide-react';
import Seo from '../components/Seo';
import SignalPill from '../components/SignalPill';
import { getOffMarket, OffMarketDetailResponse } from '../lib/api';
import { SOURCE_LABELS, tierFor, ALL_SOURCES } from '../lib/sources';

export default function Property() {
  const { id } = useParams();
  const [p, setP] = useState<OffMarketDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setP(null);
    setError(null);
    getOffMarket(decodeURIComponent(id))
      .then((d) => !cancelled && setP(d))
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <div className="container-page py-16">
        <Seo title="Not found" />
        <p className="text-slate-600">
          {error}. <Link to="/search" className="text-brand-600 hover:underline">Back to search</Link>
        </p>
      </div>
    );
  }

  if (!p) {
    return (
      <div className="container-page py-24 flex items-center justify-center text-slate-400">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading property…
      </div>
    );
  }

  const tier = tierFor(p.source_tags);
  const knownSources = new Set(ALL_SOURCES);

  return (
    <>
      <Seo title={`${p.address}, ${p.city ?? ''}, ${p.state}`} />
      <div className="container-page py-8">
        <Link to="/search" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600">
          <ArrowLeft className="w-4 h-4" /> Back to feed
        </Link>

        <div className="mt-4 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <SignalPill tier={tier} />
              {p.owner_state && p.owner_state !== p.state && (
                <span className="text-xs font-semibold text-slate-500">
                  owner mailing address in {p.owner_state}
                </span>
              )}
            </div>
            <h1 className="mt-2 font-display text-3xl font-extrabold text-slate-900">{p.address}</h1>
            <div className="text-slate-600 inline-flex items-center gap-1 mt-1">
              <MapPin className="w-4 h-4" />{' '}
              {[p.city, p.state, p.zip].filter(Boolean).join(', ')}
              {p.county && ` · ${p.county} County`}
            </div>
          </div>
          <div className="flex gap-2">
            <button className="btn-outline text-sm">Save</button>
            <button className="btn-primary text-sm">Add to alert</button>
          </div>
        </div>

        <div className="mt-8 grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="card p-6">
              <h2 className="font-display font-bold text-slate-900">Active signals</h2>
              <div className="mt-4 space-y-3">
                {p.sources.length === 0 && (
                  <p className="text-sm text-slate-500">No raw source records yet.</p>
                )}
                {p.sources.map((s, i) => {
                  const label = knownSources.has(s.source as any)
                    ? SOURCE_LABELS[s.source as keyof typeof SOURCE_LABELS]
                    : s.source;
                  return (
                    <div key={i} className="border border-slate-200 rounded-xl p-4 bg-slate-50/60">
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-semibold text-slate-900">{label}</div>
                        <div className="text-xs text-slate-500 inline-flex items-center gap-1">
                          <Calendar className="w-3 h-3" /> {new Date(s.scraped_at).toLocaleDateString()}
                        </div>
                      </div>
                      <div className="mt-1 text-xs text-slate-500 font-mono">{s.source_id}</div>
                      {s.source_url && (
                        <a
                          href={s.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-2 text-xs text-brand-600 inline-flex items-center gap-1 font-semibold hover:underline"
                        >
                          View source record <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="card p-6">
              <h2 className="font-display font-bold text-slate-900">Parcel map</h2>
              <div className="mt-3 aspect-video bg-slate-100 rounded-xl flex items-center justify-center text-slate-400 text-sm">
                Map preview — Mapbox integration pending
              </div>
            </div>
          </div>

          <aside className="space-y-4">
            <div className="card p-6">
              <h3 className="text-xs uppercase tracking-wide text-slate-400 font-bold">Property details</h3>
              <dl className="mt-3 space-y-2 text-sm">
                {p.parcel_apn && <Row k="APN" v={p.parcel_apn} />}
                {p.default_amount !== null && (
                  <Row k="Default amount" v={`$${p.default_amount.toLocaleString()}`} />
                )}
                {p.lien_amount !== null && (
                  <Row k="Lien amount" v={`$${p.lien_amount.toLocaleString()}`} />
                )}
                {p.years_delinquent !== null && (
                  <Row k="Years delinquent" v={String(p.years_delinquent)} />
                )}
                {p.asking_price !== null && (
                  <Row k="Asking price" v={`$${p.asking_price.toLocaleString()}`} />
                )}
                {p.sale_date && (
                  <Row k="Sale date" v={new Date(p.sale_date).toLocaleDateString()} />
                )}
                {p.vacancy_months !== null && (
                  <Row k="Vacancy" v={`${p.vacancy_months} months`} />
                )}
                <Row k="First seen" v={new Date(p.first_seen).toLocaleDateString()} />
              </dl>
            </div>
            <div className="card p-6 bg-brand-50 border-brand-100 text-sm text-slate-700">
              Owner contact data and full ownership history available on paid plans.
              <Link to="/pricing" className="block mt-2 text-brand-600 hover:underline font-semibold">
                View pricing →
              </Link>
            </div>
          </aside>
        </div>
      </div>
    </>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-500">{k}</dt>
      <dd className="text-slate-900 font-semibold text-right">{v}</dd>
    </div>
  );
}
