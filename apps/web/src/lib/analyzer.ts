import { apiHeaders } from './tokens';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001';

export interface AnalyzerResponse {
  query: string;
  address: string | null;
  city: string | null;
  county: string | null;
  state: string | null;
  zip: string | null;
  lat: number | null;
  lng: number | null;

  parcel_apn: string | null;
  owner_name: string | null;
  owner_state: string | null;

  year_built: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  sqft: number | null;
  lot_sqft: number | null;
  property_type: string | null;

  estimated_value: number | null;
  assessed_value: number | null;
  loan_balance: number | null;
  asking_price: number | null;
  ltv: number | null;
  equity: number | null;
  spread_pct: number | null;

  distress: {
    tags: string[];
    default_amount: number | null;
    sale_date: string | null;
    years_delinquent: number | null;
    vacancy_months: number | null;
    foreclosure_stage: string | null;
    hoa_delinquent: boolean | null;
  };

  ownership: {
    years_owned: number | null;
    last_sale_date: string | null;
    last_sale_price: number | null;
    mortgage_count: number | null;
    equity_pct: number | null;
  };

  deal: {
    total: number;
    band: 'cold' | 'warming' | 'warm' | 'hot' | 'top';
    breakdown: Array<{ key: string; label: string; points: number; detail?: string }>;
    confidence: number;
    recommendation: string;
  };

  adu: {
    score: number;
    band: 'none' | 'limited' | 'good' | 'excellent';
    units_possible: number;
    eligible: boolean;
    breakdown: Array<{ key: string; label: string; points: number; detail?: string }>;
    notes: string[];
    state?: string;
  };

  sources: {
    off_market_db: boolean;
    propertyradar: boolean;
    attom: boolean;
    found: boolean;
    geocoder: 'mapbox' | 'fallback';
  };
}

export async function analyzeAddress(address: string): Promise<AnalyzerResponse> {
  const r = await fetch(`${API_BASE}/analyzer`, {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ address }),
  });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}
