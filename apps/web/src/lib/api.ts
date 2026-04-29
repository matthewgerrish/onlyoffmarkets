const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001';

export type ApiSource =
  | 'preforeclosure' | 'auction' | 'fsbo' | 'tax-lien' | 'probate'
  | 'vacant' | 'reo' | 'canceled' | 'expired'
  | 'motivated_seller' | 'wholesale' | 'network';

export interface OffMarketRow {
  parcel_key: string;
  parcel_apn: string | null;
  address: string;
  city: string | null;
  county: string | null;
  state: string;
  zip: string | null;
  source_tags: ApiSource[];
  default_amount: number | null;
  sale_date: string | null;
  asking_price: number | null;
  lien_amount: number | null;
  years_delinquent: number | null;
  vacancy_months: number | null;
  owner_state: string | null;
  owner_name: string | null;
  latitude: number | null;
  longitude: number | null;
  estimated_value: number | null;
  assessed_value: number | null;
  loan_balance: number | null;
  estimated_equity: number | null;
  spread_pct: number | null;
  adu_ready: number;
  adu_score: number;
  first_seen: string;
  last_seen: string;
}

export interface OffMarketListResponse {
  results: OffMarketRow[];
  counts: Record<string, number>;
  disclaimer: string;
}

export interface OffMarketDetailResponse extends OffMarketRow {
  sources: {
    source: string;
    source_id: string;
    source_url: string | null;
    scraped_at: string;
    payload: unknown;
  }[];
}

interface ListParams {
  source?: ApiSource | 'all';
  state?: string;
  county?: string;
  limit?: number;
}

export async function listOffMarket(params: ListParams = {}): Promise<OffMarketListResponse> {
  const url = new URL(`${API_BASE}/off-market`);
  if (params.source && params.source !== 'all') url.searchParams.set('source', params.source);
  if (params.state) url.searchParams.set('state', params.state);
  if (params.county) url.searchParams.set('county', params.county);
  if (params.limit) url.searchParams.set('limit', String(params.limit));

  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}

export async function getOffMarket(parcelKey: string): Promise<OffMarketDetailResponse> {
  const r = await fetch(`${API_BASE}/off-market/${encodeURIComponent(parcelKey)}`);
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}

export interface CoverageSummary {
  total_parcels: number;
  by_source: Record<string, number>;
  by_state: Record<string, number>;
  states_covered: number;
  top_cities?: { city: string; state: string; count: number }[];
}

export async function getCoverage(): Promise<CoverageSummary> {
  const r = await fetch(`${API_BASE}/off-market/_/coverage`);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export interface Pin {
  parcel_key: string;
  latitude: number;
  longitude: number;
  source_tags: ApiSource[];
  state: string | null;
  default_amount: number | null;
  lien_amount: number | null;
  asking_price: number | null;
  sale_date: string | null;
  years_delinquent: number | null;
  vacancy_months: number | null;
  owner_state: string | null;
  estimated_value: number | null;
  assessed_value: number | null;
  loan_balance: number | null;
  last_seen: string;
}

export async function getPins(params: { state?: string; source?: ApiSource | 'all' } = {}): Promise<{ pins: Pin[]; count: number }> {
  const url = new URL(`${API_BASE}/off-market/_/pins`);
  if (params.state) url.searchParams.set('state', params.state);
  if (params.source && params.source !== 'all') url.searchParams.set('source', params.source);
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}
