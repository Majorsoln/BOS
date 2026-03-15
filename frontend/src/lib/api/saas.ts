import api from "./client";

/* ── Engines ────────────────────────────────────────────── */

export async function getEngines() {
  const res = await api.get("/saas/engines");
  return res.data;
}

export async function registerEngine(data: {
  engine_key: string;
  display_name: string;
  category: "FREE" | "PAID";
  description?: string;
}) {
  const res = await api.post("/saas/engines/register", data);
  return res.data;
}

/* ── Combos ─────────────────────────────────────────────── */

export async function getCombos() {
  const res = await api.get("/saas/combos");
  return res.data;
}

export async function defineCombo(data: {
  name: string;
  slug: string;
  description?: string;
  business_model: "B2B" | "B2C" | "BOTH";
  paid_engines: string[];
  max_branches?: number;
  max_users?: number;
  max_api_calls_per_month?: number;
  max_documents_per_month?: number;
}) {
  const res = await api.post("/saas/combos/define", data);
  return res.data;
}

export async function updateCombo(data: {
  combo_id: string;
  name?: string;
  description?: string;
  paid_engines?: string[];
  max_branches?: number;
  max_users?: number;
}) {
  const res = await api.post("/saas/combos/update", data);
  return res.data;
}

export async function deactivateCombo(data: { combo_id: string }) {
  const res = await api.post("/saas/combos/deactivate", data);
  return res.data;
}

export async function setComboRate(data: {
  combo_id: string;
  region_code: string;
  currency: string;
  monthly_amount: number;
}) {
  const res = await api.post("/saas/combos/set-rate", data);
  return res.data;
}

/* ── Pricing ────────────────────────────────────────────── */

export async function getPricing(params: { region_code?: string; business_model?: string }) {
  const res = await api.get("/saas/pricing", { params });
  return res.data;
}

/* ── Trial Policy ───────────────────────────────────────── */

export async function getTrialPolicy() {
  const res = await api.get("/saas/trial-policy");
  return res.data;
}

export async function setTrialPolicy(data: {
  default_trial_days: number;
  max_trial_days: number;
  grace_period_days: number;
  rate_notice_days: number;
}) {
  const res = await api.post("/saas/trial-policy/set", data);
  return res.data;
}

/* ── Trials ─────────────────────────────────────────────── */

export async function getTrialAgreement(businessId: string) {
  const res = await api.get("/saas/trials/agreement", { params: { business_id: businessId } });
  return res.data;
}

export async function createTrial(data: {
  business_id: string;
  combo_id: string;
  region_code: string;
  referral_code?: string;
}) {
  const res = await api.post("/saas/trials/create", data);
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

/* ── Rate Governance ────────────────────────────────────── */

export async function getEffectiveRate(businessId: string) {
  const res = await api.get("/saas/rates/effective", { params: { business_id: businessId } });
  return res.data;
}

export async function publishRateChange(data: {
  combo_id: string;
  region_code: string;
  old_amount: number;
  new_amount: number;
  currency: string;
  effective_from: string;
}) {
  const res = await api.post("/saas/rates/publish-change", data);
  return res.data;
}

/* ── Promotions ─────────────────────────────────────────── */

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
  combo_ids?: string[];
  discount_pct?: number;
  discount_months?: number;
  credit_amount?: number;
  credit_currency?: string;
  credit_expires_months?: number;
  extra_trial_days?: number;
  bonus_engine?: string;
  bonus_months?: number;
  bundle_engines?: string[];
  bundle_discount_pct?: number;
}) {
  const res = await api.post("/saas/promos/create", data);
  return res.data;
}

export async function redeemPromo(data: {
  promo_code: string;
  business_id: string;
  region_code?: string;
  combo_id?: string;
}) {
  const res = await api.post("/saas/promos/redeem", data);
  return res.data;
}

/* ── Referrals ──────────────────────────────────────────── */

export async function setReferralPolicy(data: {
  referrer_reward_days: number;
  referee_bonus_days: number;
  qualification_days: number;
  qualification_min_transactions: number;
  max_referrals_per_year: number;
  champion_threshold: number;
}) {
  const res = await api.post("/saas/referrals/set-policy", data);
  return res.data;
}

export async function generateReferralCode(data: {
  business_id: string;
  business_name: string;
}) {
  const res = await api.post("/saas/referrals/generate-code", data);
  return res.data;
}

export async function submitReferral(data: {
  referral_code: string;
  referee_business_id: string;
  referee_phone?: string;
}) {
  const res = await api.post("/saas/referrals/submit", data);
  return res.data;
}

export async function qualifyReferral(data: {
  referee_business_id: string;
}) {
  const res = await api.post("/saas/referrals/qualify", data);
  return res.data;
}

/* ── Resellers ──────────────────────────────────────────── */

export async function getResellers() {
  const res = await api.get("/saas/resellers");
  return res.data;
}

export async function registerReseller(data: {
  company_name: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  region_codes?: string[];
  payout_method: "MPESA" | "MOBILE_MONEY" | "BANK_TRANSFER";
  payout_phone?: string;
  bank_name?: string;
  account_number?: string;
  account_name?: string;
}) {
  const res = await api.post("/saas/resellers/register", data);
  return res.data;
}

export async function linkTenant(data: {
  reseller_id: string;
  business_id: string;
}) {
  const res = await api.post("/saas/resellers/link-tenant", data);
  return res.data;
}

export async function accrueCommission(data: {
  reseller_id: string;
  business_id: string;
  tenant_monthly_amount: number;
  currency: string;
  period: string;
}) {
  const res = await api.post("/saas/resellers/accrue-commission", data);
  return res.data;
}

export async function requestPayout(data: {
  reseller_id: string;
  amount: number;
  currency: string;
}) {
  const res = await api.post("/saas/resellers/request-payout", data);
  return res.data;
}

/* ── Subscriptions ──────────────────────────────────────── */

export async function getSubscription(businessId: string) {
  const res = await api.get("/saas/subscriptions", { params: { business_id: businessId } });
  return res.data;
}

export async function startTrial(data: {
  business_id: string;
  combo_id: string;
  trial_agreement_id?: string;
}) {
  const res = await api.post("/saas/subscriptions/start-trial", data);
  return res.data;
}

export async function activateSubscription(data: {
  business_id: string;
  plan_id?: string;
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

export async function changeCombo(data: {
  business_id: string;
  new_combo_id: string;
}) {
  const res = await api.post("/saas/subscriptions/change-combo", data);
  return res.data;
}
