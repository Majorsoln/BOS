import api from "./client";

/* ── Agent Management (Platform Admin) ───────────────────── */

export async function getAgents(params?: { type?: string; status?: string; territory?: string }) {
  const res = await api.get("/saas/agents", { params });
  return res.data;
}

export async function getAgent(agentId: string) {
  const res = await api.get(`/saas/agents/${agentId}`);
  return res.data;
}

export async function registerAgent(data: {
  agent_name: string;
  contact_email: string;
  contact_phone: string;
  agent_type: "REGION_LICENSE_AGENT" | "REMOTE_AGENT" | "RESELLER";
  territory?: string;
  region_codes?: string[];
  contact_person?: string;
  payout_method?: string;
  payout_phone?: string;
  payout_bank_name?: string;
  payout_account_number?: string;
  notes?: string;
}) {
  const res = await api.post("/saas/agents/register", data);
  return res.data;
}

export async function suspendAgent(data: { agent_id: string; reason: string }) {
  const res = await api.post("/saas/agents/suspend", data);
  return res.data;
}

export async function reinstateAgent(data: { agent_id: string }) {
  const res = await api.post("/saas/agents/reinstate", data);
  return res.data;
}

export async function terminateAgent(data: { agent_id: string; reason: string }) {
  const res = await api.post("/saas/agents/terminate", data);
  return res.data;
}

export async function updateAgent(data: {
  agent_id: string;
  agent_name?: string;
  contact_email?: string;
  contact_phone?: string;
  contact_person?: string;
  notes?: string;
}) {
  const res = await api.post("/saas/agents/update", data);
  return res.data;
}

/* ── Agent-Tenant Linking ───────────────────────────────────── */

export async function linkTenantToAgent(data: {
  agent_id: string;
  business_id: string;
}) {
  const res = await api.post("/saas/agents/link-tenant", data);
  return res.data;
}

export async function accrueCommission(data: {
  agent_id: string;
  business_id: string;
  tenant_monthly_amount: number;
  currency: string;
  period: string;
}) {
  const res = await api.post("/saas/agents/accrue-commission", data);
  return res.data;
}

/* ── Commission Settings ─────────────────────────────────── */

export async function getCommissionRanges() {
  const res = await api.get("/saas/agents/commission-ranges");
  return res.data;
}

export async function setCommissionRanges(data: {
  ranges: { min_tenants: number; max_tenants: number; rate_pct: number }[];
  residual_rate_pct: number;
  first_year_bonus_pct: number;
}) {
  const res = await api.post("/saas/agents/commission-ranges/set", data);
  return res.data;
}

/* ── Payouts ─────────────────────────────────────────────── */

export async function getAgentPayouts(params?: { agent_id?: string; status?: string }) {
  const res = await api.get("/saas/agents/payouts", { params });
  return res.data;
}

export async function approvePayout(data: { payout_id: string }) {
  const res = await api.post("/saas/agents/payouts/approve", data);
  return res.data;
}

export async function rejectPayout(data: { payout_id: string; reason: string }) {
  const res = await api.post("/saas/agents/payouts/reject", data);
  return res.data;
}

/* ── Governance ──────────────────────────────────────────── */

export async function grantGovernance(data: {
  agent_id: string;
  governance_role: "LICENSE_AGENT" | "REGION_AGENT";
  region_code: string;
  can_file_taxes?: boolean;
  max_tenants?: number;
  can_appoint_sub_agents?: boolean;
}) {
  const res = await api.post("/saas/agents/grant-governance", data);
  return res.data;
}

export async function revokeGovernance(data: {
  agent_id: string;
  reason: string;
}) {
  const res = await api.post("/saas/agents/revoke-governance", data);
  return res.data;
}

/* ── Escalations ─────────────────────────────────────────── */

export async function createEscalation(data: {
  agent_id: string;
  region_code: string;
  subject_type: string;
  subject_id?: string;
  description: string;
  severity: string;
}) {
  const res = await api.post("/saas/agents/escalations/create", data);
  return res.data;
}

export async function resolveEscalation(data: {
  escalation_id: string;
  resolution: string;
}) {
  const res = await api.post("/saas/agents/escalations/resolve", data);
  return res.data;
}

/* ── Tenant Transfers ────────────────────────────────────── */

export async function getTransferRequests(params?: { status?: string }) {
  const res = await api.get("/saas/agents/transfers", { params });
  return res.data;
}

export async function approveTransfer(data: { transfer_id: string }) {
  const res = await api.post("/saas/agents/transfers/approve", data);
  return res.data;
}

export async function denyTransfer(data: { transfer_id: string; reason: string }) {
  const res = await api.post("/saas/agents/transfers/deny", data);
  return res.data;
}

/* ── Discount Governance ─────────────────────────────────── */

export async function getDiscountGovernance() {
  const res = await api.get("/saas/discount-governance");
  return res.data;
}

export async function setDiscountGovernance(data: {
  max_platform_discount_pct?: number;
  max_trial_days?: number;
  max_rla_funded_discount_pct?: number;
}) {
  const res = await api.post("/saas/discount-governance/set", data);
  return res.data;
}

export async function getRlaDiscountSettings(agentId: string) {
  const res = await api.get("/saas/agents/rla-discount-settings", { params: { agent_id: agentId } });
  return res.data;
}

export async function setRlaDiscountSettings(data: {
  agent_id: string;
  platform_discount_pct?: number;
  rla_funded_discount_pct?: number;
  trial_days?: number;
}) {
  const res = await api.post("/saas/agents/rla-discount-settings", data);
  return res.data;
}

/* ── Agent Agreements ────────────────────────────────────── */

export async function getAgentAgreements(agentId: string) {
  const res = await api.get("/saas/agents/agreements", { params: { agent_id: agentId } });
  return res.data;
}

/* ── Agent Portal API ────────────────────────────────────── */

export async function getAgentDashboard() {
  const res = await api.get("/agent/dashboard");
  return res.data;
}

export async function getMyTenants(params?: { status?: string }) {
  const res = await api.get("/agent/tenants", { params });
  return res.data;
}

export async function onboardTenant(data: {
  business_name: string;
  business_type: string;
  country: string;
  city: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  service_category: string;
  estimated_doc_volume: string;
  ai_tier: string;
  branch_count: number;
  billing_model: string;
  buyer_type: string;
  tax_number?: string;
}) {
  const res = await api.post("/agent/tenants/onboard", data);
  return res.data;
}

export async function getMyCommissions(params?: { period?: string }) {
  const res = await api.get("/agent/commissions", { params });
  return res.data;
}

export async function requestMyPayout(data: { amount: number; currency: string; method: string }) {
  const res = await api.post("/agent/payouts/request", data);
  return res.data;
}

export async function getMyPromotions() {
  const res = await api.get("/agent/promotions");
  return res.data;
}

export async function createMyPromotion(data: {
  promo_code: string;
  discount_pct: number;
  max_uses: number;
  valid_until: string;
  description?: string;
}) {
  const res = await api.post("/agent/promotions/create", data);
  return res.data;
}

export async function requestCostShare(data: {
  promotion_description: string;
  total_cost: number;
  requested_platform_share_pct: number;
  justification: string;
}) {
  const res = await api.post("/agent/cost-share/request", data);
  return res.data;
}

export async function getMySupportTickets(params?: { status?: string }) {
  const res = await api.get("/agent/support/tickets", { params });
  return res.data;
}

export async function createSupportTicket(data: {
  tenant_id: string;
  category: string;
  subject: string;
  description: string;
  priority: string;
}) {
  const res = await api.post("/agent/support/tickets/create", data);
  return res.data;
}

export async function escalateTicket(data: { ticket_id: string; reason: string }) {
  const res = await api.post("/agent/support/tickets/escalate", data);
  return res.data;
}

export async function submitComplianceDoc(data: {
  doc_type: string;
  title: string;
  summary: string;
  file_url?: string;
}) {
  const res = await api.post("/agent/compliance/submit", data);
  return res.data;
}

export async function getComplianceDocs() {
  const res = await api.get("/agent/compliance");
  return res.data;
}

export async function getMyAgreement() {
  const res = await api.get("/agent/agreement");
  return res.data;
}

export async function getMarketIntelligence() {
  const res = await api.get("/agent/market");
  return res.data;
}

export async function requestAgentTransfer(data: {
  tenant_id: string;
  reason: string;
}) {
  const res = await api.post("/agent/tenants/request-transfer", data);
  return res.data;
}
