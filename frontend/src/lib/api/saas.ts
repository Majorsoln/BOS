import api from "./client";

/* ── Regions (Nchi) ────────────────────────────────────────── */

export async function getRegions() {
  const res = await api.get("/saas/regions");
  return res.data;
}

export async function addRegion(data: {
  code: string;
  name: string;
  currency: string;
  tax_name?: string;
  vat_rate?: number;
  digital_tax_rate?: number;
  b2b_reverse_charge?: boolean;
  registration_required?: boolean;
}) {
  const res = await api.post("/saas/regions/add", data);
  return res.data;
}

export async function updateRegion(data: {
  code: string;
  name?: string;
  currency?: string;
  tax_name?: string;
  vat_rate?: number;
  digital_tax_rate?: number;
  b2b_reverse_charge?: boolean;
  registration_required?: boolean;
}) {
  const res = await api.post("/saas/regions/update", data);
  return res.data;
}

/* ── Services (Huduma) ─────────────────────────────────────── */

export async function getServices() {
  const res = await api.get("/saas/services");
  return res.data;
}

export async function setServiceRate(data: {
  service_key: string;
  region_code: string;
  currency: string;
  monthly_amount: number;
}) {
  const res = await api.post("/saas/services/set-rate", data);
  return res.data;
}

export async function toggleService(data: {
  service_key: string;
  active: boolean;
}) {
  const res = await api.post("/saas/services/toggle", data);
  return res.data;
}

/* ── Capacity Tiers ────────────────────────────────────────── */

export async function getCapacityPricing() {
  const res = await api.get("/saas/capacity");
  return res.data;
}

export async function setCapacityTierRate(data: {
  dimension: string;
  tier_key: string;
  region_code: string;
  currency: string;
  monthly_amount: number;
}) {
  const res = await api.post("/saas/capacity/set-rate", data);
  return res.data;
}

/* ── Multi-Service Reduction Rates ─────────────────────────── */

export async function getReductionRates() {
  const res = await api.get("/saas/reductions");
  return res.data;
}

export async function setReductionRate(data: {
  region_code: string;
  service_count: number;
  reduction_pct: number;
}) {
  const res = await api.post("/saas/reductions/set", data);
  return res.data;
}

/* ── Price Calculator ──────────────────────────────────────── */

export async function calculatePrice(data: {
  region_code: string;
  services: string[];
  capacity: {
    branches: string;
    documents: string;
    users: string;
    ai_tokens: string;
  };
}) {
  const res = await api.post("/saas/calculate-price", data);
  return res.data;
}

/* ── Trial Policy ──────────────────────────────────────────── */

export async function getTrialPolicy() {
  const res = await api.get("/saas/trial-policy");
  return res.data;
}

export async function setTrialPolicy(data: {
  default_trial_days: number;
  max_trial_days: number;
  grace_period_days: number;
}) {
  const res = await api.post("/saas/trial-policy/set", data);
  return res.data;
}

/* ── Trials ────────────────────────────────────────────────── */

export async function getTrials(params?: { status?: string }) {
  const res = await api.get("/saas/trials", { params });
  return res.data;
}

export async function extendTrial(data: {
  business_id: string;
  extra_days: number;
  reason?: string;
}) {
  const res = await api.post("/saas/trials/extend", data);
  return res.data;
}

export async function convertTrial(data: { business_id: string }) {
  const res = await api.post("/saas/trials/convert", data);
  return res.data;
}

/* ── Rate Governance ───────────────────────────────────────── */

export async function getEffectiveRate(businessId: string) {
  const res = await api.get("/saas/rates/effective", { params: { business_id: businessId } });
  return res.data;
}

export async function publishRateChange(data: {
  service_key: string;
  region_code: string;
  old_amount: number;
  new_amount: number;
  currency: string;
  effective_from: string;
}) {
  const res = await api.post("/saas/rates/publish-change", data);
  return res.data;
}

/* ── Promotions ────────────────────────────────────────────── */

export async function getPromos() {
  const res = await api.get("/saas/promos");
  return res.data;
}

export async function createPromo(data: {
  promo_code: string;
  promo_type: string;
  description?: string;
  valid_from: string;
  valid_until: string;
  max_redemptions?: number;
  region_codes?: string[];
  discount_pct?: number;
  discount_months?: number;
  credit_amount?: number;
  credit_currency?: string;
  extra_trial_days?: number;
}) {
  const res = await api.post("/saas/promos/create", data);
  return res.data;
}

export async function redeemPromo(data: {
  promo_code: string;
  business_id: string;
}) {
  const res = await api.post("/saas/promos/redeem", data);
  return res.data;
}

/* ── Subscriptions ─────────────────────────────────────────── */

export async function getSubscriptions(params?: { status?: string }) {
  const res = await api.get("/saas/subscriptions", { params });
  return res.data;
}

export async function activateSubscription(data: {
  business_id: string;
}) {
  const res = await api.post("/saas/subscriptions/activate", data);
  return res.data;
}

export async function cancelSubscription(data: {
  business_id: string;
  reason?: string;
}) {
  const res = await api.post("/saas/subscriptions/cancel", data);
  return res.data;
}
