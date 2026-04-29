import { apiHeaders } from './tokens';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001';

export type PlanId = 'free' | 'standard' | 'premium';

export interface Plan {
  id: PlanId;
  label: string;
  price_usd: number;
  interval: string;
  badge: string | null;
  blurb: string;
  cta: string;
  token_bonus_pct: number;
  monthly_token_grant: number;
  features: string[];
}

export interface Membership {
  user_id: string;
  plan: PlanId;
  plan_meta: Plan;
  status: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  stripe_customer_id: string | null;
}

export async function getPlans(): Promise<{ plans: Plan[]; stripe_live: boolean }> {
  const r = await fetch(`${API_BASE}/billing/plans`);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function getMembership(): Promise<Membership> {
  const r = await fetch(`${API_BASE}/billing/membership`, { headers: apiHeaders() });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function checkoutTokens(
  packageId: string,
): Promise<{ url: string; mock: boolean }> {
  const r = await fetch(`${API_BASE}/billing/checkout/tokens`, {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ package_id: packageId }),
  });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}

export async function checkoutMembership(
  plan: PlanId,
): Promise<{ url: string; mock: boolean }> {
  const r = await fetch(`${API_BASE}/billing/checkout/membership`, {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ plan }),
  });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}

export async function confirmSession(sessionId: string): Promise<{
  ok: boolean;
  plan?: string;
  credited?: number;
  bonus?: number;
  already_credited?: boolean;
  payment_status?: string;
  mock?: boolean;
}> {
  const r = await fetch(`${API_BASE}/billing/confirm-session`, {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}

export async function syncFromStripe(): Promise<{
  ok: boolean;
  plan?: string;
  reason?: string;
  mock?: boolean;
}> {
  const r = await fetch(`${API_BASE}/billing/sync`, {
    method: 'POST',
    headers: apiHeaders(),
  });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function openCustomerPortal(): Promise<{ url: string; mock: boolean }> {
  const r = await fetch(`${API_BASE}/billing/portal`, {
    method: 'POST',
    headers: apiHeaders(),
  });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}
