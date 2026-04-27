import { Outlet, NavLink, Link } from 'react-router-dom';
import { Search, Bell, DollarSign, Database, Info } from 'lucide-react';
import Logo from './Logo';

const nav = [
  { to: '/search', label: 'Search', icon: Search },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/sources', label: 'Sources', icon: Database },
  { to: '/pricing', label: 'Pricing', icon: DollarSign },
  { to: '/about', label: 'About', icon: Info },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      <header className="sticky top-0 z-40 bg-white/85 backdrop-blur border-b border-slate-100">
        <div className="container-page flex h-16 items-center justify-between">
          <Link to="/" aria-label="OnlyOffMarkets home" className="shrink-0 -my-4">
            <Logo size={80} wordmarkSize={32} />
          </Link>
          <nav className="hidden lg:flex items-center gap-1">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `btn-ghost text-sm whitespace-nowrap ${isActive ? 'text-brand-600 bg-brand-50' : ''}`
                }
              >
                <Icon className="w-4 h-4" />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2 shrink-0">
            <Link to="/search" className="btn-ghost text-sm hidden sm:inline-flex whitespace-nowrap">Sign in</Link>
            <Link to="/pricing" className="btn-primary text-sm whitespace-nowrap">Subscribe</Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-slate-100 mt-16 bg-slate-50">
        <div className="container-page py-10 grid sm:grid-cols-2 gap-6 items-center">
          <div className="flex items-center gap-3">
            <Logo size={32} />
          </div>
          <div className="text-sm text-slate-500 sm:text-right flex flex-wrap gap-4 sm:justify-end">
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
