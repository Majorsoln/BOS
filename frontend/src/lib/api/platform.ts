import api from "./client";

/* ── Platform Audit Log ──────────────────────────────────── */

export async function getAuditLog(params?: {
  subject_id?: string;
  actor_id?: string;
  event_type?: string;
  limit?: number;
}) {
  const res = await api.get("/platform/audit", { params });
  return res.data;
}

export async function getAuditEntry(entryId: string) {
  const res = await api.get(`/platform/audit/${entryId}`);
  return res.data;
}

export async function getTenantAuditHistory(tenantId: string) {
  const res = await api.get(`/platform/audit/tenant/${tenantId}`);
  return res.data;
}

/* ── Platform Health / Observability ──────────────────────── */

export async function getHealthSummary() {
  const res = await api.get("/platform/health");
  return res.data;
}

export async function getHealthSLOs() {
  const res = await api.get("/platform/health/slos");
  return res.data;
}

export async function getHealthBreaches() {
  const res = await api.get("/platform/health/breaches");
  return res.data;
}

export async function takeHealthSnapshot() {
  const res = await api.post("/platform/health/snapshot");
  return res.data;
}

/* ── Compliance Review Queue ─────────────────────────────── */

export async function getPendingProfiles(params?: {
  country_code?: string;
}) {
  const res = await api.get("/platform/compliance/pending", { params });
  return res.data;
}

export async function getComplianceStats() {
  const res = await api.get("/platform/compliance/stats");
  return res.data;
}

/* ── Compliance Audit Ledger ──────────────────────────────── */

export async function getComplianceAuditTrail(params?: {
  region_code?: string;
  limit?: number;
}) {
  const res = await api.get("/platform/compliance/audit", { params });
  return res.data;
}

/* ── Governance (Two-Level Admin Model) ───────────────────── */

export async function getGovernanceAgents(regionCode: string) {
  const res = await api.get("/platform/governance/agents", {
    params: { region_code: regionCode },
  });
  return res.data;
}

export async function getGovernanceEscalations(params?: {
  region_code?: string;
  status?: string;
}) {
  const res = await api.get("/platform/governance/escalations", { params });
  return res.data;
}
