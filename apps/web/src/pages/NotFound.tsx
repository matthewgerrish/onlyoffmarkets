import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="container-page py-24 text-center">
      <div className="font-display font-bold text-slate-300 text-6xl">404</div>
      <h1 className="mt-2 font-display text-3xl font-extrabold text-slate-900">Page not found</h1>
      <Link to="/" className="mt-6 btn-primary inline-flex">Back to home</Link>
    </div>
  );
}
