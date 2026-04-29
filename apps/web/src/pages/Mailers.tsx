import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Mail, Plus, Send, Trash2, FileText, Megaphone, Target, X } from 'lucide-react';
import Seo from '../components/Seo';
import PostcardPreview from '../components/PostcardPreview';
import SendCampaignModal from '../components/SendCampaignModal';
import {
  listTemplates, deleteTemplate, listCampaigns,
  MailerTemplate, MailerCampaign,
} from '../lib/mailers';

type Tab = 'templates' | 'campaigns';

export default function Mailers() {
  const [searchParams, setSearchParams] = useSearchParams();
  const targetParcel = searchParams.get('parcel');
  const targetParcels = (searchParams.get('parcels') || '').split(',').filter(Boolean);
  const [tab, setTab] = useState<Tab>('templates');
  const [templates, setTemplates] = useState<MailerTemplate[] | null>(null);
  const [campaigns, setCampaigns] = useState<MailerCampaign[] | null>(null);
  const [lobMode, setLobMode] = useState<string>('mock');
  const [error, setError] = useState<string | null>(null);
  const [sendingTemplate, setSendingTemplate] = useState<MailerTemplate | null>(null);

  const load = () => {
    setError(null);
    listTemplates().then(setTemplates).catch((e) => setError(e.message));
    listCampaigns()
      .then(({ results, lob_mode }) => {
        setCampaigns(results);
        setLobMode(lob_mode);
      })
      .catch((e) => setError(e.message));
  };

  useEffect(() => {
    load();
  }, []);

  const onDelete = async (id: string) => {
    if (!confirm('Delete this template?')) return;
    await deleteTemplate(id);
    load();
  };

  return (
    <>
      <Seo title="Mailers" />

      {/* Banner */}
      <div className="relative bg-gradient-to-br from-brand-navy via-brand-700 to-brand-500 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.15),transparent_55%)]" />
        <div className="container-page relative py-12">
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="max-w-2xl">
              <h1 className="font-display text-4xl sm:text-5xl font-extrabold inline-flex items-center gap-3">
                <Mail className="w-8 h-8" /> mailers
              </h1>
              <p className="mt-3 text-white/80 text-base sm:text-lg">
                Send physical postcards to property owners — pre-made templates,
                custom HTML editor with QR codes, dispatched via Lob.
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <span className={`pill border ${lobMode === 'mock' ? 'bg-amber-400/15 border-amber-300/30 text-amber-100' : lobMode === 'test' ? 'bg-white/10 border-white/30' : 'bg-emerald-400/20 border-emerald-300/30 text-emerald-100'}`}>
                  Lob: {lobMode}
                </span>
                <span className="pill bg-white/10 border border-white/20 text-white/80">
                  4×6 from $0.49 / postcard
                </span>
                <span className="pill bg-white/10 border border-white/20 text-white/80">
                  Tracked delivery
                </span>
              </div>
            </div>
            <Link to="/mailers/new" className="btn-primary shrink-0">
              <Plus className="w-4 h-4" /> New template
            </Link>
          </div>
        </div>
      </div>

      <div className="container-page py-8">
        {(targetParcel || targetParcels.length > 0) && (
          <div className="mb-6 card p-5 bg-gradient-to-r from-brand-50 to-white border-brand-200 flex items-start gap-4">
            <div className="w-10 h-10 rounded-full bg-brand-100 text-brand-700 inline-flex items-center justify-center shrink-0">
              <Target className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-display font-bold text-slate-900">
                {targetParcels.length > 0
                  ? `Send to ${targetParcels.length} selected propert${targetParcels.length === 1 ? 'y' : 'ies'}`
                  : 'Send to one property'}
              </div>
              <p className="text-sm text-slate-600 mt-1">
                Pick a template below to dispatch the campaign.
              </p>
            </div>
            <button
              onClick={() => {
                searchParams.delete('parcel');
                searchParams.delete('parcels');
                setSearchParams(searchParams);
              }}
              className="text-slate-400 hover:text-slate-700 p-2 -m-2"
              aria-label="Clear target"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Tab switcher */}
        <div className="flex bg-slate-100 rounded-full p-1 text-sm font-semibold w-fit">
          <button
            onClick={() => setTab('templates')}
            className={`px-4 py-2 rounded-full inline-flex items-center gap-2 transition-colors ${tab === 'templates' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            <FileText className="w-4 h-4" /> Templates
            {templates && <span className="text-xs font-mono opacity-60">{templates.length}</span>}
          </button>
          <button
            onClick={() => setTab('campaigns')}
            className={`px-4 py-2 rounded-full inline-flex items-center gap-2 transition-colors ${tab === 'campaigns' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            <Megaphone className="w-4 h-4" /> Campaigns
            {campaigns && <span className="text-xs font-mono opacity-60">{campaigns.length}</span>}
          </button>
        </div>

        {error && (
          <div className="mt-6 card p-5 text-sm text-rose-700 border-rose-200 bg-rose-50">
            {error}
          </div>
        )}

        {tab === 'templates' && (
          <div className="mt-6">
            {templates === null && (
              <div className="grid lg:grid-cols-2 gap-5">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div
                    key={i}
                    className="card p-5 animate-fade-in"
                    style={{ animationDelay: `${i * 70}ms` }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 space-y-2">
                        <div className="skeleton h-4 w-1/2" />
                        <div className="skeleton h-3 w-3/4" />
                      </div>
                      <div className="skeleton h-7 w-16 rounded-full" />
                    </div>
                    <div className="skeleton mt-4 h-40" />
                  </div>
                ))}
              </div>
            )}
            {templates && templates.length === 0 && (
              <div className="card p-12 text-center text-slate-400">
                No templates yet. <Link to="/mailers/new" className="text-brand-600 font-semibold">Create one</Link>.
              </div>
            )}
            {templates && templates.length > 0 && (
              <div className="grid lg:grid-cols-2 gap-5">
                {templates.map((t, i) => (
                  <div
                    key={t.id}
                    className="card card-hover p-5 animate-fade-in-up"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-display font-bold text-slate-900">{t.name}</h3>
                          {t.is_preset && (
                            <span className="pill bg-brand-50 text-brand-700 border border-brand-100">Preset</span>
                          )}
                        </div>
                        {t.description && (
                          <p className="mt-1 text-sm text-slate-500">{t.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          onClick={() => setSendingTemplate(t)}
                          className="btn-primary text-xs"
                          title="Send a campaign with this template"
                        >
                          <Send className="w-3.5 h-3.5" /> Send
                        </button>
                        {!t.is_preset && (
                          <button
                            onClick={() => onDelete(t.id)}
                            className="btn-ghost text-slate-400 hover:text-rose-500"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="mt-4">
                      <PostcardPreview frontHtml={t.front_html} backHtml={t.back_html} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'campaigns' && (
          <div className="mt-6">
            {campaigns === null && (
              <div className="card overflow-hidden">
                <div className="bg-slate-50 px-4 py-3 flex gap-4 border-b border-slate-100">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="skeleton h-3 flex-1" />
                  ))}
                </div>
                {Array.from({ length: 4 }).map((_, i) => (
                  <div
                    key={i}
                    className="px-4 py-4 flex gap-4 border-b border-slate-100 last:border-0 animate-fade-in"
                    style={{ animationDelay: `${i * 70}ms` }}
                  >
                    {Array.from({ length: 5 }).map((_, j) => (
                      <div key={j} className="skeleton h-3.5 flex-1" />
                    ))}
                  </div>
                ))}
              </div>
            )}
            {campaigns && campaigns.length === 0 && (
              <div className="card p-12 text-center text-slate-400">
                <Send className="w-6 h-6 mx-auto mb-2 opacity-40" />
                No campaigns yet. From the search page, select properties and click <strong className="text-slate-700">Send mailer</strong>.
              </div>
            )}
            {campaigns && campaigns.length > 0 && (
              <div className="card overflow-x-auto">
                <table className="w-full text-sm min-w-[640px]">
                  <thead className="bg-slate-50 text-slate-500">
                    <tr>
                      <th className="text-left p-3 font-semibold">Campaign</th>
                      <th className="text-center p-3 font-semibold">Recipients</th>
                      <th className="text-center p-3 font-semibold">Sent</th>
                      <th className="text-center p-3 font-semibold">Errors</th>
                      <th className="text-left p-3 font-semibold">Status</th>
                      <th className="text-left p-3 font-semibold">Sent at</th>
                    </tr>
                  </thead>
                  <tbody>
                    {campaigns.map((c) => (
                      <tr key={c.id} className="border-t border-slate-100">
                        <td className="p-3 font-semibold text-slate-900">{c.name}</td>
                        <td className="p-3 text-center font-mono">{c.parcel_keys.length}</td>
                        <td className="p-3 text-center font-mono text-emerald-600">{c.sent_count}</td>
                        <td className="p-3 text-center font-mono text-rose-500">{c.error_count}</td>
                        <td className="p-3">
                          <span className={`pill ${
                            c.status === 'sent' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' :
                            c.status === 'failed' ? 'bg-rose-50 text-rose-700 border border-rose-100' :
                            'bg-amber-50 text-amber-700 border border-amber-100'
                          }`}>{c.status}</span>
                        </td>
                        <td className="p-3 text-slate-500 font-mono text-xs">
                          {c.sent_at ? new Date(c.sent_at).toLocaleString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {sendingTemplate && (
        <SendCampaignModal
          template={sendingTemplate}
          fixedParcelKey={targetParcel || undefined}
          prefilledKeys={targetParcels.length > 0 ? targetParcels : undefined}
          onClose={() => {
            setSendingTemplate(null);
            load();
          }}
        />
      )}
    </>
  );
}
