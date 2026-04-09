import api from "./client";
import type { PlatformAdminRole } from "@/stores/platform-auth-store";

/* ── Platform Identity ───────────────────────────────────── */

export async function getPlatformMe(email?: string) {
  const params = email ? { email } : {};
  const res = await api.get("/platform/me", { params });
  return res.data;
}

/* ── Platform Admin Management ───────────────────────────── */

export async function getPlatformAdmins(role?: PlatformAdminRole) {
  const params = role ? { role } : {};
  const res = await api.get("/platform/admins", { params });
  return res.data;
}

export async function addPlatformAdmin(data: {
  name: string;
  email: string;
  role: PlatformAdminRole;
  created_by?: string;
}) {
  const res = await api.post("/platform/admins/add", data);
  return res.data;
}

export async function updatePlatformAdminRole(data: {
  admin_id: string;
  role: PlatformAdminRole;
}) {
  const res = await api.post("/platform/admins/update-role", data);
  return res.data;
}

export async function suspendPlatformAdmin(admin_id: string) {
  const res = await api.post("/platform/admins/suspend", { admin_id });
  return res.data;
}

export async function reinstatePlatformAdmin(admin_id: string) {
  const res = await api.post("/platform/admins/reinstate", { admin_id });
  return res.data;
}

/* ── Regional Rollup ─────────────────────────────────────── */

export async function getRegionsRollup(period?: string) {
  const params = period ? { period } : {};
  const res = await api.get("/platform/regions/rollup", { params });
  return res.data;
}

/* ── Remittance Oversight ────────────────────────────────── */

export async function getRemittanceOverdue(grace_days?: number) {
  const params = grace_days !== undefined ? { grace_days } : {};
  const res = await api.get("/platform/remittance/overdue", { params });
  return res.data;
}

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
