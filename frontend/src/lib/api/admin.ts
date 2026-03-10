import api from "./client";

/* ── Business ──────────────────────────────────────────── */

export async function getBusinessProfile() {
  const { data } = await api.get("/admin/business");
  return data;
}

export async function updateBusinessProfile(fields: Record<string, string>) {
  const { data } = await api.post("/admin/business/update", fields);
  return data;
}

/* ── Branches ──────────────────────────────────────────── */

export async function listBranches() {
  const { data } = await api.get("/admin/branches");
  return data;
}

/* ── Roles ─────────────────────────────────────────────── */

export async function listRoles() {
  const { data } = await api.get("/admin/roles");
  return data;
}

export async function createRole(name: string, permissions: string[]) {
  const { data } = await api.post("/admin/roles/create", { name, permissions });
  return data;
}

export async function assignRole(actorId: string, roleId: string, branchId?: string) {
  const { data } = await api.post("/admin/roles/assign", {
    actor_id: actorId,
    role_id: roleId,
    branch_id: branchId,
  });
  return data;
}

export async function revokeRole(actorId: string, roleId: string) {
  const { data } = await api.post("/admin/roles/revoke", {
    actor_id: actorId,
    role_id: roleId,
  });
  return data;
}

/* ── Actors ────────────────────────────────────────────── */

export async function listActors() {
  const { data } = await api.get("/admin/actors");
  return data;
}

export async function deactivateActor(actorId: string) {
  const { data } = await api.post("/admin/actors/deactivate", { actor_id: actorId });
  return data;
}

/* ── API Keys ──────────────────────────────────────────── */

export async function listApiKeys() {
  const { data } = await api.get("/admin/api-keys");
  return data;
}

export async function createApiKey(actorId: string, actorType: string, scopes: Record<string, string[]>) {
  const { data } = await api.post("/admin/api-keys/create", {
    actor_id: actorId,
    actor_type: actorType,
    scopes,
  });
  return data;
}

export async function revokeApiKey(keyId: string) {
  const { data } = await api.post("/admin/api-keys/revoke", { key_id: keyId });
  return data;
}

/* ── Feature Flags ─────────────────────────────────────── */

export async function listFeatureFlags() {
  const { data } = await api.get("/admin/feature-flags");
  return data;
}

export async function setFeatureFlag(flagName: string, enabled: boolean) {
  const { data } = await api.post("/admin/feature-flags/set", {
    flag_name: flagName,
    enabled,
  });
  return data;
}

export async function clearFeatureFlag(flagName: string) {
  const { data } = await api.post("/admin/feature-flags/clear", { flag_name: flagName });
  return data;
}

/* ── Tax Rules ─────────────────────────────────────────── */

export async function listTaxRules() {
  const { data } = await api.get("/admin/tax-rules");
  return data;
}

export async function setTaxRule(taxCode: string, rate: number) {
  const { data } = await api.post("/admin/tax-rules/set", { tax_code: taxCode, rate });
  return data;
}

/* ── Customers ─────────────────────────────────────────── */

export async function listCustomers() {
  const { data } = await api.get("/admin/customers");
  return data;
}

export async function createCustomer(fields: { display_name: string; phone?: string; email?: string; address?: string }) {
  const { data } = await api.post("/admin/customers/create", fields);
  return data;
}

export async function updateCustomer(customerId: string, fields: Record<string, string>) {
  const { data } = await api.post("/admin/customers/update", { customer_id: customerId, ...fields });
  return data;
}

/* ── Documents ─────────────────────────────────────────── */

export async function listDocuments(cursor?: string) {
  const params: Record<string, string> = {};
  if (cursor) params.cursor = cursor;
  const { data } = await api.get("/docs", { params });
  return data;
}

export async function getDocumentRenderPlan(documentId: string) {
  const { data } = await api.get(`/docs/${documentId}/render-plan`);
  return data;
}

export async function getDocumentHtml(documentId: string, locale?: string) {
  const params: Record<string, string> = {};
  if (locale) params.locale = locale;
  const { data } = await api.get(`/docs/${documentId}/render-html`, { params });
  return data;
}

export async function getDocumentPdf(documentId: string) {
  const response = await api.get(`/docs/${documentId}/render-pdf`, {
    responseType: "blob",
  });
  return response.data;
}
