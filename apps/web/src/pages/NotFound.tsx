import { Link } from 'react-router-dom';
import { Compass, Search, Home } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="container-page py-20 sm:py-32 text-center max-w-xl mx-auto">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-brand-50 text-brand-500 mb-6">
        <Compass className="w-8 h-8" />
      </div>
      <div className="font-display font-extrabold text-7xl sm:text-8xl text-slate-200 leading-none">404</div>
      <h1 className="mt-3 font-display text-3xl font-extrabold text-brand-navy">Off the map</h1>
      <p className="mt-3 text-slate-600">
        That URL doesn't match a parcel, alert, or page in our index.
        Try the feed — there's plenty there.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link to="/" className="btn-outline">
          <Home className="w-4 h-4" /> Home
        </Link>
        <Link to="/search" className="btn-primary">
          <Search className="w-4 h-4" /> Search the feed
        </Link>
      </div>
    </div>
  );
}
