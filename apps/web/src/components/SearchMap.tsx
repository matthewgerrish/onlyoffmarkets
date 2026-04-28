import { useEffect, useRef, useState } from 'react';
import mapboxgl, { Map as MapboxMap, Marker, Popup, LngLatBoundsLike } from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Link } from 'react-router-dom';
import { OffMarketRow } from '../lib/api';
import { dealScore, bandHex } from '../lib/score';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined;

interface Props {
  rows: OffMarketRow[];
  /** When set, that pin is highlighted + popup opened on mount */
  focusKey?: string | null;
}

export default function SearchMap({ rows, focusKey }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Filter rows that have coordinates
  const geoRows = rows.filter(
    (r) => typeof r.latitude === 'number' && typeof r.longitude === 'number'
  );

  // Initialize the map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    if (!MAPBOX_TOKEN) {
      setError('VITE_MAPBOX_TOKEN not set — add it to your environment to enable the map.');
      return;
    }
    mapboxgl.accessToken = MAPBOX_TOKEN;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [-98.5795, 39.8283], // geographic centre of contiguous US
      zoom: 3.4,
      attributionControl: false,
    });
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new mapboxgl.AttributionControl({ compact: true }));
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Render markers whenever rows change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear old
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    if (geoRows.length === 0) return;

    const bounds = new mapboxgl.LngLatBounds();

    for (const r of geoRows) {
      const score = dealScore(r);
      const hex = bandHex(score.band);

      const el = document.createElement('div');
      el.className = 'oom-pin';
      el.style.cssText = `
        width: 28px; height: 28px; border-radius: 50%;
        background: ${hex}; color: #fff;
        display: flex; align-items: center; justify-content: center;
        font: 700 11px/1 ui-sans-serif, system-ui, sans-serif;
        border: 2px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,.25);
        cursor: pointer;
        transform: ${r.parcel_key === focusKey ? 'scale(1.25)' : 'scale(1)'};
      `;
      el.textContent = String(score.total);

      const popupHtml = `
        <div style="font-family:ui-sans-serif,system-ui;min-width:180px">
          <div style="font-size:10px;color:#666;margin-bottom:2px;text-transform:uppercase;letter-spacing:.05em">
            ${score.band} · ${score.total}
          </div>
          <div style="font-weight:700;color:#0f1f3d;font-size:13px">
            ${r.address}
          </div>
          <div style="font-size:11px;color:#475569;margin-top:2px">
            ${[r.city, r.state, r.zip].filter(Boolean).join(', ')}
          </div>
          <a href="/property/${encodeURIComponent(r.parcel_key)}"
             style="display:inline-block;margin-top:8px;font-size:11px;color:#1d6cf2;font-weight:600;text-decoration:none">
            Open property →
          </a>
        </div>`;

      const popup = new Popup({ offset: 18, closeButton: false }).setHTML(popupHtml);
      const marker = new Marker({ element: el }).setLngLat([r.longitude!, r.latitude!]).setPopup(popup).addTo(map);
      markersRef.current.push(marker);
      bounds.extend([r.longitude!, r.latitude!]);

      // Open popup on hover
      el.addEventListener('mouseenter', () => marker.togglePopup());
      el.addEventListener('mouseleave', () => marker.togglePopup());
    }

    if (!bounds.isEmpty()) {
      map.fitBounds(bounds as LngLatBoundsLike, {
        padding: 60,
        maxZoom: 13,
        duration: 600,
      });
    }
  }, [geoRows, focusKey]);

  if (error) {
    return (
      <div className="card p-8 text-sm text-slate-500 text-center">
        <p className="font-semibold text-slate-700 mb-1">Map disabled</p>
        <p className="max-w-md mx-auto">
          {error}{' '}
          <Link to="/about" className="text-brand-600 hover:underline">Learn more</Link>
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      <div ref={containerRef} className="rounded-2xl overflow-hidden border border-slate-200" style={{ height: '70vh', minHeight: 500 }} />
      {geoRows.length === 0 && rows.length > 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-500 pointer-events-none">
          <div className="bg-white/90 px-4 py-2 rounded-full shadow border border-slate-200">
            No coordinates yet — re-run the pipeline to backfill lat/lng.
          </div>
        </div>
      )}
      {rows.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-500 pointer-events-none">
          <div className="bg-white/90 px-4 py-2 rounded-full shadow border border-slate-200">
            No properties match your filters.
          </div>
        </div>
      )}
      <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur border border-slate-200 rounded-full px-3 py-1.5 text-[11px] font-mono text-slate-600 shadow-sm">
        {geoRows.length} of {rows.length} mapped
      </div>
    </div>
  );
}
