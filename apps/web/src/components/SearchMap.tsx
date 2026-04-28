import { useEffect, useRef, useState } from 'react';
import mapboxgl, { Map as MapboxMap, LngLatBoundsLike, GeoJSONSource } from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Link } from 'react-router-dom';
import type { OffMarketRow } from '../lib/api';
import { dealScore, bandHex } from '../lib/score';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined;

interface Props {
  rows: OffMarketRow[];
  /** Highlights a pin and centers it (used for hover sync from list) */
  hoveredKey?: string | null;
  /** Notify parent when user hovers a pin */
  onPinHover?: (parcelKey: string | null) => void;
  /** Notify parent when user clicks a pin */
  onPinClick?: (parcelKey: string) => void;
  /** Notify parent of map viewport bounds [west, south, east, north] */
  onBoundsChange?: (bounds: [number, number, number, number]) => void;
  /** Address/zip/city query — fly map to that location when present */
  flyToQuery?: string;
  /** Pixel height; defaults to 70vh */
  height?: string;
  /** When true, no rounded border / margin (used for full-bleed layouts) */
  inset?: boolean;
}

const SOURCE_ID = 'parcels';
const CLUSTER_LAYER = 'parcel-clusters';
const CLUSTER_COUNT_LAYER = 'parcel-cluster-count';
const POINT_LAYER = 'parcel-points';
const POINT_LABEL_LAYER = 'parcel-points-label';
const HOVER_LAYER = 'parcel-points-hover';

export default function SearchMap({
  rows,
  hoveredKey,
  onPinHover,
  onPinClick,
  onBoundsChange,
  flyToQuery,
  height = '70vh',
  inset = false,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const popupRef = useRef<mapboxgl.Popup | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [styleReady, setStyleReady] = useState(false);

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
      center: [-98.5795, 39.8283],
      zoom: 3.4,
      attributionControl: false,
      dragRotate: false,
    });
    map.touchZoomRotate.disableRotation();
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new mapboxgl.AttributionControl({ compact: true }));

    // Geocoder fly-to control — small input top-left
    map.addControl(
      new mapboxgl.GeolocateControl({
        positionOptions: { enableHighAccuracy: false },
        showUserHeading: false,
      }),
      'top-right'
    );

    map.on('load', () => {
      // Pre-create empty source/layers; data will be set in the data-effect
      map.addSource(SOURCE_ID, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
        cluster: true,
        clusterMaxZoom: 13,
        clusterRadius: 50,
      });

      // Cluster bubbles
      map.addLayer({
        id: CLUSTER_LAYER,
        type: 'circle',
        source: SOURCE_ID,
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': '#1d6cf2',
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2,
          'circle-opacity': 0.9,
          'circle-radius': [
            'step', ['get', 'point_count'],
            16,        // ≤ 10
            10, 22,    // ≤ 50
            50, 28,    // ≤ 250
            250, 34,   // > 250
          ],
        },
      });
      map.addLayer({
        id: CLUSTER_COUNT_LAYER,
        type: 'symbol',
        source: SOURCE_ID,
        filter: ['has', 'point_count'],
        layout: {
          'text-field': ['get', 'point_count_abbreviated'],
          'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
          'text-size': 12,
        },
        paint: { 'text-color': '#ffffff' },
      });

      // Single-point pins (data-driven color by deal score band)
      map.addLayer({
        id: POINT_LAYER,
        type: 'circle',
        source: SOURCE_ID,
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-color': ['get', 'color'],
          'circle-radius': [
            'case',
            ['==', ['get', 'parcel_key'], ['literal', '']], 12,  // never matches; fallback
            12,
          ],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2,
        },
      });
      map.addLayer({
        id: POINT_LABEL_LAYER,
        type: 'symbol',
        source: SOURCE_ID,
        filter: ['!', ['has', 'point_count']],
        layout: {
          'text-field': ['get', 'score'],
          'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
          'text-size': 10,
          'text-allow-overlap': true,
        },
        paint: { 'text-color': '#ffffff' },
      });

      // Highlighted (hovered) pin — bigger ring underneath
      map.addLayer({
        id: HOVER_LAYER,
        type: 'circle',
        source: SOURCE_ID,
        filter: ['==', ['get', 'parcel_key'], ''],
        paint: {
          'circle-color': 'rgba(0,0,0,0)',
          'circle-radius': 22,
          'circle-stroke-color': '#0f1f3d',
          'circle-stroke-width': 3,
        },
      });

      // Cluster click → zoom in
      map.on('click', CLUSTER_LAYER, (e) => {
        const features = map.queryRenderedFeatures(e.point, { layers: [CLUSTER_LAYER] });
        const clusterId = features[0]?.properties?.cluster_id;
        const src = map.getSource(SOURCE_ID) as GeoJSONSource;
        if (clusterId == null) return;
        src.getClusterExpansionZoom(clusterId, (err, zoom) => {
          if (err || zoom == null) return;
          map.easeTo({
            center: (features[0].geometry as GeoJSON.Point).coordinates as [number, number],
            zoom,
            duration: 500,
          });
        });
      });

      // Pin click → notify parent + popup
      map.on('click', POINT_LAYER, (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const props = f.properties as Record<string, string>;
        const coords = (f.geometry as GeoJSON.Point).coordinates as [number, number];
        if (popupRef.current) popupRef.current.remove();
        popupRef.current = new mapboxgl.Popup({ offset: 14, closeButton: false })
          .setLngLat(coords)
          .setHTML(popupHtml(props))
          .addTo(map);
        onPinClick?.(props.parcel_key);
      });

      // Emit viewport bounds on move/zoom (debounced via moveend)
      const emitBounds = () => {
        if (!onBoundsChange) return;
        const b = map.getBounds();
        if (!b) return;
        onBoundsChange([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]);
      };
      map.on('moveend', emitBounds);
      // Initial emit once style is loaded
      emitBounds();

      // Hover styling
      map.on('mouseenter', POINT_LAYER, (e) => {
        map.getCanvas().style.cursor = 'pointer';
        const key = (e.features?.[0]?.properties as any)?.parcel_key as string | undefined;
        if (key) onPinHover?.(key);
      });
      map.on('mouseleave', POINT_LAYER, () => {
        map.getCanvas().style.cursor = '';
        onPinHover?.(null);
      });
      map.on('mouseenter', CLUSTER_LAYER, () => { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', CLUSTER_LAYER, () => { map.getCanvas().style.cursor = ''; });

      setStyleReady(true);
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      setStyleReady(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Push data + fit bounds when rows change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady) return;
    const src = map.getSource(SOURCE_ID) as GeoJSONSource | undefined;
    if (!src) return;

    const features: GeoJSON.Feature[] = geoRows.map((r) => {
      const score = dealScore(r);
      return {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [r.longitude!, r.latitude!] },
        properties: {
          parcel_key: r.parcel_key,
          address: r.address,
          city: r.city || '',
          state: r.state,
          zip: r.zip || '',
          score: String(score.total),
          color: bandHex(score.band),
          band: score.band,
        },
      };
    });
    src.setData({ type: 'FeatureCollection', features });

    if (geoRows.length > 0) {
      const bounds = new mapboxgl.LngLatBounds();
      for (const r of geoRows) bounds.extend([r.longitude!, r.latitude!]);
      if (!bounds.isEmpty()) {
        map.fitBounds(bounds as LngLatBoundsLike, { padding: 60, maxZoom: 12, duration: 600 });
      }
    }
  }, [geoRows, styleReady]);

  // External hover → update HOVER_LAYER filter
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady) return;
    map.setFilter(HOVER_LAYER, ['==', ['get', 'parcel_key'], hoveredKey || '']);
  }, [hoveredKey, styleReady]);

  // Fly-to via Mapbox geocoder (debounced 400ms)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady) return;
    const q = (flyToQuery || '').trim();
    if (!q) return;
    const t = setTimeout(() => {
      const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(q)}.json?country=us&types=postcode,place,region&limit=1&access_token=${MAPBOX_TOKEN}`;
      fetch(url)
        .then((r) => r.json())
        .then((data) => {
          const f = data.features?.[0];
          if (!f) return;
          const center = f.center as [number, number];
          if (f.bbox) {
            map.fitBounds(f.bbox as LngLatBoundsLike, { padding: 60, duration: 600, maxZoom: 12 });
          } else {
            map.flyTo({ center, zoom: 12, duration: 600 });
          }
        })
        .catch(() => {});
    }, 400);
    return () => clearTimeout(t);
  }, [flyToQuery, styleReady]);

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
    <div className={`relative ${inset ? 'h-full' : ''}`}>
      <div
        ref={containerRef}
        className={inset
          ? 'h-full w-full bg-slate-100'
          : 'rounded-2xl overflow-hidden border border-slate-200 bg-slate-100'}
        style={inset ? { height: '100%' } : { height, minHeight: 400 }}
      />
      {rows.length > 0 && geoRows.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-500 pointer-events-none">
          <div className="bg-white/90 px-4 py-2 rounded-full shadow border border-slate-200">
            No coordinates yet — backfill via pipeline run.
          </div>
        </div>
      )}
      <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur border border-slate-200 rounded-full px-3 py-1.5 text-[11px] font-mono text-slate-600 shadow-sm">
        {geoRows.length} of {rows.length} mapped
      </div>
    </div>
  );
}

function popupHtml(p: Record<string, string>): string {
  const loc = [p.city, p.state, p.zip].filter(Boolean).join(', ');
  return `
    <div style="font-family:ui-sans-serif,system-ui;min-width:200px">
      <div style="font-size:10px;color:#64748b;margin-bottom:2px;text-transform:uppercase;letter-spacing:.05em">
        ${p.band} · ${p.score}
      </div>
      <div style="font-weight:700;color:#0f1f3d;font-size:13px">${escapeHtml(p.address)}</div>
      <div style="font-size:11px;color:#475569;margin-top:2px">${escapeHtml(loc)}</div>
      <a href="/property/${encodeURIComponent(p.parcel_key)}"
         style="display:inline-block;margin-top:8px;font-size:11px;color:#1d6cf2;font-weight:600;text-decoration:none">
        Open property →
      </a>
    </div>`;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c)
  );
}
