/**
 * DealMeter — weighted score for off-market parcels.
 *
 * Inputs come from the canonical OffMarketRow shape. We score 0–100 with
 * a fixed cap. Each metric is independent + additive so we can also surface
 * the breakdown in the UI (why a property scored what it did).
 */
import type { ApiSource, OffMarketRow } from './api';

export interface ScoreBreakdownItem {
  key: string;
  label: string;
  points: number;
  detail?: string;
}

export interface DealScore {
  total: number;          // 0-100
  band: 'cold' | 'warming' | 'warm' | 'hot' | 'top';
  breakdown: ScoreBreakdownItem[];
}

// Per-source heat. Stacking happens on top via diversity bonus.
const SOURCE_WEIGHTS: Partial<Record<ApiSource, number>> = {
  auction: 25,         // sale-date pressure
  preforeclosure: 22,  // bank-driven, financial distress
  'tax-lien': 18,      // long-tail distress
  probate: 16,         // motivated heir, often unrenovated
  vacant: 14,          // carrying costs + neglect signals
  reo: 12,             // bank already owns, slower
  fsbo: 10,            // motivated but not necessarily distressed
  motivated_seller: 12,
  expired: 8,
  canceled: 8,
  wholesale: 6,
  network: 4,
};

// Bands derived from the total
function bandFor(total: number): DealScore['band'] {
  if (total >= 85) return 'top';
  if (total >= 70) return 'hot';
  if (total >= 50) return 'warm';
  if (total >= 30) return 'warming';
  return 'cold';
}

export function dealScore(p: OffMarketRow): DealScore {
  const breakdown: ScoreBreakdownItem[] = [];
  let total = 0;

  // 1. Highest-weight source tag (avoid double-counting two distress sources, take max)
  let topSource: ApiSource | null = null;
  let topPoints = 0;
  for (const t of p.source_tags) {
    const w = SOURCE_WEIGHTS[t] ?? 0;
    if (w > topPoints) {
      topPoints = w;
      topSource = t;
    }
  }
  if (topSource) {
    breakdown.push({
      key: 'primary',
      label: `${topSource.replace(/_/g, ' ')} signal`,
      points: topPoints,
      detail: 'highest-weight active source',
    });
    total += topPoints;
  }

  // 2. Diversity bonus — every extra distress source compounds urgency
  const extras = p.source_tags.length - 1;
  if (extras > 0) {
    const pts = Math.min(extras * 6, 18); // capped at +18
    breakdown.push({
      key: 'stack',
      label: `${extras} additional source${extras === 1 ? '' : 's'}`,
      points: pts,
      detail: 'multiple distress signals on one parcel',
    });
    total += pts;
  }

  // 3. Years delinquent — more years = more pressure
  if (p.years_delinquent && p.years_delinquent > 0) {
    const pts = Math.min(p.years_delinquent * 4, 16);
    breakdown.push({
      key: 'delinquent',
      label: `${p.years_delinquent} year${p.years_delinquent === 1 ? '' : 's'} delinquent`,
      points: pts,
    });
    total += pts;
  }

  // 4. Vacancy duration
  if (p.vacancy_months && p.vacancy_months > 0) {
    const pts = Math.min(Math.round(p.vacancy_months * 1.5), 14);
    breakdown.push({
      key: 'vacancy',
      label: `${p.vacancy_months} month${p.vacancy_months === 1 ? '' : 's'} vacant`,
      points: pts,
    });
    total += pts;
  }

  // 5. Absentee owner (mailing state ≠ property state)
  if (p.owner_state && p.state && p.owner_state !== p.state) {
    breakdown.push({
      key: 'absentee',
      label: `Absentee owner (${p.owner_state})`,
      points: 8,
      detail: 'owner mailing address out of state',
    });
    total += 8;
  }

  // 6. Sale date proximity — auction within 60 days = urgent
  if (p.sale_date) {
    const days = Math.round((new Date(p.sale_date).getTime() - Date.now()) / 86_400_000);
    if (days >= 0 && days <= 60) {
      const pts = days <= 14 ? 14 : days <= 30 ? 10 : 6;
      breakdown.push({
        key: 'sale',
        label: `Sale in ${days}d`,
        points: pts,
        detail: 'time pressure → motivated decisions',
      });
      total += pts;
    }
  }

  // 7. Stacked debt — meaningful even without LTV (signals financial pressure)
  const debt = (p.default_amount ?? 0) + (p.lien_amount ?? 0);
  if (debt >= 25_000) {
    const pts = debt >= 100_000 ? 10 : debt >= 50_000 ? 7 : 4;
    breakdown.push({
      key: 'debt',
      label: `$${debt.toLocaleString()} stacked debt`,
      points: pts,
      detail: 'larger debt → owner more likely to negotiate',
    });
    total += pts;
  }

  // 8. Loan-to-value (LTV) — lower LTV = more equity = bigger room to negotiate.
  // Underwater (LTV ≥ 1.0) gets 0 because the bank owns the upside, not the seller.
  const valueRef = p.estimated_value ?? p.assessed_value;
  if (valueRef && p.loan_balance !== null && p.loan_balance !== undefined && valueRef > 0) {
    const ltv = p.loan_balance / valueRef;
    let pts = 0;
    let label = '';
    if (ltv <= 0.05) {            // effectively paid off
      pts = 18;
      label = 'Owned free & clear';
    } else if (ltv <= 0.4) {
      pts = 14;
      label = `Low LTV ${Math.round(ltv * 100)}%`;
    } else if (ltv <= 0.65) {
      pts = 9;
      label = `Moderate LTV ${Math.round(ltv * 100)}%`;
    } else if (ltv < 0.85) {
      pts = 4;
      label = `High LTV ${Math.round(ltv * 100)}%`;
    } else if (ltv < 1.0) {
      pts = 0;
      label = `Tight LTV ${Math.round(ltv * 100)}%`;
    } else {
      pts = -8;                   // underwater — penalize, harder to close
      label = `Underwater ${Math.round(ltv * 100)}%`;
    }
    if (pts !== 0 || label) {
      breakdown.push({
        key: 'ltv',
        label,
        points: pts,
        detail: 'loan balance ÷ estimated value',
      });
      total += pts;
    }
  }

  // 9. Asking price discount vs estimated value (FSBO listed below market)
  if (p.asking_price && p.estimated_value && p.estimated_value > 0) {
    const discount = 1 - p.asking_price / p.estimated_value;
    if (discount > 0.02) {
      // 30% under market = 18 pts; 10% under = 6 pts; 5% under = 3 pts
      const pts = Math.min(Math.round(discount * 60), 18);
      breakdown.push({
        key: 'asking_discount',
        label: `Asking ${Math.round(discount * 100)}% below est. value`,
        points: pts,
        detail: `$${p.asking_price.toLocaleString()} vs $${p.estimated_value.toLocaleString()} AVM`,
      });
      total += pts;
    }
  }

  // 9. Recency — fresher signals are easier to act on
  if (p.last_seen) {
    const daysOld = Math.round((Date.now() - new Date(p.last_seen).getTime()) / 86_400_000);
    if (daysOld <= 7) {
      breakdown.push({ key: 'fresh', label: 'Fresh (≤7d old)', points: 4 });
      total += 4;
    } else if (daysOld <= 30) {
      breakdown.push({ key: 'fresh', label: 'Recent (≤30d old)', points: 2 });
      total += 2;
    }
  }

  total = Math.max(0, Math.min(100, Math.round(total)));
  return { total, band: bandFor(total), breakdown };
}

// UI helpers — keyed by band
export function bandColor(band: DealScore['band']): string {
  switch (band) {
    case 'top':     return 'bg-rose-500';
    case 'hot':     return 'bg-orange-500';
    case 'warm':    return 'bg-amber-500';
    case 'warming': return 'bg-yellow-500';
    case 'cold':    return 'bg-brand-500';
  }
}

export function bandTextColor(band: DealScore['band']): string {
  switch (band) {
    case 'top':     return 'text-rose-600';
    case 'hot':     return 'text-orange-600';
    case 'warm':    return 'text-amber-600';
    case 'warming': return 'text-yellow-600';
    case 'cold':    return 'text-brand-600';
  }
}

// Hex value for SVG stroke (Tailwind JIT can't see runtime class strings)
export function bandHex(band: DealScore['band']): string {
  switch (band) {
    case 'top':     return '#f43f5e'; // rose-500
    case 'hot':     return '#f97316'; // orange-500
    case 'warm':    return '#f59e0b'; // amber-500
    case 'warming': return '#eab308'; // yellow-500
    case 'cold':    return '#1d6cf2'; // brand-500
  }
}
