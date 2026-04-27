import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, MapPin, Calendar, ExternalLink, Loader2,
  Bookmark, Bell, Share2, Hash, Building2,
} from 'lucide-react';
import Seo from '../components/Seo';
import { DealMeterDetail } from '../components/DealMeter';
import MapPlaceholder from '../components/MapPlaceholder';
import { getOffMarket, OffMarketDetailResponse } from '../lib/api';
import { SOURCE_LABELS, ALL_SOURCES } from '../lib/sources';
import { dealScore } from '../lib/score';

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

  const score = dealScore(p);
  const knownSources = new Set(ALL_SOURCES);
  const locationStr = [p.city, p.state, p.zip].filter(Boolean).join(', ');

  return (
    <>
      <Seo title={`${p.address}, ${p.city ?? ''}, ${p.state}`} />

      {/* Banner header — sets the page tone */}
      <div className="relative bg-gradient-to-br from-brand-navy via-brand-700 to-brand-500 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.15),transparent_55%)]" />
        <div className="container-page relative py-8">
          <Link to="/search" className="inline-flex items-center gap-1 text-sm text-white/70 hover:text-white">
            <ArrowLeft className="w-4 h-4" /> Back to feed
          </Link>

          <div className="mt-5 flex items-start justify-between gap-6 flex-wrap">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="pill bg-white/15 text-white border border-white/30 uppercase tracking-wider">
                  {score.band} · {score.total}
                </span>
                {p.owner_state && p.owner_state !== p.state && (
                  <span className="pill bg-white/10 text-white/90 border border-white/20">
                    Owner mailing address in {p.owner_state}
                  </span>
                )}
                {p.years_delinquent !== null && p.years_delinquent !== undefined && (
                  <span className="pill bg-white/10 text-white/90 border border-white/20">
                    {p.years_delinquent}y delinquent
                  </span>
                )}
              </div>
              <h1 className="mt-3 font-display text-3xl sm:text-4xl font-extrabold tracking-tight">
                {p.address}
              </h1>
              <div className="mt-1 text-white/80 inline-flex items-center gap-1.5">
                <MapPin className="w-4 h-4" />
                {locationStr}
                {p.county && <span className="text-white/60">· {p.county} County</span>}
              </div>
            </div>
            <div className="flex gap-2">
              <button className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 hover:bg-white/15 border border-white/20 text-sm font-semibold transition-colors">
                <Share2 className="w-4 h-4" /> Share
              </button>
              <button className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 hover:bg-white/15 border border-white/20 text-sm font-semibold transition-colors">
                <Bookmark className="w-4 h-4" /> Save
              </button>
              <button className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white text-brand-navy text-sm font-semibold hover:bg-brand-50 transition-colors">
                <Bell className="w-4 h-4" /> Add to alert
              </button>
            </div>
          </div>

          {/* Quick stat strip */}
          <div className="mt-7 grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Stat label="Active sources" value={String(p.source_tags.length)} />
            <Stat
              label="Default amount"
              value={p.default_amount ? `$${p.default_amount.toLocaleString()}` : '—'}
            />
            <Stat
              label="Lien"
              value={p.lien_amount ? `$${p.lien_amount.toLocaleString()}` : '—'}
            />
            <Stat
              label="Sale date"
              value={p.sale_date ? new Date(p.sale_date).toLocaleDateString() : '—'}
            />
          </div>
        </div>
      </div>

      <div className="container-page py-10">
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="card p-6">
              <div className="flex items-center justify-between gap-2">
                <h2 className="font-display font-bold text-slate-900">Active signals</h2>
                <span className="text-xs text-slate-500 font-mono">
                  {p.sources.length} record{p.sources.length === 1 ? '' : 's'}
                </span>
              </div>
              <div className="mt-4 space-y-3">
                {p.sources.length === 0 && (
                  <p className="text-sm text-slate-500">No raw source records yet.</p>
                )}
                {p.sources.map((s, i) => {
                  const label = knownSources.has(s.source as any)
                    ? SOURCE_LABELS[s.source as keyof typeof SOURCE_LABELS]
                    : s.source;
                  return (
                    <div
                      key={i}
                      className="border border-slate-200 rounded-xl p-4 bg-slate-50/60 hover:border-brand-300 hover:bg-brand-50/40 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div className="min-w-0">
                          <div className="font-semibold text-slate-900">{label}</div>
                          <div className="mt-1 text-xs text-slate-500 font-mono inline-flex items-center gap-1">
                            <Hash className="w-3 h-3" /> {s.source_id}
                          </div>
                        </div>
                        <div className="text-xs text-slate-500 inline-flex items-center gap-1 shrink-0">
                          <Calendar className="w-3 h-3" /> {new Date(s.scraped_at).toLocaleDateString()}
                        </div>
                      </div>
                      {s.source_url && (
                        <a
                          href={s.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-3 text-xs text-brand-600 inline-flex items-center gap-1 font-semibold hover:underline"
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
              <div className="mt-3">
                <MapPlaceholder label={`Parcel · ${p.county ?? p.city ?? p.state}`} />
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Approximate location — click to open in your county GIS viewer once Mapbox is wired up.
              </p>
            </div>

            <div className="card p-6">
              <h2 className="font-display font-bold text-slate-900">Comparable sales</h2>
              <div className="mt-3 grid sm:grid-cols-3 gap-3">
                {[
                  { addr: '••• ELM ST', sold: '$278,000', dist: '0.3 mi' },
                  { addr: '••• OAK AVE', sold: '$312,500', dist: '0.5 mi' },
                  { addr: '••• PINE LN', sold: '$295,000', dist: '0.7 mi' },
                ].map((c) => (
                  <div
                    key={c.addr}
                    className="border border-slate-200 rounded-xl p-3 hover:border-brand-300 transition-colors"
                  >
                    <div className="text-xs text-slate-400">{c.dist} away</div>
                    <div className="mt-1 font-display font-bold text-sm text-slate-900 truncate">
                      {c.addr}
                    </div>
                    <div className="mt-1 text-sm text-brand-600 font-semibold">{c.sold}</div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs text-slate-500">Demo comps — wired to public sale-price feeds in next iteration.</p>
            </div>
          </div>

          <aside className="space-y-4">
            <div className="card p-6">
              <DealMeterDetail score={score} />
            </div>

            <div className="card p-6">
              <h3 className="text-xs uppercase tracking-wide text-slate-400 font-bold flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5" /> Property details
              </h3>
              <dl className="mt-3 space-y-2 text-sm">
                {p.parcel_apn && <Row k="APN" v={p.parcel_apn} mono />}
                {p.estimated_value && (
                  <Row k="Est. value (AVM)" v={`$${p.estimated_value.toLocaleString()}`} />
                )}
                {p.assessed_value && (
                  <Row k="Assessed value" v={`$${p.assessed_value.toLocaleString()}`} />
                )}
                {p.loan_balance !== null && p.loan_balance !== undefined && (
                  <Row k="Loan balance" v={`$${p.loan_balance.toLocaleString()}`} />
                )}
                {(() => {
                  const ref = p.estimated_value ?? p.assessed_value;
                  if (ref && p.loan_balance !== null && p.loan_balance !== undefined && ref > 0) {
                    const ltv = (p.loan_balance / ref) * 100;
                    return <Row k="LTV" v={`${ltv.toFixed(0)}%`} />;
                  }
                  return null;
                })()}
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
                <Row k="Last updated" v={new Date(p.last_seen).toLocaleDateString()} />
              </dl>
            </div>

            <div className="card p-6 bg-gradient-to-br from-brand-50 to-white border-brand-100 text-sm text-slate-700">
              <div className="font-display font-bold text-brand-navy">Owner contact data</div>
              <p className="mt-1 text-slate-600">
                Mailing address, phone, and ownership history are available on paid plans.
              </p>
              <Link
                to="/pricing"
                className="mt-3 btn-primary text-sm w-full justify-center"
              >
                View pricing
              </Link>
            </div>
          </aside>
        </div>
      </div>
    </>
  );
}

function Row({ k, v, mono = false }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-500">{k}</dt>
      <dd className={`text-slate-900 font-semibold text-right ${mono ? 'font-mono' : ''}`}>{v}</dd>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white/10 border border-white/20 rounded-xl px-4 py-3 backdrop-blur-sm">
      <div className="text-[11px] uppercase tracking-wider text-white/60 font-semibold">{label}</div>
      <div className="mt-1 font-display font-bold text-xl text-white">{value}</div>
    </div>
  );
}
