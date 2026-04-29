/* Token wallet client.
 *
 * User identity for the MVP is a UUID stored in localStorage. We send it as
 * X-User-Id on every request that touches the wallet — see `apiHeaders()`.
 * When real auth ships, swap the helper to read from the auth context and
 * everything downstream keeps working.
 */
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001';
const STORAGE_KEY = 'oom_user_id_v1';

export function getUserId(): string {
  let id = localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id =
      (crypto as Crypto & { randomUUID?: () => string }).randomUUID?.() ||
      'u_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}

export function apiHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return { 'X-User-Id': getUserId(), ...extra };
}

export interface TokenPackage {
  id: string;
  label: string;
  tokens: number;
  price_usd: number;
  per_token_usd: number;
  discount_pct: number;
  badge: string | null;
}

export interface TokenAction {
  key: string;
  label: string;
  tokens: number;
}

export interface PackagesResponse {
  token_usd: number;
  packages: TokenPackage[];
  actions: TokenAction[];
}

export interface BalanceSummary {
  user_id: string;
  balance: number;
  lifetime_purchased: number;
  lifetime_spent: number;
}

export interface TokenTransaction {
  id: string;
  kind: 'purchase' | 'spend' | 'refund' | 'grant';
  amount: number;
  action_key: string | null;
  parcel_key: string | null;
  package_id: string | null;
  note: string | null;
  created_at: string | null;
}

export async function getPackages(): Promise<PackagesResponse> {
  const r = await fetch(`${API_BASE}/tokens/packages`);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function getBalance(): Promise<BalanceSummary> {
  const r = await fetch(`${API_BASE}/tokens/balance`, { headers: apiHeaders() });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function getTransactions(limit = 50): Promise<TokenTransaction[]> {
  const r = await fetch(`${API_BASE}/tokens/transactions?limit=${limit}`, {
    headers: apiHeaders(),
  });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return (await r.json()).results;
}

export async function purchasePackage(packageId: string): Promise<{
  success: boolean;
  tokens_credited: number;
  balance: number;
  billed_usd: number;
}> {
  const r = await fetch(`${API_BASE}/tokens/purchase`, {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ package_id: packageId }),
  });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}

/* ---------- Action cost lookup helpers (synced with backend defaults) ---------- */

export const ACTION_TOKEN_COST: Record<string, number> = {
  skip_trace_standard: 1,
  skip_trace_pro: 3,
  mailer_postcard: 4,
};

export function tokenLabel(n: number): string {
  return `${n} token${n === 1 ? '' : 's'}`;
}
