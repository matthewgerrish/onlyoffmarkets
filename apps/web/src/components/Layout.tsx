import { useState } from 'react';
import { Outlet, NavLink, Link, useLocation } from 'react-router-dom';
import { Search, Bell, DollarSign, Database, Info, Mail, Menu, X, Coins, Crown } from 'lucide-react';
import Logo from './Logo';
import TokenBadge from './TokenBadge';
import MembershipBadge from './MembershipBadge';

/** Primary nav — kept short so the bar fits on standard laptop widths. */
const nav = [
  { to: '/search', label: 'Search', icon: Search },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/mailers', label: 'Mailers', icon: Mail },
  { to: '/tokens', label: 'Tokens', icon: Coins },
  { to: '/membership', label: 'Membership', icon: Crown },
  { to: '/pricing', label: 'Pricing', icon: DollarSign },
];

/** Secondary nav — folded into mobile drawer + footer only. */
const navSecondary = [
  { to: '/sources', label: 'Sources', icon: Database },
  { to: '/about', label: 'About', icon: Info },
];

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <header className="sticky top-0 z-40 bg-white/85 backdrop-blur border-b border-slate-100 overflow-hidden">
        <div className="container-page flex h-16 items-center justify-between gap-2 min-w-0">
          <Link
            to="/"
            aria-label="OnlyOffMarkets home"
            className="shrink-0 sm:-my-4 inline-flex items-center min-w-0"
          >
            {/* Phone: icon + tight wordmark · Tablet/desktop: full */}
            <span className="sm:hidden">
              <Logo size={48} wordmarkSize={18} showTld={false} />
            </span>
            <span className="hidden sm:inline-flex lg:hidden">
              <Logo size={64} wordmarkSize={24} />
            </span>
            <span className="hidden lg:inline-flex">
              <Logo size={72} wordmarkSize={28} />
            </span>
          </Link>

          <nav className="hidden lg:flex items-center gap-0.5 min-w-0 overflow-hidden">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-sm font-semibold whitespace-nowrap transition-colors hover:bg-brand-50 hover:text-brand-600 ${
                    isActive ? 'text-brand-600 bg-brand-50' : 'text-slate-700'
                  }`
                }
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                <span className="hidden xl:inline">{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-1.5 shrink-0">
            <span className="hidden lg:inline-flex"><MembershipBadge /></span>
            <span className="hidden sm:inline-flex"><TokenBadge /></span>
            <span className="sm:hidden"><TokenBadge compact /></span>
            <Link
              to="/membership"
              className="btn-primary text-xs whitespace-nowrap hidden xl:inline-flex !px-3 !py-1.5"
            >
              Subscribe
            </Link>
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
      />

      <main className="flex-1">
        <div key={location.pathname} className="animate-fade-in">
          <Outlet />
        </div>
      </main>

      <footer className="border-t border-slate-100 mt-16 bg-slate-50">
        <div className="container-page py-10 grid sm:grid-cols-2 gap-6 items-center">
          <div className="flex items-center gap-3">
            <Logo size={32} wordmarkSize={18} />
          </div>
          <div className="text-sm text-slate-500 sm:text-right flex flex-wrap gap-x-4 gap-y-2 sm:justify-end">
            <Link to="/sources" className="hover:text-brand-600">Data sources</Link>
            <Link to="/about" className="hover:text-brand-600">Compliance</Link>
            <Link to="/pricing" className="hover:text-brand-600">Pricing</Link>
            <span>© {new Date().getFullYear()} OnlyOffMarkets</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

function MobileDrawer({
  open,
  onClose,
  currentPath,
}: {
  open: boolean;
  onClose: () => void;
  currentPath: string;
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
          <Link to="/search" onClick={onClose} className="btn-outline w-full justify-center">Sign in</Link>
          <Link to="/pricing" onClick={onClose} className="btn-primary w-full justify-center">Subscribe</Link>
        </div>
      </div>
    </div>
  );
}
