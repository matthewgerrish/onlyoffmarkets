import { MapPin } from 'lucide-react';

/**
 * A faux topographic / parcel map preview. Pure SVG, no Mapbox dependency yet.
 * Looks like a real map without making a network call.
 */
export default function MapPlaceholder({ label }: { label?: string }) {
  return (
    <div className="relative aspect-video rounded-xl overflow-hidden border border-slate-200 bg-gradient-to-br from-brand-50 via-slate-50 to-emerald-50">
      <svg
        viewBox="0 0 800 450"
        className="absolute inset-0 w-full h-full"
        aria-hidden="true"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(15,31,61,0.06)" strokeWidth="1" />
          </pattern>
          <linearGradient id="land" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e0efff" />
            <stop offset="100%" stopColor="#dff5e8" />
          </linearGradient>
        </defs>

        {/* base land */}
        <rect width="800" height="450" fill="url(#land)" />
        <rect width="800" height="450" fill="url(#grid)" />

        {/* a wandering "river" */}
        <path
          d="M 0 280 C 120 240, 240 320, 360 270 C 480 220, 600 280, 800 240"
          stroke="#bfd9ff"
          strokeWidth="14"
          fill="none"
          strokeLinecap="round"
        />

        {/* "roads" */}
        <path d="M 0 150 L 800 170" stroke="rgba(15,31,61,0.18)" strokeWidth="2.5" />
        <path d="M 200 0 L 220 450" stroke="rgba(15,31,61,0.18)" strokeWidth="2.5" />
        <path d="M 540 0 L 560 450" stroke="rgba(15,31,61,0.12)" strokeWidth="2" />
        <path d="M 0 360 L 800 380" stroke="rgba(15,31,61,0.12)" strokeWidth="2" />

        {/* parcel polygons */}
        {[
          { x: 240, y: 180, w: 90, h: 60 },
          { x: 340, y: 180, w: 70, h: 60 },
          { x: 240, y: 250, w: 60, h: 70 },
          { x: 310, y: 250, w: 100, h: 70 },
          { x: 420, y: 180, w: 80, h: 90 },
          { x: 420, y: 280, w: 80, h: 60 },
        ].map((p, i) => (
          <rect
            key={i}
            x={p.x}
            y={p.y}
            width={p.w}
            height={p.h}
            fill="rgba(255,255,255,0.65)"
            stroke="rgba(15,31,61,0.18)"
            strokeWidth="1.5"
          />
        ))}

        {/* highlight target parcel */}
        <rect
          x={310}
          y={250}
          width={100}
          height={70}
          fill="rgba(29,108,242,0.18)"
          stroke="#1d6cf2"
          strokeWidth="2.5"
        />
      </svg>

      {/* center pin */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-full pointer-events-none">
        <div className="relative">
          <div className="absolute inset-0 rounded-full bg-brand-500/30 blur-md scale-150" />
          <div className="relative w-10 h-10 rounded-full bg-brand-500 text-white flex items-center justify-center shadow-lg">
            <MapPin className="w-5 h-5" />
          </div>
          <div className="absolute left-1/2 -translate-x-1/2 -bottom-1 w-1 h-3 bg-brand-700" />
        </div>
      </div>

      {/* watermark */}
      <div className="absolute bottom-2 right-3 text-[10px] font-mono text-slate-500/80 bg-white/70 backdrop-blur px-2 py-0.5 rounded">
        {label ?? 'Map preview · Mapbox integration pending'}
      </div>
    </div>
  );
}
