import { useEffect, useRef, useState } from 'react';
import mapboxgl, { Map as MapboxMap, Marker } from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { ExternalLink } from 'lucide-react';
import { bandHex, DealScore } from '../lib/score';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined;

interface Props {
  latitude: number | null;
  longitude: number | null;
  band: DealScore['band'];
  score: number;
  address: string;
}

/** Single-pin Mapbox view used on the property detail page. Falls back
 *  to a simple message card when no coordinates are known. */
export default function ParcelMap({ latitude, longitude, band, score, address }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const [error, setError] = useState<string | null>(null);

  const hasCoords = typeof latitude === 'number' && typeof longitude === 'number';

  useEffect(() => {
    if (!hasCoords || !containerRef.current) return;
    if (!MAPBOX_TOKEN) {
      setError('Mapbox not configured');
      return;
    }
    if (mapRef.current) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [longitude!, latitude!],
      zoom: 16,
      attributionControl: false,
      dragRotate: false,
      cooperativeGestures: true,
    });
    map.touchZoomRotate.disableRotation();
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new mapboxgl.AttributionControl({ compact: true }));

    // Custom pin element
    const el = document.createElement('div');
    const hex = bandHex(band);
    el.style.cssText = `
      width: 36px; height: 36px; border-radius: 50%;
      background: ${hex}; color: #fff;
      display: flex; align-items: center; justify-content: center;
      font: 800 13px ui-sans-serif, system-ui;
      border: 3px solid #fff;
      box-shadow: 0 4px 14px rgba(0,0,0,.25);
    `;
    el.textContent = String(score);

    new Marker({ element: el }).setLngLat([longitude!, latitude!]).addTo(map);

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [hasCoords, latitude, longitude, band, score]);

  if (!hasCoords || error) {
    return (
      <div className="aspect-video rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-center text-sm text-slate-500">
        {error ?? 'Coordinates not yet captured for this parcel.'}
      </div>
    );
  }

  const gisLink = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;

  return (
    <div className="relative">
      <div
        ref={containerRef}
        className="aspect-video rounded-xl overflow-hidden border border-slate-200 bg-slate-100"
      />
      <a
        href={gisLink}
        target="_blank"
        rel="noopener noreferrer"
        className="absolute top-3 left-3 bg-white/95 backdrop-blur border border-slate-200 rounded-full px-3 py-1.5 text-xs font-semibold text-slate-700 inline-flex items-center gap-1.5 shadow-sm hover:bg-white"
      >
        Open in Google Maps <ExternalLink className="w-3 h-3" />
      </a>
    </div>
  );
}
