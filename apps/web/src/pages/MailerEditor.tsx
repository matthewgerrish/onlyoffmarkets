import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Eye, Code } from 'lucide-react';
import Seo from '../components/Seo';
import PostcardPreview from '../components/PostcardPreview';
import QRMaker from '../components/QRMaker';
import { createTemplate } from '../lib/mailers';

const STARTER_FRONT = `<html><body style="margin:0;font-family:Helvetica,sans-serif;width:6in;height:4in;background:#0f1f3d;color:#fff;display:flex;align-items:center;justify-content:center;text-align:center;">
  <div>
    <h1 style="font-size:48px;margin:0 0 14px;color:#1d6cf2">CASH OFFER</h1>
    <p style="font-size:18px;margin:0;letter-spacing:2px">No fees · No repairs · 14-day close</p>
  </div>
</body></html>`;

const STARTER_BACK = `<html><body style="margin:0;font-family:Helvetica,sans-serif;width:6in;height:4in;padding:0.3in;box-sizing:border-box;font-size:14px;position:relative;">
  <p>Hi {{to.name}},</p>
  <p>I'm reaching out about your property at {{property_address}}. I buy houses for cash — no fees, no repairs, no agents.</p>
  <p>Scan the QR code or call to chat.</p>
  <p style="margin-top:0.25in;">— {{from.name}}</p>
  <!-- QR placeholder — replace src with the data URI from the QR maker below -->
  <img src="QR_CODE_DATA_URI_HERE" style="position:absolute;bottom:0.3in;right:0.3in;width:0.9in;height:0.9in;" alt="qr" />
</body></html>`;

export default function MailerEditor() {
  const nav = useNavigate();
  const [name, setName] = useState('Untitled template');
  const [description, setDescription] = useState('');
  const [size, setSize] = useState<'4x6' | '6x9' | '6x11'>('4x6');
  const [frontHtml, setFrontHtml] = useState(STARTER_FRONT);
  const [backHtml, setBackHtml] = useState(STARTER_BACK);
  const [qrUrl, setQrUrl] = useState('');
  const [view, setView] = useState<'preview' | 'code'>('preview');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const { id } = await createTemplate({
        name,
        description: description || null,
        front_html: frontHtml,
        back_html: backHtml,
        size,
        qr_url: qrUrl || null,
      });
      nav('/mailers');
      console.log('saved', id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Seo title="New mailer template" />
      <div className="container-page py-8">
        <Link to="/mailers" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600">
          <ArrowLeft className="w-4 h-4" /> Back to mailers
        </Link>

        <div className="mt-4 flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0">
            <h1 className="font-display text-3xl font-extrabold text-brand-navy">New mailer template</h1>
            <p className="text-slate-600 mt-1">Design once. Send to any group of leads.</p>
          </div>
          <button
            onClick={onSave}
            disabled={saving || !name}
            className="btn-primary disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving…' : 'Save template'}
          </button>
        </div>

        {error && (
          <div className="mt-4 card p-4 text-sm text-rose-700 border-rose-200 bg-rose-50">
            {error}
          </div>
        )}

        <div className="mt-6 grid lg:grid-cols-[1fr_1.4fr] gap-6 items-start">
          {/* Left: meta + editors */}
          <div className="space-y-5">
            <div className="card p-5 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Name</label>
                <input className="input w-full" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Description</label>
                <input
                  className="input w-full"
                  placeholder="What this template is for…"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Postcard size</label>
                <select className="input w-full" value={size} onChange={(e) => setSize(e.target.value as any)}>
                  <option value="4x6">4×6 (cheapest)</option>
                  <option value="6x9">6×9</option>
                  <option value="6x11">6×11 (premium)</option>
                </select>
              </div>
            </div>

            <QRMaker initialUrl={qrUrl} onChange={setQrUrl} />

            <div className="card p-5">
              <div className="text-xs uppercase tracking-wider font-bold text-slate-400 mb-3">Front HTML</div>
              <textarea
                className="w-full font-mono text-xs bg-slate-50 border border-slate-200 rounded-lg p-3 min-h-[160px]"
                value={frontHtml}
                onChange={(e) => setFrontHtml(e.target.value)}
                spellCheck={false}
              />
            </div>

            <div className="card p-5">
              <div className="text-xs uppercase tracking-wider font-bold text-slate-400 mb-3">
                Back HTML
              </div>
              <textarea
                className="w-full font-mono text-xs bg-slate-50 border border-slate-200 rounded-lg p-3 min-h-[200px]"
                value={backHtml}
                onChange={(e) => setBackHtml(e.target.value)}
                spellCheck={false}
              />
              <p className="text-[11px] text-slate-500 mt-2">
                Merge fields supported: <code className="font-mono">{'{{to.name}}'}</code>, <code className="font-mono">{'{{property_address}}'}</code>, <code className="font-mono">{'{{property_city}}'}</code>, <code className="font-mono">{'{{from.name}}'}</code>.
              </p>
            </div>
          </div>

          {/* Right: live preview */}
          <div className="lg:sticky lg:top-20">
            <div className="card p-5">
              <div className="flex items-center justify-between gap-3 mb-4">
                <div className="text-xs uppercase tracking-wider font-bold text-slate-400">Live preview</div>
                <div className="flex bg-slate-100 rounded-full p-1 text-xs font-semibold">
                  <button
                    onClick={() => setView('preview')}
                    className={`px-3 py-1.5 rounded-full inline-flex items-center gap-1.5 transition-colors ${
                      view === 'preview' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500'
                    }`}
                  >
                    <Eye className="w-3.5 h-3.5" /> Preview
                  </button>
                  <button
                    onClick={() => setView('code')}
                    className={`px-3 py-1.5 rounded-full inline-flex items-center gap-1.5 transition-colors ${
                      view === 'code' ? 'bg-white text-brand-navy shadow-sm' : 'text-slate-500'
                    }`}
                  >
                    <Code className="w-3.5 h-3.5" /> Source
                  </button>
                </div>
              </div>

              {view === 'preview' && (
                <PostcardPreview frontHtml={frontHtml} backHtml={backHtml} size={size} />
              )}
              {view === 'code' && (
                <pre className="text-[11px] font-mono bg-slate-900 text-slate-100 rounded-lg p-3 overflow-auto max-h-[480px]">
{`-- FRONT --
${frontHtml}

-- BACK --
${backHtml}`}
                </pre>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
