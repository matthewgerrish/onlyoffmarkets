import type { ApiSource } from './api';

export const SOURCE_LABELS: Record<ApiSource, string> = {
  preforeclosure: 'Preforeclosure (NOD)',
  auction: 'Trustee / auction sale',
  fsbo: 'For sale by owner',
  'tax-lien': 'Tax delinquent',
  probate: 'Probate filing',
  vacant: 'Vacant / absentee',
  reo: 'Bank-owned (REO)',
  canceled: 'MLS canceled',
  expired: 'MLS expired',
  motivated_seller: 'Motivated seller',
  wholesale: 'Wholesaler assignment',
  network: 'Off-market network',
};

export const ALL_SOURCES: ApiSource[] = Object.keys(SOURCE_LABELS) as ApiSource[];

export type Tier = 'cold' | 'warming' | 'warm' | 'hot' | 'top';

/** Heuristic: number + kind of stacked signals on a parcel determines its heat. */
export function tierFor(tags: ApiSource[]): Tier {
  const hot = new Set<ApiSource>(['preforeclosure', 'auction', 'tax-lien', 'probate']);
  const hotCount = tags.filter((t) => hot.has(t)).length;
  if (hotCount >= 3) return 'top';
  if (hotCount >= 2) return 'hot';
  if (hotCount === 1) return 'warm';
  if (tags.includes('fsbo') || tags.includes('motivated_seller') || tags.includes('expired')) return 'warming';
  return 'cold';
}
