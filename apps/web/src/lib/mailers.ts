const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001';

export interface MailerTemplate {
  id: string;
  name: string;
  description: string | null;
  front_html: string;
  back_html: string;
  size: string;
  qr_url: string | null;
  is_preset: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface MailerCampaign {
  id: string;
  name: string;
  template_id: string | null;
  parcel_keys: string[];
  status: string;
  sent_count: number;
  error_count: number;
  lob_postcard_ids: string[];
  created_at: string | null;
  sent_at: string | null;
}

export type SkipTraceTier = 'standard' | 'pro';

export interface SkipTraceTierInfo {
  tier: SkipTraceTier;
  label: string;
  provider_label: string;
  advertised_usd: number;
  markup_pct: number;
  match_rate_pct: number;
  description: string;
}

export interface OwnerContact {
  provider: string;
  owner_name: string | null;
  phones: { number: string; type: string; confidence: string }[];
  emails: { address: string; confidence: string }[];
  mailing_address: string | null;
  notes?: string;
  tier?: SkipTraceTier;
  tier_label?: string;
  billing?: {
    tier: SkipTraceTier;
    provider_label: string;
    advertised_usd: number;
    markup_pct: number;
    billed: boolean;
  };
}

export async function lookupOwner(
  parcelKey: string,
  tier: SkipTraceTier = 'standard',
): Promise<OwnerContact> {
  const r = await fetch(
    `${API_BASE}/owner/${encodeURIComponent(parcelKey)}?tier=${tier}`,
  );
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}

export async function getSkipTracePricing(): Promise<{ tiers: SkipTraceTierInfo[] }> {
  const r = await fetch(`${API_BASE}/owner/_/pricing`);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function listTemplates(): Promise<MailerTemplate[]> {
  const r = await fetch(`${API_BASE}/mailers/templates`);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return (await r.json()).results;
}

export async function createTemplate(t: Omit<MailerTemplate, 'id' | 'is_preset' | 'created_at' | 'updated_at'>): Promise<{ id: string }> {
  const r = await fetch(`${API_BASE}/mailers/templates`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(t),
  });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}

export async function deleteTemplate(id: string): Promise<void> {
  const r = await fetch(`${API_BASE}/mailers/templates/${id}`, { method: 'DELETE' });
  if (!r.ok) throw new Error(`API ${r.status}`);
}

export interface CampaignPayload {
  name: string;
  template_id: string | null;
  front_html?: string;
  back_html?: string;
  size?: string;
  parcel_keys: string[];
  from_name: string;
  from_address_line1: string;
  from_address_city: string;
  from_address_state: string;
  from_address_zip: string;
}

export async function listCampaigns(): Promise<{ results: MailerCampaign[]; lob_mode: string }> {
  const r = await fetch(`${API_BASE}/mailers/campaigns`);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function sendCampaign(payload: CampaignPayload): Promise<{
  id: string;
  status: string;
  sent_count: number;
  error_count: number;
  lob_postcard_ids: string[];
  lob_mode: string;
}> {
  const r = await fetch(`${API_BASE}/mailers/campaigns`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`API ${r.status}: ${await r.text()}`);
  return r.json();
}
