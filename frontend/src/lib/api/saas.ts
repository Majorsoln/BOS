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

/* ── Region Detail & Lifecycle ────────────────────────────────── */

export async function getRegionDetail(regionCode: string) {
  const res = await api.get(`/saas/regions/${regionCode}/detail`);
  return res.data;
}

export async function launchRegion(data: { region_code: string; notes?: string }) {
  const res = await api.post("/saas/regions/launch", data);
  return res.data;
}

export async function suspendRegion(data: { region_code: string; reason: string }) {
  const res = await api.post("/saas/regions/suspend", data);
  return res.data;
}

export async function reactivateRegion(data: { region_code: string; notes?: string }) {
  const res = await api.post("/saas/regions/reactivate", data);
  return res.data;
}

export async function sunsetRegion(data: { region_code: string; reason: string }) {
  const res = await api.post("/saas/regions/sunset", data);
  return res.data;
}

/* ── Region Payment Channels ─────────────────────────────────── */

export async function getRegionPaymentChannels(regionCode: string) {
  const res = await api.get(`/saas/regions/${regionCode}/payment-channels`);
  return res.data;
}

export async function setRegionPaymentChannel(data: {
  region_code: string;
  channel_key: string;
  display_name: string;
  provider: string;
  channel_type: string;
  is_active?: boolean;
  config?: Record<string, string>;
  min_amount?: number;
  max_amount?: number;
  settlement_delay_days?: number;
}) {
  const res = await api.post("/saas/regions/set-payment-channel", data);
  return res.data;
}

export async function removeRegionPaymentChannel(data: {
  region_code: string;
  channel_key: string;
}) {
  const res = await api.post("/saas/regions/remove-payment-channel", data);
  return res.data;
}

/* ── Region Settlement Accounts ──────────────────────────────── */

export async function getRegionSettlementAccounts(regionCode: string) {
  const res = await api.get(`/saas/regions/${regionCode}/settlement-accounts`);
  return res.data;
}

export async function setRegionSettlement(data: {
  region_code: string;
  bank_name: string;
  account_name: string;
  account_number: string;
  branch_code?: string;
  swift_code?: string;
  currency: string;
  is_primary?: boolean;
}) {
  const res = await api.post("/saas/regions/set-settlement", data);
  return res.data;
}

/* ── Region Dashboard ────────────────────────────────────────── */

export async function getRegionDashboard(regionCode: string) {
  const res = await api.get(`/saas/regions/${regionCode}/dashboard`);
  return res.data;
}

/* ── Region Performance & Resellers ──────────────────────────── */

export async function getRegionResellers(regionCode: string) {
  const res = await api.get(`/saas/regions/${regionCode}/resellers`);
  return res.data;
}

export async function getRegionPerformance(regionCode: string) {
  const res = await api.get(`/saas/regions/${regionCode}/performance`);
  return res.data;
}

export async function getRegionSummary(regionCode: string) {
  const res = await api.get(`/saas/regions/${regionCode}/summary`);
  return res.data;
}

export async function getRegionTerritories(regionCode: string) {
  const res = await api.get(`/saas/regions/${regionCode}/territories`);
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

/* ── Compliance Packs ─────────────────────────────────────── */

export async function listCompliancePacks(regionCode?: string) {
  const params: Record<string, string> = {};
  if (regionCode) params.region_code = regionCode;
  const res = await api.get("/saas/compliance-packs", { params });
  return res.data;
}

export async function getLatestCompliancePack(regionCode: string) {
  const res = await api.get(`/saas/compliance-packs/${regionCode}/latest`);
  return res.data;
}

export async function getCompliancePack(regionCode: string, version: number) {
  const res = await api.get(`/saas/compliance-packs/${regionCode}/${version}`);
  return res.data;
}

export async function publishCompliancePack(data: {
  region_code: string;
  display_name: string;
  effective_date: string;
  tax_rules: Array<{
    tax_code: string;
    rate: number;
    description: string;
    applies_to: string[];
    is_compound?: boolean;
    category?: string;
    threshold_amount?: number;
    exemption_codes?: string[];
    reverse_charge_applicable?: boolean;
    withholding_rate?: number;
    effective_from?: string;
    effective_until?: string;
  }>;
  receipt_requirements: {
    require_sequential_number: boolean;
    require_tax_number: boolean;
    require_customer_tax_id?: boolean;
    require_digital_signature?: boolean;
    require_qr_code?: boolean;
    number_prefix_format?: string;
  };
  data_retention: {
    financial_records_years: number;
    audit_log_years: number;
    personal_data_years: number;
    region_law_reference: string;
    consent_records_years?: number;
    tax_records_years?: number;
    employee_records_years?: number;
    destruction_method?: string;
  };
  required_invoice_fields: string[];
  optional_invoice_fields: string[];
  change_summary: string;
  // E-Invoicing
  e_invoicing?: {
    mandate_active: boolean;
    system_name?: string;
    regulatory_body?: string;
    api_endpoint_ref?: string;
    transmission_mode?: string;
    requires_device_registration?: boolean;
    device_type?: string;
    qr_code_required?: boolean;
    digital_signature_required?: boolean;
    invoice_number_format?: string;
    max_offline_hours?: number;
    penalty_reference?: string;
  };
  // Invoice Format Rules
  invoice_format?: {
    required_header_fields?: string[];
    required_line_fields?: string[];
    required_footer_fields?: string[];
    document_language?: string;
    secondary_language?: string;
    currency_decimal_places?: number;
    date_format?: string;
    tax_breakdown_required?: boolean;
    credit_note_must_reference_invoice?: boolean;
    pro_forma_legally_binding?: boolean;
    max_payment_terms_days?: number;
  };
  // Cross-Border Rules
  cross_border?: {
    reverse_charge_on_imports?: boolean;
    reverse_charge_threshold?: number;
    withholding_on_foreign_services?: boolean;
    withholding_rate?: number;
    transfer_pricing_doc_required?: boolean;
    permanent_establishment_rules?: string;
    double_tax_treaty_countries?: string[];
  };
  // Digital Signature
  digital_signature?: {
    require_digital_signature?: boolean;
    signature_algorithm?: string;
    certificate_authority?: string;
    timestamp_required?: boolean;
    signature_visible_on_pdf?: boolean;
  };
  // Additional governance fields
  fiscal_year_start_month?: number;
  reporting_frequency?: string;
  vat_return_frequency?: string;
  currency_code?: string;
  law_reference_url?: string;
}) {
  const res = await api.post("/saas/compliance-packs/publish", data);
  return res.data;
}

export async function deprecateCompliancePack(data: {
  region_code: string;
  version: number;
  superseded_by_version: number;
}) {
  const res = await api.post("/saas/compliance-packs/deprecate", data);
  return res.data;
}

export async function pinTenantPack(data: {
  tenant_id: string;
  region_code: string;
  version: number;
}) {
  const res = await api.post("/saas/compliance-packs/pin-tenant", data);
  return res.data;
}

export async function upgradeTenantPack(data: {
  tenant_id: string;
  region_code: string;
  to_version: number;
}) {
  const res = await api.post("/saas/compliance-packs/upgrade-tenant", data);
  return res.data;
}

/* ── Tenant Compliance Onboarding ─────────────────────────── */

export async function listCountryPolicies() {
  const res = await api.get("/saas/compliance/country-policies");
  return res.data;
}

export async function setCountryPolicy(data: {
  country_code: string;
  country_name: string;
  b2b_allowed?: boolean;
  b2c_allowed?: boolean;
  vat_registration_required?: boolean;
  company_registration_required?: boolean;
  requires_tax_id?: boolean;
  requires_physical_address?: boolean;
  default_trial_days?: number;
  grace_period_days?: number;
  manual_review_required?: boolean;
  active?: boolean;
  // E-Invoicing
  e_invoicing_mandatory?: boolean;
  e_invoicing_system?: string;
  e_invoicing_deadline?: string;
  fiscal_device_required?: boolean;
  // Entity Types
  allowed_entity_types?: string[];
  ngo_tax_exempt?: boolean;
  government_procurement_rules?: boolean;
  cooperative_registration_required?: boolean;
  // Tax Configuration
  tax_exemption_categories?: string[];
  vat_registration_threshold?: number;
  withholding_tax_applicable?: boolean;
  digital_services_tax?: boolean;
  // Document & Language
  document_language?: string;
  secondary_document_language?: string;
  receipt_qr_code_required?: boolean;
  // Privacy & Data Governance
  privacy_regime?: string;
  privacy_regulator?: string;
  data_controller_model?: string;
  consent_required_for_processing?: boolean;
  consent_required_for_marketing?: boolean;
  data_localization_rule?: string;
  cross_border_transfer_allowed?: boolean;
  cross_border_transfer_requires_adequacy?: boolean;
  cross_border_approved_countries?: string[];
  breach_notification_hours?: number;
  data_subject_access_days?: number;
  right_to_erasure?: boolean;
  data_protection_officer_required?: boolean;
  privacy_impact_assessment_required?: boolean;
  // Reporting & Fiscal
  fiscal_year_start_month?: number;
  vat_return_frequency?: string;
  income_tax_return_frequency?: string;
  statutory_audit_required?: boolean;
  reporting_currency?: string;
  // Compliance Automation
  auto_compliance_checks?: boolean;
  grace_period_after_law_change_days?: number;
  penalty_reference?: string;
  escalation_contact?: string;
}) {
  const res = await api.post("/saas/compliance/set-country-policy", data);
  return res.data;
}

export async function submitComplianceProfile(data: {
  business_id: string;
  country_code: string;
  customer_type: string;
  legal_name: string;
  trade_name?: string;
  tax_id?: string;
  company_registration_number?: string;
  physical_address?: string;
  city?: string;
  contact_email?: string;
  contact_phone?: string;
}) {
  const res = await api.post("/saas/compliance/submit-profile", data);
  return res.data;
}

export async function reviewComplianceProfile(data: {
  profile_id: string;
  decision: "approve" | "reject";
  reviewer_id: string;
  reason?: string;
}) {
  const res = await api.post("/saas/compliance/review-profile", data);
  return res.data;
}

export async function activateComplianceProfile(data: { profile_id: string }) {
  const res = await api.post("/saas/compliance/activate-profile", data);
  return res.data;
}

export async function suspendComplianceProfile(data: {
  profile_id: string;
  reason: string;
}) {
  const res = await api.post("/saas/compliance/suspend-profile", data);
  return res.data;
}

export async function reactivateComplianceProfile(data: {
  profile_id: string;
  reason?: string;
}) {
  const res = await api.post("/saas/compliance/reactivate-profile", data);
  return res.data;
}

export async function getComplianceProfile(businessId: string) {
  const res = await api.get("/saas/compliance/profile", {
    params: { business_id: businessId },
  });
  return res.data;
}
