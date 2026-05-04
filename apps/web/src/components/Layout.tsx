import { useState, useRef, useEffect } from 'react';
import { Outlet, NavLink, Link, useLocation } from 'react-router-dom';
import { Search, Bell, DollarSign, Database, Info, Mail, Menu, X, Coins, Crown, Target, Bookmark } from 'lucide-react';
import Logo from './Logo';
import TokenBadge from './TokenBadge';
import MembershipBadge from './MembershipBadge';
import LoginModal from './LoginModal';
import AuthBootstrap from './AuthBootstrap';
import { useAuth } from './AuthContext';
import { useMembership } from './MembershipContext';
import { LogIn, LogOut, Settings } from 'lucide-react';

/** Primary nav — kept short so the bar fits on standard laptop widths.
 *  Membership lives on the crown badge (right side), not in the nav,
 *  to avoid the duplicate-Membership-link + Premium-badge collision
 *  at lg/xl breakpoints. */
const nav = [
  { to: '/search', label: 'Search', icon: Search },
  { to: '/analyzer', label: 'Underwrite', icon: Target },
  { to: '/watchlist', label: 'Watch', icon: Bookmark },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/mailers', label: 'Mailers', icon: Mail },
  { to: '/tokens', label: 'Tokens', icon: Coins },
];

/** Pricing moved to footer/secondary to keep primary nav lean. */

/** Secondary nav — folded into mobile drawer + footer only. */
const navSecondary = [
  { to: '/membership', label: 'Membership', icon: Crown },
  { to: '/pricing',    label: 'Pricing',    icon: DollarSign },
  { to: '/sources',    label: 'Sources',    icon: Database },
  { to: '/about',      label: 'About',      icon: Info },
];

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const { isAuthed, user, openLogin, signOut } = useAuth();
  const { isPaid } = useMembership();

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <AuthBootstrap />
      <LoginModal />
      <header className="sticky top-0 z-40 bg-white/85 backdrop-blur border-b border-slate-100">
        <div className="container-page flex h-16 items-center gap-2 min-w-0">
          {/* Logo — sized down progressively to leave room for the nav */}
          <Link
            to="/"
            aria-label="OnlyOffMarkets home"
            className="shrink-0 inline-flex items-center"
          >
            <span className="sm:hidden">
              <Logo size={44} wordmarkSize={16} showTld={false} />
            </span>
            <span className="hidden sm:inline-flex lg:hidden">
              <Logo size={56} wordmarkSize={20} />
            </span>
            <span className="hidden lg:inline-flex xl:hidden">
              <Logo size={48} wordmarkSize={18} showTld={false} />
            </span>
            <span className="hidden xl:inline-flex">
              <Logo size={56} wordmarkSize={22} />
            </span>
          </Link>

          {/* Primary nav — icon-only at lg, icon + label at xl. Each item
           *  carries a `title` so hover-tooltips reveal the label at lg. */}
          <nav className="hidden lg:flex items-center gap-0.5 ml-2 mr-auto min-w-0 overflow-hidden">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                title={label}
                className={({ isActive }) =>
                  `inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-sm font-semibold whitespace-nowrap transition-colors hover:bg-brand-50 hover:text-brand-600 ${
                    isActive ? 'text-brand-600 bg-brand-50' : 'text-slate-700'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="hidden xl:inline">{label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Spacer to push right cluster on mobile (no nav between) */}
          <div className="lg:hidden flex-1" />

          {/* Right-side cluster — Membership badge, Token badge, Avatar */}
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="hidden xl:inline-flex"><MembershipBadge /></span>
            <span className="hidden sm:inline-flex"><TokenBadge /></span>
            <span className="sm:hidden"><TokenBadge compact /></span>

            {/* Auth: signed-in users get an Avatar dropdown that
             *  consolidates email + membership manage + sign-out into
             *  one click target. Signed-out users get a Sign-in button. */}
            {isAuthed ? (
              <UserMenu user={user} signOut={signOut} />
            ) : (
              <button
                type="button"
                onClick={openLogin}
                title="Sign in"
                className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold text-slate-700 hover:bg-slate-100 whitespace-nowrap"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span className="hidden xl:inline">Sign in</span>
              </button>
            )}

            <button
              type="button"
              className="lg:hidden inline-flex items-center justify-center w-10 h-10 rounded-full text-slate-700 hover:bg-slate-100"
              onClick={() => setMenuOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile drawer */}
      <MobileDrawer
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        currentPath={location.pathname}
        isAuthed={isAuthed}
        isPaid={isPaid}
        userEmail={user?.email || null}
        onSignIn={() => {
          setMenuOpen(false);
          openLogin();
        }}
        onSignOut={async () => {
          setMenuOpen(false);
          await signOut();
        }}
      />

      <main className="flex-1">
        <div key={location.pathname} className="animate-fade-in">
          <Outlet />
        </div>
      </main>

      <footer className="border-t border-slate-100 mt-20 bg-gradient-to-b from-white to-slate-50">
        <div className="container-page py-14">
          <div className="grid lg:grid-cols-[2fr_1fr_1fr_1fr] gap-10 lg:gap-16">
            <div>
              <Logo size={56} wordmarkSize={22} />
              <p className="mt-4 text-sm text-slate-600 max-w-xs leading-relaxed">
                Every off-market lead in one feed. Public-record signals from
                all 50 states, scored, mapped, and ready to action.
              </p>
              <div className="mt-5 flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-[10px] font-bold uppercase tracking-wider">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Live
                </span>
                <span className="text-[11px] text-slate-400">
                  signals refreshed daily
                </span>
              </div>
            </div>

            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3">
                Product
              </div>
              <ul className="space-y-2 text-sm">
                <li><Link to="/search"     className="text-slate-600 hover:text-brand-600">Search</Link></li>
                <li><Link to="/analyzer"   className="text-slate-600 hover:text-brand-600">Underwrite</Link></li>
                <li><Link to="/watchlist"  className="text-slate-600 hover:text-brand-600">Watchlist</Link></li>
                <li><Link to="/alerts"     className="text-slate-600 hover:text-brand-600">Alerts</Link></li>
                <li><Link to="/mailers"    className="text-slate-600 hover:text-brand-600">Mailers</Link></li>
                <li><Link to="/tokens"     className="text-slate-600 hover:text-brand-600">Tokens</Link></li>
              </ul>
            </div>

            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3">
                Plans
              </div>
              <ul className="space-y-2 text-sm">
                <li><Link to="/membership" className="text-slate-600 hover:text-brand-600">Membership</Link></li>
                <li><Link to="/pricing"    className="text-slate-600 hover:text-brand-600">Pricing</Link></li>
                <li><Link to="/sources"    className="text-slate-600 hover:text-brand-600">Data sources</Link></li>
              </ul>
            </div>

            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-3">
                Company
              </div>
              <ul className="space-y-2 text-sm">
                <li><Link to="/about"      className="text-slate-600 hover:text-brand-600">About & compliance</Link></li>
                <li><a href="mailto:hello@onlyoffmarkets.com" className="text-slate-600 hover:text-brand-600">hello@onlyoffmarkets.com</a></li>
              </ul>
            </div>
          </div>

          <div className="mt-12 pt-6 border-t border-slate-200 flex items-center justify-between gap-4 flex-wrap">
            <div className="text-[11px] text-slate-400">
              © {new Date().getFullYear()} OnlyOffMarkets · Signals, not listings.
            </div>
            <div className="text-[11px] text-slate-400 inline-flex items-center gap-3">
              <span>Public-record data only.</span>
              <span className="opacity-50">·</span>
              <span>Built for investors, not gawkers.</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* Avatar + dropdown menu for authed users at md+ breakpoints. Keeps
 * the header tight by collapsing email + membership-manage + sign-out
 * into a single click target. */
function UserMenu({
  user,
  signOut,
}: {
  user: { email?: string | null } | null;
  signOut: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('click', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('click', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const email = user?.email || '';
  const initial = (email[0] || '?').toUpperCase();

  return (
    <div ref={ref} className="hidden md:inline-flex relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        title={email || 'Account'}
        className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white font-bold text-sm shadow-sm hover:shadow-brand transition-shadow"
        aria-label="Account menu"
        aria-haspopup="true"
        aria-expanded={open}
      >
        {initial}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-60 bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-fade-in-down z-50">
          <div className="px-4 py-3 border-b border-slate-100">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Signed in as
            </div>
            <div className="mt-0.5 text-sm font-semibold text-slate-900 truncate" title={email}>
              {email || '—'}
            </div>
          </div>
          <div className="py-1.5">
            <Link
              to="/membership"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-brand-50 hover:text-brand-700"
            >
              <Crown className="w-4 h-4 text-amber-500" /> Membership
            </Link>
            <Link
              to="/tokens"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-brand-50 hover:text-brand-700"
            >
              <Coins className="w-4 h-4 text-amber-500" /> Token wallet
            </Link>
            <Link
              to="/watchlist"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-brand-50 hover:text-brand-700"
            >
              <Bookmark className="w-4 h-4 text-amber-500" /> Watchlist
            </Link>
            <Link
              to="/alerts"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-brand-50 hover:text-brand-700"
            >
              <Settings className="w-4 h-4 text-slate-500" /> Alerts
            </Link>
          </div>
          <div className="border-t border-slate-100 py-1.5">
            <button
              type="button"
              onClick={() => { setOpen(false); void signOut(); }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-rose-600 hover:bg-rose-50"
            >
              <LogOut className="w-4 h-4" /> Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function MobileDrawer({
  open,
  onClose,
  currentPath,
  isAuthed,
  isPaid,
  userEmail,
  onSignIn,
  onSignOut,
}: {
  open: boolean;
  onClose: () => void;
  currentPath: string;
  isAuthed: boolean;
  isPaid: boolean;
  userEmail: string | null;
  onSignIn: () => void;
  onSignOut: () => void | Promise<void>;
}) {
  return (
    <div
      className={`fixed inset-0 z-50 lg:hidden transition-opacity ${
        open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
      }`}
      aria-hidden={!open}
    >
      {/* Backdrop */}
      <button
        type="button"
        aria-label="Close menu"
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Sheet */}
      <div
        className={`absolute right-0 top-0 bottom-0 w-[80%] max-w-sm bg-white shadow-2xl flex flex-col transition-transform ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between px-5 h-16 border-b border-slate-100">
          <Logo size={48} wordmarkSize={20} showTld={false} />
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="w-10 h-10 rounded-full inline-flex items-center justify-center text-slate-500 hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto py-3">
          {[...nav, ...navSecondary].map(({ to, label, icon: Icon }) => {
            const active = currentPath === to || currentPath.startsWith(to + '/');
            return (
              <Link
                key={to}
                to={to}
                onClick={onClose}
                className={`flex items-center gap-3 px-5 py-3 text-base font-semibold ${
                  active ? 'bg-brand-50 text-brand-700' : 'text-slate-700 hover:bg-slate-50'
                }`}
              >
                <Icon className="w-5 h-5" />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-slate-100 p-4 flex flex-col gap-2">
          {isAuthed ? (
            <>
              {userEmail && (
                <div className="text-[11px] text-slate-500 truncate text-center mb-1">
                  Signed in as <strong className="text-slate-700">{userEmail}</strong>
                </div>
              )}
              <button
                onClick={() => void onSignOut()}
                className="btn-outline w-full justify-center"
              >
                Sign out
              </button>
            </>
          ) : (
            <button onClick={onSignIn} className="btn-outline w-full justify-center">
              Sign in
            </button>
          )}
          {isPaid ? (
            <Link to="/membership" onClick={onClose} className="btn-outline w-full justify-center">
              Manage membership
            </Link>
          ) : (
            <Link to="/membership" onClick={onClose} className="btn-primary w-full justify-center">
              Subscribe
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
