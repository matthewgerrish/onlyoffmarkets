import { useState } from 'react';
import { Mail, X, Loader2, Check, ExternalLink, ShieldCheck } from 'lucide-react';
import { requestMagicLink } from '../lib/auth';
import { useAuth } from './AuthContext';
import { useToast } from './Toast';

/** Magic-link sign-in dialog. Open it from the header or any 401 boundary. */
export default function LoginModal() {
  const { loginOpen, closeLogin } = useAuth();
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<{ live: boolean; devLink?: string } | null>(null);
  const toast = useToast();

  if (!loginOpen) return null;

  const onClose = () => {
    setEmail('');
    setSent(null);
    closeLogin();
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes('@')) {
      toast.error('Please enter a valid email');
      return;
    }
    setBusy(true);
    try {
      const r = await requestMagicLink(email);
      setSent({ live: r.live_email, devLink: r.dev_link });
    } catch (err) {
      toast.error((err as Error).message || 'Could not send sign-in email');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center bg-slate-900/40 backdrop-blur-sm p-0 sm:p-6 animate-fade-in"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl animate-slide-up overflow-hidden"
      >
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
          <div className="font-display font-bold text-slate-900 inline-flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-brand-500" /> Sign in
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {!sent ? (
          <form onSubmit={onSubmit} className="p-5">
            <p className="text-sm text-slate-600">
              We'll email a one-time link. No password to remember — your wallet,
              membership, and saved properties move with your email.
            </p>

            <label className="mt-4 block text-xs font-bold uppercase tracking-wider text-slate-500">
              Email
            </label>
            <div className="mt-1.5 relative">
              <Mail className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="email"
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@yourdomain.com"
                className="w-full bg-white border border-slate-200 rounded-full pl-9 pr-4 py-2.5 text-sm
                  text-slate-900 placeholder:text-slate-400
                  focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                required
                inputMode="email"
                autoComplete="email"
              />
            </div>

            <button
              type="submit"
              disabled={busy}
              className="mt-4 btn-primary w-full justify-center disabled:opacity-60"
            >
              {busy ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Sending…
                </>
              ) : (
                <>Send sign-in link</>
              )}
            </button>

            <p className="mt-3 text-[11px] text-slate-400 text-center">
              By signing in you agree to our terms. Email links expire in 15 minutes.
            </p>
          </form>
        ) : (
          <div className="p-5">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 mb-3">
              <Check className="w-6 h-6" />
            </div>
            <h3 className="font-display font-extrabold text-xl text-brand-navy">
              Check your inbox
            </h3>
            <p className="mt-1 text-sm text-slate-600">
              We sent a sign-in link to <strong>{email}</strong>. Click it from
              the same browser to come right back here.
            </p>
            {!sent.live && sent.devLink && (
              <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                <div className="font-bold flex items-center gap-1.5 mb-1">
                  <ExternalLink className="w-3.5 h-3.5" /> Dev mode — click your link
                </div>
                <a
                  href={sent.devLink}
                  className="break-all font-mono text-amber-900 hover:underline"
                >
                  {sent.devLink}
                </a>
                <p className="mt-2 text-amber-700">
                  Email isn't wired up (RESEND_API_KEY unset). Click the link
                  above directly to complete sign-in.
                </p>
              </div>
            )}
            <button onClick={onClose} className="mt-5 btn-outline w-full justify-center">
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
