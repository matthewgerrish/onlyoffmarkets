import { apiHeaders } from './tokens';
import type { AnalyzerResponse } from './analyzer';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001';

export interface WatchlistItem {
  id: number;
  user_id: string;
  parcel_key: string;
  address: string;
  city: string | null;
  state: string | null;
  zip: string | null;
  lat: number | null;
  lng: number | null;
  deal_score: number | null;
  deal_band: string | null;
  adu_score: number | null;
  adu_band: string | null;
  snapshot: AnalyzerResponse | null;
  notes: string | null;
  saved_at: string | null;
}

export async function listWatchlist(): Promise<WatchlistItem[]> {
  const r = await fetch(`${API_BASE}/watchlist`, { headers: apiHeaders() });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return (await r.json()).results as WatchlistItem[];
}

export async function saveToWatchlist(payload: {
  parcel_key: string;
  address: string;
  city?: string | null;
  state?: string | null;
  zip?: string | null;
  lat?: number | null;
  lng?: number | null;
  deal_score?: number | null;
  deal_band?: string | null;
  adu_score?: number | null;
  adu_band?: string | null;
  snapshot?: AnalyzerResponse | null;
  notes?: string | null;
}): Promise<{ ok: boolean; saved: WatchlistItem }> {
  const r = await fetch(`${API_BASE}/watchlist`, {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}

export async function removeFromWatchlist(parcelKey: string): Promise<void> {
  const r = await fetch(`${API_BASE}/watchlist/${encodeURIComponent(parcelKey)}`, {
    method: 'DELETE',
    headers: apiHeaders(),
  });
  if (!r.ok) throw new Error(`API ${r.status}`);
}

export async function updateNotes(parcelKey: string, notes: string): Promise<void> {
  const r = await fetch(`${API_BASE}/watchlist/${encodeURIComponent(parcelKey)}/notes`, {
    method: 'PUT',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ notes }),
  });
  if (!r.ok) throw new Error(`API ${r.status}`);
}

/** Build a deterministic parcel_key from an analyzer result. Prefers
 *  the real APN; falls back to a slug of address+state. */
export function parcelKeyFor(r: AnalyzerResponse): string {
  if (r.parcel_apn) return r.parcel_apn;
  const slug = [r.address, r.state].filter(Boolean).join(' ').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  return slug || 'unknown';
}
