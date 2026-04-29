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
  property_type: string | null;
  bedrooms: number | null;
  bathrooms: number | null;
  sqft: number | null;
  lot_sqft: number | null;
  year_built: number | null;
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

export type PropertyType =
  | 'single_family' | 'condo' | 'townhome' | 'multi_family'
  | 'land' | 'commercial' | 'manufactured' | 'other';

interface ListParams {
  source?: ApiSource | 'all';
  state?: string;
  states?: string[];
  county?: string;
  property_type?: PropertyType;
  min_value?: number;
  max_value?: number;
  min_beds?: number;
  min_baths?: number;
  min_sqft?: number;
  max_sqft?: number;
  limit?: number;
}

export async function listOffMarket(params: ListParams = {}): Promise<OffMarketListResponse> {
  const url = new URL(`${API_BASE}/off-market`);
  if (params.source && params.source !== 'all') url.searchParams.set('source', params.source);
  if (params.states && params.states.length > 0) url.searchParams.set('states', params.states.join(','));
  else if (params.state) url.searchParams.set('state', params.state);
  if (params.county) url.searchParams.set('county', params.county);
  if (params.property_type) url.searchParams.set('property_type', params.property_type);
  if (typeof params.min_value === 'number') url.searchParams.set('min_value', String(params.min_value));
  if (typeof params.max_value === 'number') url.searchParams.set('max_value', String(params.max_value));
  if (typeof params.min_beds === 'number') url.searchParams.set('min_beds', String(params.min_beds));
  if (typeof params.min_baths === 'number') url.searchParams.set('min_baths', String(params.min_baths));
  if (typeof params.min_sqft === 'number') url.searchParams.set('min_sqft', String(params.min_sqft));
  if (typeof params.max_sqft === 'number') url.searchParams.set('max_sqft', String(params.max_sqft));
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
  by_property_type?: Record<string, number>;
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
  property_type: string | null;
  last_seen: string;
}

export async function getPins(
  params: {
    state?: string;
    states?: string[];
    source?: ApiSource | 'all';
    property_type?: PropertyType;
    min_value?: number;
    max_value?: number;
    min_beds?: number;
    min_baths?: number;
    min_sqft?: number;
    max_sqft?: number;
  } = {}
): Promise<{ pins: Pin[]; count: number }> {
  const url = new URL(`${API_BASE}/off-market/_/pins`);
  if (params.states && params.states.length > 0) url.searchParams.set('states', params.states.join(','));
  else if (params.state) url.searchParams.set('state', params.state);
  if (params.source && params.source !== 'all') url.searchParams.set('source', params.source);
  if (params.property_type) url.searchParams.set('property_type', params.property_type);
  if (typeof params.min_value === 'number') url.searchParams.set('min_value', String(params.min_value));
  if (typeof params.max_value === 'number') url.searchParams.set('max_value', String(params.max_value));
  if (typeof params.min_beds === 'number') url.searchParams.set('min_beds', String(params.min_beds));
  if (typeof params.min_baths === 'number') url.searchParams.set('min_baths', String(params.min_baths));
  if (typeof params.min_sqft === 'number') url.searchParams.set('min_sqft', String(params.min_sqft));
  if (typeof params.max_sqft === 'number') url.searchParams.set('max_sqft', String(params.max_sqft));
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}
