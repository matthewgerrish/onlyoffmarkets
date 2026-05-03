/* Admin client — token-gated. Stores admin token in localStorage so
 * the user only types it once per browser. */
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001';
const TOKEN_KEY = 'oom_admin_token_v1';

export function getAdminToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAdminToken(t: string): void {
  localStorage.setItem(TOKEN_KEY, t);
}

export function clearAdminToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export interface ScraperHealthRow {
  slug: string;
  source_class: string;
  state: 'green' | 'yellow' | 'red' | 'never';
  registered: boolean;
  runs: number;
  total_scraped: number;
  total_persisted: number;
  total_errors: number;
  last_run: string | null;
  hours_since_run: number | null;
  last_source?: string | null;
}

export interface ScraperRun {
  id: number;
  slug: string;
  source: string | null;
  started_at: string | null;
  finished_at: string | null;
  scraped: number;
  persisted: number;
  errors: number;
  elapsed_s: number | null;
  status: string;
  note: string | null;
}

function buildUrl(path: string, params: Record<string, string | number | undefined> = {}): string {
  const token = getAdminToken();
  if (!token) throw new Error('Admin token not set');
  const url = new URL(`${API_BASE}${path}`);
  url.searchParams.set('token', token);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) url.searchParams.set(k, String(v));
  }
  return url.toString();
}

export async function getScraperHealth(days = 14): Promise<ScraperHealthRow[]> {
  const r = await fetch(buildUrl('/admin/scrapers', { days }));
  if (r.status === 401) throw new Error('Bad admin token');
  if (r.status === 503) throw new Error('Admin disabled (ADMIN_TOKEN not set on Fly)');
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  const data = await r.json();
  return data.scrapers as ScraperHealthRow[];
}

export async function getScraperHistory(slug: string, limit = 30): Promise<ScraperRun[]> {
  const r = await fetch(buildUrl(`/admin/scrapers/${encodeURIComponent(slug)}`, { limit }));
  if (!r.ok) throw new Error(`API ${r.status}`);
  const data = await r.json();
  return data.runs as ScraperRun[];
}

export async function runPipeline(sources?: string[]): Promise<unknown> {
  const url = new URL(buildUrl('/admin/run'));
  if (sources && sources.length) {
    for (const s of sources) url.searchParams.append('sources', s);
  }
  const r = await fetch(url.toString(), { method: 'POST' });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}

export async function getCoverage(): Promise<{
  total_parcels: number;
  total_source_records: number;
  by_state: Record<string, number>;
  by_source: Record<string, number>;
  registered_scrapers: string[];
}> {
  const r = await fetch(buildUrl('/admin/coverage'));
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}
