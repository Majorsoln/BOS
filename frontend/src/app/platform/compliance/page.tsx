"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
  Badge, Button, Input, Label, Select, Separator, Table, TableBody,
  TableCell, TableHead, TableHeader, TableRow, Toast, Textarea,
} from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import {
  listCompliancePacks, publishCompliancePack, deprecateCompliancePack,
  pinTenantPack, upgradeTenantPack,
  listCountryPolicies, setCountryPolicy,
  getComplianceProfile, reviewComplianceProfile,
  activateComplianceProfile, suspendComplianceProfile, reactivateComplianceProfile,
} from "@/lib/api/saas";
import { REGIONS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";

type TabKey = "packs" | "policies" | "profiles";

interface CompliancePack {
  region_code: string;
  version: number;
  pack_ref: string;
  display_name: string;
  effective_date: string;
  published_at: string;
  published_by: string;
  change_summary: string;
  deprecated: boolean;
  tax_rules: Array<{ tax_code: string; rate: number; description: string }>;
  receipt_requirements: Record<string, boolean | string>;
  data_retention: Record<string, number | string>;
}

interface CountryPolicyType {
  country_code: string;
  country_name: string;
  b2b_allowed: boolean;
  b2c_allowed: boolean;
  vat_registration_required: boolean;
  company_registration_required: boolean;
  requires_tax_id: boolean;
  requires_physical_address: boolean;
  default_trial_days: number;
  grace_period_days: number;
  manual_review_required: boolean;
  active: boolean;
  version: number;
  // Governance fields
  e_invoicing_mandatory?: boolean;
  e_invoicing_system?: string;
  fiscal_device_required?: boolean;
  privacy_regime?: string;
  privacy_regulator?: string;
  breach_notification_hours?: number;
  data_subject_access_days?: number;
  right_to_erasure?: boolean;
  data_protection_officer_required?: boolean;
  document_language?: string;
  fiscal_year_start_month?: number;
  vat_return_frequency?: string;
  reporting_currency?: string;
  receipt_qr_code_required?: boolean;
  withholding_tax_applicable?: boolean;
  digital_services_tax?: boolean;
}

interface ComplianceProfileType {
  profile_id: string;
  business_id: string;
  country_code: string;
  customer_type: string;
  legal_name: string;
  trade_name: string;
  tax_id: string;
  company_registration_number: string;
  physical_address: string;
  city: string;
  contact_email: string;
  contact_phone: string;
  state: string;
  tax_id_verified: boolean;
  company_reg_verified: boolean;
  address_verified: boolean;
  eligible_for_billing: boolean;
  rejection_reason: string;
  reviewer_id: string;
  review_notes: string;
  created_at: string | null;
  updated_at: string | null;
  verified_at: string | null;
  pack_ref: string;
}

const STATE_BADGE_VARIANT: Record<string, "success" | "warning" | "destructive" | "outline" | "purple" | "secondary"> = {
  draft: "outline",
  submitted: "warning",
  under_review: "warning",
  verified: "purple",
  active: "success",
  restricted: "warning",
  suspended: "destructive",
  blocked: "destructive",
  rejected: "destructive",
  deactivated: "secondary",
};

export default function CompliancePage() {
  const [tab, setTab] = useState<TabKey>("packs");
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  // ── Packs tab state ──
  const [packRegion, setPackRegion] = useState("");
  const [showPublish, setShowPublish] = useState(false);
  const [publishData, setPublishData] = useState({
    region_code: "", display_name: "", effective_date: "", change_summary: "",
    tax_code: "", tax_rate: "", tax_description: "",
    tax_category: "STANDARD",
    require_sequential_number: true, require_tax_number: true,
    require_qr_code: false, number_prefix_format: "RCP-{YYYY}-{NNNNN}",
    financial_records_years: "7", audit_log_years: "7", personal_data_years: "5",
    consent_records_years: "5", tax_records_years: "7",
    region_law_reference: "",
    required_invoice_fields: "business_name,tax_id,date,invoice_number,line_items,total",
    optional_invoice_fields: "customer_tax_id,po_number,delivery_date",
    // E-Invoicing
    e_invoicing_active: false, e_invoicing_system: "", e_invoicing_regulatory_body: "",
    e_invoicing_transmission_mode: "REAL_TIME",
    e_invoicing_device_required: false, e_invoicing_qr_required: false,
    e_invoicing_signature_required: false, e_invoicing_max_offline_hours: "24",
    // Invoice Format
    invoice_tax_breakdown_required: true, invoice_credit_note_ref_required: true,
    invoice_document_language: "en", invoice_date_format: "YYYY-MM-DD",
    // Cross-Border
    cross_border_reverse_charge: false, cross_border_withholding: false,
    cross_border_withholding_rate: "0", cross_border_transfer_pricing: false,
    // Digital Signature
    digital_signature_required: false, digital_signature_algorithm: "RSA-SHA256",
    digital_signature_timestamp: false,
    // Governance
    fiscal_year_start_month: "1", vat_return_frequency: "MONTHLY",
    law_reference_url: "",
  });
  const [publishing, setPublishing] = useState(false);

  // ── Policies tab state ──
  const [showAddPolicy, setShowAddPolicy] = useState(false);
  const [policyData, setPolicyData] = useState({
    country_code: "", country_name: "",
    b2b_allowed: true, b2c_allowed: true,
    vat_registration_required: false, company_registration_required: false,
    requires_tax_id: false, requires_physical_address: false,
    default_trial_days: 180, grace_period_days: 30,
    manual_review_required: false, active: true,
    // E-Invoicing
    e_invoicing_mandatory: false, e_invoicing_system: "", fiscal_device_required: false,
    // Privacy
    privacy_regime: "NONE", privacy_regulator: "",
    breach_notification_hours: 72, data_subject_access_days: 30,
    right_to_erasure: false, data_protection_officer_required: false,
    consent_required_for_processing: true, consent_required_for_marketing: true,
    // Document & Tax
    document_language: "en", receipt_qr_code_required: false,
    withholding_tax_applicable: false, digital_services_tax: false,
    // Fiscal & Reporting
    fiscal_year_start_month: 1, vat_return_frequency: "MONTHLY",
    reporting_currency: "", statutory_audit_required: false,
    // Compliance Automation
    auto_compliance_checks: true, escalation_contact: "",
  });
  const [savingPolicy, setSavingPolicy] = useState(false);

  // ── Profiles tab state ──
  const [profileSearch, setProfileSearch] = useState("");
  const [profile, setProfile] = useState<ComplianceProfileType | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [reviewTarget, setReviewTarget] = useState<ComplianceProfileType | null>(null);
  const [reviewDecision, setReviewDecision] = useState<"approve" | "reject">("approve");
  const [reviewReason, setReviewReason] = useState("");
  const [reviewing, setReviewing] = useState(false);

  const qc = useQueryClient();

  const packsQuery = useQuery({
    queryKey: ["saas", "compliance-packs", packRegion],
    queryFn: () => listCompliancePacks(packRegion || undefined),
  });
  const packs: CompliancePack[] = packsQuery.data?.packs ?? [];

  const policiesQuery = useQuery({
    queryKey: ["saas", "country-policies"],
    queryFn: listCountryPolicies,
  });
  const policies: CountryPolicyType[] = policiesQuery.data?.policies ?? [];

  // ── Publish pack ──
  async function handlePublish(e: React.FormEvent) {
    e.preventDefault();
    setPublishing(true);
    try {
      await publishCompliancePack({
        region_code: publishData.region_code,
        display_name: publishData.display_name,
        effective_date: publishData.effective_date,
        tax_rules: publishData.tax_code ? [{
          tax_code: publishData.tax_code,
          rate: parseFloat(publishData.tax_rate) || 0,
          description: publishData.tax_description,
          applies_to: ["GOODS", "SERVICES"],
          category: publishData.tax_category,
        }] : [],
        receipt_requirements: {
          require_sequential_number: publishData.require_sequential_number,
          require_tax_number: publishData.require_tax_number,
          require_qr_code: publishData.require_qr_code,
          require_digital_signature: publishData.digital_signature_required,
          number_prefix_format: publishData.number_prefix_format,
        },
        data_retention: {
          financial_records_years: parseInt(publishData.financial_records_years) || 7,
          audit_log_years: parseInt(publishData.audit_log_years) || 7,
          personal_data_years: parseInt(publishData.personal_data_years) || 5,
          region_law_reference: publishData.region_law_reference,
          consent_records_years: parseInt(publishData.consent_records_years) || 5,
          tax_records_years: parseInt(publishData.tax_records_years) || 7,
        },
        required_invoice_fields: publishData.required_invoice_fields.split(",").map((s) => s.trim()).filter(Boolean),
        optional_invoice_fields: publishData.optional_invoice_fields.split(",").map((s) => s.trim()).filter(Boolean),
        change_summary: publishData.change_summary,
        // E-Invoicing
        e_invoicing: publishData.e_invoicing_active ? {
          mandate_active: true,
          system_name: publishData.e_invoicing_system || undefined,
          regulatory_body: publishData.e_invoicing_regulatory_body || undefined,
          transmission_mode: publishData.e_invoicing_transmission_mode,
          requires_device_registration: publishData.e_invoicing_device_required,
          qr_code_required: publishData.e_invoicing_qr_required,
          digital_signature_required: publishData.e_invoicing_signature_required,
          max_offline_hours: parseInt(publishData.e_invoicing_max_offline_hours) || 24,
        } : undefined,
        // Invoice Format
        invoice_format: {
          document_language: publishData.invoice_document_language,
          date_format: publishData.invoice_date_format,
          tax_breakdown_required: publishData.invoice_tax_breakdown_required,
          credit_note_must_reference_invoice: publishData.invoice_credit_note_ref_required,
        },
        // Cross-Border
        cross_border: (publishData.cross_border_reverse_charge || publishData.cross_border_withholding) ? {
          reverse_charge_on_imports: publishData.cross_border_reverse_charge,
          withholding_on_foreign_services: publishData.cross_border_withholding,
          withholding_rate: parseFloat(publishData.cross_border_withholding_rate) || 0,
          transfer_pricing_doc_required: publishData.cross_border_transfer_pricing,
        } : undefined,
        // Digital Signature
        digital_signature: publishData.digital_signature_required ? {
          require_digital_signature: true,
          signature_algorithm: publishData.digital_signature_algorithm,
          timestamp_required: publishData.digital_signature_timestamp,
        } : undefined,
        // Governance
        fiscal_year_start_month: parseInt(publishData.fiscal_year_start_month) || 1,
        vat_return_frequency: publishData.vat_return_frequency,
        law_reference_url: publishData.law_reference_url || undefined,
      });
      setToast({ message: "Compliance pack published", variant: "success" });
      setShowPublish(false);
      qc.invalidateQueries({ queryKey: ["saas", "compliance-packs"] });
    } catch {
      setToast({ message: "Failed to publish pack", variant: "error" });
    } finally {
      setPublishing(false);
    }
  }

  // ── Save country policy ──
  async function handleSavePolicy(e: React.FormEvent) {
    e.preventDefault();
    setSavingPolicy(true);
    try {
      await setCountryPolicy({
        country_code: policyData.country_code,
        country_name: policyData.country_name,
        b2b_allowed: policyData.b2b_allowed,
        b2c_allowed: policyData.b2c_allowed,
        vat_registration_required: policyData.vat_registration_required,
        company_registration_required: policyData.company_registration_required,
        requires_tax_id: policyData.requires_tax_id,
        requires_physical_address: policyData.requires_physical_address,
        default_trial_days: policyData.default_trial_days,
        grace_period_days: policyData.grace_period_days,
        manual_review_required: policyData.manual_review_required,
        active: policyData.active,
        // E-Invoicing
        e_invoicing_mandatory: policyData.e_invoicing_mandatory,
        e_invoicing_system: policyData.e_invoicing_system || undefined,
        fiscal_device_required: policyData.fiscal_device_required,
        // Privacy
        privacy_regime: policyData.privacy_regime || undefined,
        privacy_regulator: policyData.privacy_regulator || undefined,
        breach_notification_hours: policyData.breach_notification_hours,
        data_subject_access_days: policyData.data_subject_access_days,
        right_to_erasure: policyData.right_to_erasure,
        data_protection_officer_required: policyData.data_protection_officer_required,
        consent_required_for_processing: policyData.consent_required_for_processing,
        consent_required_for_marketing: policyData.consent_required_for_marketing,
        // Document & Tax
        document_language: policyData.document_language || undefined,
        receipt_qr_code_required: policyData.receipt_qr_code_required,
        withholding_tax_applicable: policyData.withholding_tax_applicable,
        digital_services_tax: policyData.digital_services_tax,
        // Fiscal & Reporting
        fiscal_year_start_month: policyData.fiscal_year_start_month,
        vat_return_frequency: policyData.vat_return_frequency || undefined,
        reporting_currency: policyData.reporting_currency || undefined,
        statutory_audit_required: policyData.statutory_audit_required,
        // Compliance Automation
        auto_compliance_checks: policyData.auto_compliance_checks,
        escalation_contact: policyData.escalation_contact || undefined,
      });
      setToast({ message: `Policy for ${policyData.country_code} saved`, variant: "success" });
      setShowAddPolicy(false);
      qc.invalidateQueries({ queryKey: ["saas", "country-policies"] });
    } catch {
      setToast({ message: "Failed to save policy", variant: "error" });
    } finally {
      setSavingPolicy(false);
    }
  }

  // ── Search profile ──
  async function handleSearchProfile() {
    if (!profileSearch.trim()) return;
    setProfileLoading(true);
    try {
      const res = await getComplianceProfile(profileSearch.trim());
      setProfile(res.profile || null);
      if (!res.profile) setToast({ message: "No compliance profile found", variant: "error" });
    } catch {
      setProfile(null);
      setToast({ message: "Failed to load profile", variant: "error" });
    } finally {
      setProfileLoading(false);
    }
  }

  // ── Review profile ──
  async function handleReview(e: React.FormEvent) {
    e.preventDefault();
    if (!reviewTarget) return;
    setReviewing(true);
    try {
      await reviewComplianceProfile({
        profile_id: reviewTarget.profile_id,
        decision: reviewDecision,
        reviewer_id: "platform-admin",
        reason: reviewReason,
      });
      setToast({ message: `Profile ${reviewDecision === "approve" ? "approved" : "rejected"}`, variant: "success" });
      setReviewTarget(null);
      setReviewReason("");
      handleSearchProfile(); // reload
    } catch {
      setToast({ message: "Failed to review profile", variant: "error" });
    } finally {
      setReviewing(false);
    }
  }

  // ── Quick actions on profile ──
  async function handleProfileAction(action: "activate" | "suspend" | "reactivate", reason?: string) {
    if (!profile) return;
    try {
      if (action === "activate") await activateComplianceProfile({ profile_id: profile.profile_id });
      if (action === "suspend") await suspendComplianceProfile({ profile_id: profile.profile_id, reason: reason || "Admin action" });
      if (action === "reactivate") await reactivateComplianceProfile({ profile_id: profile.profile_id, reason: reason || "Admin action" });
      setToast({ message: `Profile ${action}d`, variant: "success" });
      handleSearchProfile();
    } catch {
      setToast({ message: `Failed to ${action} profile`, variant: "error" });
    }
  }

  return (
    <div>
      <PageHeader title="Compliance Management" description="Compliance packs, country policies, and tenant verification" />

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-neutral-100 p-1 dark:bg-neutral-900">
        {([
          { key: "packs" as const, label: "Compliance Packs" },
          { key: "policies" as const, label: "Country Policies" },
          { key: "profiles" as const, label: "Tenant Profiles" },
        ]).map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-white text-neutral-900 shadow-sm dark:bg-neutral-800 dark:text-neutral-50"
                : "text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-50"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ═══ Packs Tab ═══ */}
      {tab === "packs" && (
        <>
          <div className="mb-4 flex items-center gap-3">
            <Select value={packRegion} onChange={(e) => setPackRegion(e.target.value)} className="w-48">
              <option value="">All Regions</option>
              {REGIONS.map((r) => (
                <option key={r.code} value={r.code}>{r.code} — {r.name}</option>
              ))}
            </Select>
            <Button size="sm" variant="outline" onClick={() => qc.invalidateQueries({ queryKey: ["saas", "compliance-packs"] })}>Refresh</Button>
            <Button size="sm" onClick={() => setShowPublish(true)}>Publish New Pack</Button>
          </div>

          <Card>
            <CardContent className="pt-6">
              {packsQuery.isLoading ? (
                <p className="text-sm text-neutral-400">Loading...</p>
              ) : packs.length === 0 ? (
                <EmptyState title="No compliance packs" description="Publish a compliance pack for a region to get started" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Pack Ref</TableHead>
                      <TableHead>Display Name</TableHead>
                      <TableHead>Region</TableHead>
                      <TableHead>Effective</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Tax Rules</TableHead>
                      <TableHead>Change Summary</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {packs.map((p) => (
                      <TableRow key={p.pack_ref}>
                        <TableCell className="font-mono text-sm">{p.pack_ref}</TableCell>
                        <TableCell className="font-medium">{p.display_name}</TableCell>
                        <TableCell><Badge variant="outline">{p.region_code}</Badge></TableCell>
                        <TableCell className="text-sm">{formatDate(p.effective_date)}</TableCell>
                        <TableCell>
                          <Badge variant={p.deprecated ? "destructive" : "success"}>
                            {p.deprecated ? "Deprecated" : "Active"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">{p.tax_rules?.length || 0} rules</TableCell>
                        <TableCell className="max-w-[200px] truncate text-sm text-neutral-500">{p.change_summary}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* ═══ Policies Tab ═══ */}
      {tab === "policies" && (
        <>
          <div className="mb-4 flex items-center gap-3">
            <Button size="sm" onClick={() => setShowAddPolicy(true)}>Add Country Policy</Button>
            <Button size="sm" variant="outline" onClick={() => qc.invalidateQueries({ queryKey: ["saas", "country-policies"] })}>Refresh</Button>
          </div>

          <Card>
            <CardContent className="pt-6">
              {policiesQuery.isLoading ? (
                <p className="text-sm text-neutral-400">Loading...</p>
              ) : policies.length === 0 ? (
                <EmptyState title="No country policies" description="Configure compliance policies per country" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Country</TableHead>
                      <TableHead>Business Model</TableHead>
                      <TableHead>Requirements</TableHead>
                      <TableHead>E-Invoicing</TableHead>
                      <TableHead>Privacy</TableHead>
                      <TableHead>Trial</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {policies.map((p) => (
                      <TableRow key={p.country_code}>
                        <TableCell className="font-medium">{p.country_code} — {p.country_name}</TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            {p.b2b_allowed && <Badge variant="outline" className="text-xs">B2B</Badge>}
                            {p.b2c_allowed && <Badge variant="outline" className="text-xs">B2C</Badge>}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {p.vat_registration_required && <Badge variant="secondary" className="text-xs">VAT Reg</Badge>}
                            {p.requires_tax_id && <Badge variant="secondary" className="text-xs">Tax ID</Badge>}
                            {p.withholding_tax_applicable && <Badge variant="secondary" className="text-xs">WHT</Badge>}
                            {p.digital_services_tax && <Badge variant="secondary" className="text-xs">DST</Badge>}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {p.e_invoicing_mandatory ? (
                              <Badge variant="purple" className="text-xs">{p.e_invoicing_system || "Required"}</Badge>
                            ) : (
                              <Badge variant="outline" className="text-xs">Not Required</Badge>
                            )}
                            {p.fiscal_device_required && <Badge variant="secondary" className="text-xs">Fiscal Device</Badge>}
                          </div>
                        </TableCell>
                        <TableCell>
                          {p.privacy_regime && p.privacy_regime !== "NONE" ? (
                            <Badge variant="purple" className="text-xs">{p.privacy_regime.replace(/_/g, " ")}</Badge>
                          ) : (
                            <Badge variant="outline" className="text-xs">None</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-sm">{p.default_trial_days}d + {p.grace_period_days}d grace</TableCell>
                        <TableCell>
                          <Badge variant={p.active ? "success" : "secondary"}>
                            {p.active ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* ═══ Profiles Tab ═══ */}
      {tab === "profiles" && (
        <>
          <div className="mb-4 flex items-center gap-3">
            <Input
              value={profileSearch}
              onChange={(e) => setProfileSearch(e.target.value)}
              placeholder="Enter Business ID (UUID)"
              className="w-80"
              onKeyDown={(e) => e.key === "Enter" && handleSearchProfile()}
            />
            <Button size="sm" onClick={handleSearchProfile} disabled={profileLoading}>
              {profileLoading ? "Searching..." : "Search"}
            </Button>
          </div>

          {profile && (
            <div className="space-y-4">
              {/* Profile Info */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>{profile.legal_name || profile.business_id}</CardTitle>
                    <CardDescription>
                      {profile.country_code} | {profile.customer_type} | Business: {profile.business_id.slice(0, 12)}...
                    </CardDescription>
                  </div>
                  <Badge variant={STATE_BADGE_VARIANT[profile.state?.toLowerCase()] || "outline"} className="text-sm">
                    {profile.state}
                  </Badge>
                </CardHeader>
                <CardContent>
                  {/* Profile details */}
                  <div className="mb-4 grid grid-cols-2 gap-3 text-sm">
                    <div><span className="text-neutral-400">Legal Name:</span> <span className="font-medium">{profile.legal_name || "\u2014"}</span></div>
                    <div><span className="text-neutral-400">Trade Name:</span> <span className="font-medium">{profile.trade_name || "\u2014"}</span></div>
                    <div><span className="text-neutral-400">Tax ID:</span> <span className="font-medium">{profile.tax_id || "\u2014"}</span></div>
                    <div><span className="text-neutral-400">Company Reg:</span> <span className="font-medium">{profile.company_registration_number || "\u2014"}</span></div>
                    <div><span className="text-neutral-400">Address:</span> <span className="font-medium">{profile.physical_address || "\u2014"}{profile.city ? `, ${profile.city}` : ""}</span></div>
                    <div><span className="text-neutral-400">Contact:</span> <span className="font-medium">{profile.contact_email || "\u2014"} / {profile.contact_phone || "\u2014"}</span></div>
                  </div>

                  {/* Verification flags */}
                  <div className="mb-4 flex flex-wrap gap-2">
                    <Badge variant={profile.tax_id_verified ? "success" : "outline"}>{profile.tax_id_verified ? "\u2713" : "\u2717"} Tax ID</Badge>
                    <Badge variant={profile.company_reg_verified ? "success" : "outline"}>{profile.company_reg_verified ? "\u2713" : "\u2717"} Company Reg</Badge>
                    <Badge variant={profile.address_verified ? "success" : "outline"}>{profile.address_verified ? "\u2713" : "\u2717"} Address</Badge>
                    <Badge variant={profile.eligible_for_billing ? "success" : "secondary"}>{profile.eligible_for_billing ? "Billing Eligible" : "Not Billing Eligible"}</Badge>
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div><span className="text-neutral-400">Created:</span> {formatDate(profile.created_at)}</div>
                    <div><span className="text-neutral-400">Verified:</span> {profile.verified_at ? formatDate(profile.verified_at) : "Not yet"}</div>
                    <div><span className="text-neutral-400">Pack Ref:</span> {profile.pack_ref || "\u2014"}</div>
                  </div>

                  {profile.rejection_reason && (
                    <div className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
                      Rejection reason: {profile.rejection_reason}
                    </div>
                  )}

                  {profile.review_notes && (
                    <div className="mt-2 rounded border border-blue-200 bg-blue-50 p-2 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300">
                      Review notes: {profile.review_notes}
                    </div>
                  )}

                  <Separator className="my-4" />

                  {/* Action buttons based on state */}
                  <div className="flex gap-2">
                    {(profile.state === "submitted" || profile.state === "under_review") && (
                      <Button size="sm" onClick={() => { setReviewTarget(profile); setReviewDecision("approve"); }}>
                        Review
                      </Button>
                    )}
                    {profile.state === "verified" && (
                      <Button size="sm" onClick={() => handleProfileAction("activate")}>
                        Activate
                      </Button>
                    )}
                    {profile.state === "active" && (
                      <Button size="sm" variant="destructive" onClick={() => handleProfileAction("suspend", "Admin suspension")}>
                        Suspend
                      </Button>
                    )}
                    {profile.state === "suspended" && (
                      <Button size="sm" onClick={() => handleProfileAction("reactivate", "Admin reactivation")}>
                        Reactivate
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Profile Metadata */}
              <Card>
                <CardHeader>
                  <CardTitle>Profile Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div><span className="text-neutral-400">Profile ID:</span> <span className="font-mono text-xs">{profile.profile_id}</span></div>
                    <div><span className="text-neutral-400">Reviewer:</span> <span className="font-mono text-xs">{profile.reviewer_id || "\u2014"}</span></div>
                    <div><span className="text-neutral-400">Last Updated:</span> {profile.updated_at ? formatDate(profile.updated_at) : "\u2014"}</div>
                    <div><span className="text-neutral-400">Customer Type:</span> {profile.customer_type}</div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}

      {/* ═══ Publish Pack Dialog ═══ */}
      <FormDialog
        open={showPublish}
        onClose={() => setShowPublish(false)}
        title="Publish Compliance Pack"
        description="Create a new versioned compliance pack for a region"
        onSubmit={handlePublish}
        submitLabel="Publish"
        loading={publishing}
        wide
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Region</Label>
            <Select value={publishData.region_code} onChange={(e) => setPublishData({ ...publishData, region_code: e.target.value })} required>
              <option value="">-- Select --</option>
              {REGIONS.map((r) => (
                <option key={r.code} value={r.code}>{r.code} — {r.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Display Name</Label>
            <Input value={publishData.display_name} onChange={(e) => setPublishData({ ...publishData, display_name: e.target.value })} placeholder="e.g. Kenya VAT Compliance v2" required />
          </div>
          <div>
            <Label>Effective Date</Label>
            <Input type="date" value={publishData.effective_date} onChange={(e) => setPublishData({ ...publishData, effective_date: e.target.value })} required />
          </div>
          <div>
            <Label>Law Reference</Label>
            <Input value={publishData.region_law_reference} onChange={(e) => setPublishData({ ...publishData, region_law_reference: e.target.value })} placeholder="e.g. Kenya VAT Act Cap 476" />
          </div>
        </div>

        <Separator />
        <p className="text-sm font-semibold">Tax Rule</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Tax Code</Label>
            <Input value={publishData.tax_code} onChange={(e) => setPublishData({ ...publishData, tax_code: e.target.value })} placeholder="VAT" />
          </div>
          <div>
            <Label>Tax Category</Label>
            <Select value={publishData.tax_category} onChange={(e) => setPublishData({ ...publishData, tax_category: e.target.value })}>
              <option value="STANDARD">Standard</option>
              <option value="ZERO_RATED">Zero Rated</option>
              <option value="EXEMPT">Exempt</option>
              <option value="REVERSE_CHARGE">Reverse Charge</option>
              <option value="REDUCED">Reduced</option>
              <option value="WITHHOLDING">Withholding</option>
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Rate (0-1)</Label>
            <Input type="number" step="0.01" min="0" max="1" value={publishData.tax_rate} onChange={(e) => setPublishData({ ...publishData, tax_rate: e.target.value })} placeholder="0.16" />
          </div>
          <div>
            <Label>Description</Label>
            <Input value={publishData.tax_description} onChange={(e) => setPublishData({ ...publishData, tax_description: e.target.value })} placeholder="Value Added Tax 16%" />
          </div>
        </div>

        <Separator />
        <p className="text-sm font-semibold">Receipt Requirements</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publishData.require_sequential_number} onChange={(e) => setPublishData({ ...publishData, require_sequential_number: e.target.checked })} />
            Sequential Number Required
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publishData.require_tax_number} onChange={(e) => setPublishData({ ...publishData, require_tax_number: e.target.checked })} />
            Tax Number on Receipt
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publishData.require_qr_code} onChange={(e) => setPublishData({ ...publishData, require_qr_code: e.target.checked })} />
            QR Code Required (e.g. KRA TIMS)
          </label>
        </div>

        <Separator />
        <p className="text-sm font-semibold">E-Invoicing</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publishData.e_invoicing_active} onChange={(e) => setPublishData({ ...publishData, e_invoicing_active: e.target.checked })} />
            E-Invoicing Mandate Active
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publishData.e_invoicing_device_required} onChange={(e) => setPublishData({ ...publishData, e_invoicing_device_required: e.target.checked })} />
            Device Registration Required
          </label>
        </div>
        {publishData.e_invoicing_active && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>System Name</Label>
              <Input value={publishData.e_invoicing_system} onChange={(e) => setPublishData({ ...publishData, e_invoicing_system: e.target.value })} placeholder="e.g. KRA eTIMS" />
            </div>
            <div>
              <Label>Regulatory Body</Label>
              <Input value={publishData.e_invoicing_regulatory_body} onChange={(e) => setPublishData({ ...publishData, e_invoicing_regulatory_body: e.target.value })} placeholder="e.g. Kenya Revenue Authority" />
            </div>
            <div>
              <Label>Transmission Mode</Label>
              <Select value={publishData.e_invoicing_transmission_mode} onChange={(e) => setPublishData({ ...publishData, e_invoicing_transmission_mode: e.target.value })}>
                <option value="REAL_TIME">Real Time</option>
                <option value="BATCH">Batch</option>
                <option value="NEAR_REAL_TIME">Near Real Time</option>
              </Select>
            </div>
            <div>
              <Label>Max Offline Hours</Label>
              <Input type="number" value={publishData.e_invoicing_max_offline_hours} onChange={(e) => setPublishData({ ...publishData, e_invoicing_max_offline_hours: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={publishData.e_invoicing_qr_required} onChange={(e) => setPublishData({ ...publishData, e_invoicing_qr_required: e.target.checked })} />
              QR Code Required
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={publishData.e_invoicing_signature_required} onChange={(e) => setPublishData({ ...publishData, e_invoicing_signature_required: e.target.checked })} />
              Digital Signature Required
            </label>
          </div>
        )}

        <Separator />
        <p className="text-sm font-semibold">Invoice Format Rules</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Document Language</Label>
            <Select value={publishData.invoice_document_language} onChange={(e) => setPublishData({ ...publishData, invoice_document_language: e.target.value })}>
              <option value="en">English</option>
              <option value="sw">Swahili</option>
              <option value="fr">French</option>
              <option value="ar">Arabic</option>
              <option value="pt">Portuguese</option>
            </Select>
          </div>
          <div>
            <Label>Date Format</Label>
            <Select value={publishData.invoice_date_format} onChange={(e) => setPublishData({ ...publishData, invoice_date_format: e.target.value })}>
              <option value="YYYY-MM-DD">YYYY-MM-DD (ISO)</option>
              <option value="DD/MM/YYYY">DD/MM/YYYY</option>
              <option value="MM/DD/YYYY">MM/DD/YYYY</option>
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publishData.invoice_tax_breakdown_required} onChange={(e) => setPublishData({ ...publishData, invoice_tax_breakdown_required: e.target.checked })} />
            Tax Breakdown Required on Invoice
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publishData.invoice_credit_note_ref_required} onChange={(e) => setPublishData({ ...publishData, invoice_credit_note_ref_required: e.target.checked })} />
            Credit Note Must Reference Invoice
          </label>
        </div>

        <Separator />
        <p className="text-sm font-semibold">Cross-Border Rules</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publishData.cross_border_reverse_charge} onChange={(e) => setPublishData({ ...publishData, cross_border_reverse_charge: e.target.checked })} />
            Reverse Charge on Imports
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publishData.cross_border_withholding} onChange={(e) => setPublishData({ ...publishData, cross_border_withholding: e.target.checked })} />
            Withholding on Foreign Services
          </label>
        </div>
        {(publishData.cross_border_reverse_charge || publishData.cross_border_withholding) && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Withholding Rate (0-1)</Label>
              <Input type="number" step="0.01" min="0" max="1" value={publishData.cross_border_withholding_rate} onChange={(e) => setPublishData({ ...publishData, cross_border_withholding_rate: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={publishData.cross_border_transfer_pricing} onChange={(e) => setPublishData({ ...publishData, cross_border_transfer_pricing: e.target.checked })} />
              Transfer Pricing Docs Required
            </label>
          </div>
        )}

        <Separator />
        <p className="text-sm font-semibold">Digital Signature</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={publishData.digital_signature_required} onChange={(e) => setPublishData({ ...publishData, digital_signature_required: e.target.checked })} />
            Require Digital Signature on Documents
          </label>
          {publishData.digital_signature_required && (
            <>
              <div>
                <Label>Signature Algorithm</Label>
                <Select value={publishData.digital_signature_algorithm} onChange={(e) => setPublishData({ ...publishData, digital_signature_algorithm: e.target.value })}>
                  <option value="RSA-SHA256">RSA-SHA256</option>
                  <option value="ECDSA-SHA256">ECDSA-SHA256</option>
                  <option value="ED25519">ED25519</option>
                </Select>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={publishData.digital_signature_timestamp} onChange={(e) => setPublishData({ ...publishData, digital_signature_timestamp: e.target.checked })} />
                Timestamp Required
              </label>
            </>
          )}
        </div>

        <Separator />
        <p className="text-sm font-semibold">Fiscal Governance</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Fiscal Year Start Month</Label>
            <Select value={publishData.fiscal_year_start_month} onChange={(e) => setPublishData({ ...publishData, fiscal_year_start_month: e.target.value })}>
              {["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].map((m, i) => (
                <option key={i + 1} value={String(i + 1)}>{m}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>VAT Return Frequency</Label>
            <Select value={publishData.vat_return_frequency} onChange={(e) => setPublishData({ ...publishData, vat_return_frequency: e.target.value })}>
              <option value="MONTHLY">Monthly</option>
              <option value="QUARTERLY">Quarterly</option>
              <option value="BIANNUAL">Bi-Annual</option>
              <option value="ANNUAL">Annual</option>
            </Select>
          </div>
        </div>
        <div>
          <Label>Law Reference URL</Label>
          <Input value={publishData.law_reference_url} onChange={(e) => setPublishData({ ...publishData, law_reference_url: e.target.value })} placeholder="https://..." />
        </div>

        <Separator />
        <p className="text-sm font-semibold">Data Retention</p>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label>Financial Records (years)</Label>
            <Input type="number" value={publishData.financial_records_years} onChange={(e) => setPublishData({ ...publishData, financial_records_years: e.target.value })} />
          </div>
          <div>
            <Label>Audit Log (years)</Label>
            <Input type="number" value={publishData.audit_log_years} onChange={(e) => setPublishData({ ...publishData, audit_log_years: e.target.value })} />
          </div>
          <div>
            <Label>Personal Data (years)</Label>
            <Input type="number" value={publishData.personal_data_years} onChange={(e) => setPublishData({ ...publishData, personal_data_years: e.target.value })} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Consent Records (years)</Label>
            <Input type="number" value={publishData.consent_records_years} onChange={(e) => setPublishData({ ...publishData, consent_records_years: e.target.value })} />
          </div>
          <div>
            <Label>Tax Records (years)</Label>
            <Input type="number" value={publishData.tax_records_years} onChange={(e) => setPublishData({ ...publishData, tax_records_years: e.target.value })} />
          </div>
        </div>

        <div>
          <Label>Change Summary</Label>
          <Textarea value={publishData.change_summary} onChange={(e) => setPublishData({ ...publishData, change_summary: e.target.value })} placeholder="Describe what changed in this version" />
        </div>
      </FormDialog>

      {/* ═══ Add Country Policy Dialog ═══ */}
      <FormDialog
        open={showAddPolicy}
        onClose={() => setShowAddPolicy(false)}
        title="Country Compliance Policy"
        description="Set compliance requirements for a country"
        onSubmit={handleSavePolicy}
        submitLabel="Save Policy"
        loading={savingPolicy}
        wide
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Country Code</Label>
            <Select value={policyData.country_code} onChange={(e) => {
              const region = REGIONS.find((r) => r.code === e.target.value);
              setPolicyData({ ...policyData, country_code: e.target.value, country_name: region?.name || "" });
            }} required>
              <option value="">-- Select --</option>
              {REGIONS.map((r) => (
                <option key={r.code} value={r.code}>{r.code} — {r.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Country Name</Label>
            <Input value={policyData.country_name} onChange={(e) => setPolicyData({ ...policyData, country_name: e.target.value })} required />
          </div>
        </div>

        <Separator />
        <p className="text-sm font-semibold">Business Model</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.b2b_allowed} onChange={(e) => setPolicyData({ ...policyData, b2b_allowed: e.target.checked })} />
            B2B Allowed
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.b2c_allowed} onChange={(e) => setPolicyData({ ...policyData, b2c_allowed: e.target.checked })} />
            B2C Allowed
          </label>
        </div>

        <Separator />
        <p className="text-sm font-semibold">Onboarding Requirements</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.vat_registration_required} onChange={(e) => setPolicyData({ ...policyData, vat_registration_required: e.target.checked })} />
            VAT Registration Required
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.company_registration_required} onChange={(e) => setPolicyData({ ...policyData, company_registration_required: e.target.checked })} />
            Company Registration Required
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.requires_tax_id} onChange={(e) => setPolicyData({ ...policyData, requires_tax_id: e.target.checked })} />
            Tax ID Required
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.requires_physical_address} onChange={(e) => setPolicyData({ ...policyData, requires_physical_address: e.target.checked })} />
            Physical Address Required
          </label>
        </div>

        <Separator />
        <p className="text-sm font-semibold">E-Invoicing</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.e_invoicing_mandatory} onChange={(e) => setPolicyData({ ...policyData, e_invoicing_mandatory: e.target.checked })} />
            E-Invoicing Mandatory
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.fiscal_device_required} onChange={(e) => setPolicyData({ ...policyData, fiscal_device_required: e.target.checked })} />
            Fiscal Device Required
          </label>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>E-Invoicing System</Label>
            <Select value={policyData.e_invoicing_system} onChange={(e) => setPolicyData({ ...policyData, e_invoicing_system: e.target.value })}>
              <option value="">None</option>
              <option value="KRA_ETIMS">KRA eTIMS (Kenya)</option>
              <option value="TRA_EFDMS">TRA EFDMS (Tanzania)</option>
              <option value="URA_EFRIS">URA EFRIS (Uganda)</option>
              <option value="FIRS_MBS">FIRS MBS (Nigeria)</option>
              <option value="RRA_EBM">RRA EBM (Rwanda)</option>
              <option value="SARS_EFILING">SARS eFiling (South Africa)</option>
            </Select>
          </div>
          <div>
            <Label>Receipt QR Code</Label>
            <label className="mt-2 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={policyData.receipt_qr_code_required} onChange={(e) => setPolicyData({ ...policyData, receipt_qr_code_required: e.target.checked })} />
              QR Code Required on Receipts
            </label>
          </div>
        </div>

        <Separator />
        <p className="text-sm font-semibold">Privacy & Data Governance</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Privacy Regime</Label>
            <Select value={policyData.privacy_regime} onChange={(e) => setPolicyData({ ...policyData, privacy_regime: e.target.value })}>
              <option value="NONE">None</option>
              <option value="KENYA_DPA">Kenya DPA 2019</option>
              <option value="GDPR">GDPR (EU)</option>
              <option value="POPIA">POPIA (South Africa)</option>
              <option value="NIGERIA_NDPR">Nigeria NDPR</option>
              <option value="TANZANIA_EDPA">Tanzania EDPA</option>
              <option value="UGANDA_DPP">Uganda DPP</option>
              <option value="RWANDA_DPL">Rwanda DPL</option>
              <option value="AU_CONVENTION">AU Convention (Malabo)</option>
            </Select>
          </div>
          <div>
            <Label>Privacy Regulator</Label>
            <Input value={policyData.privacy_regulator} onChange={(e) => setPolicyData({ ...policyData, privacy_regulator: e.target.value })} placeholder="e.g. ODPC (Kenya)" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Breach Notification (hours)</Label>
            <Input type="number" value={policyData.breach_notification_hours} onChange={(e) => setPolicyData({ ...policyData, breach_notification_hours: parseInt(e.target.value) || 72 })} />
          </div>
          <div>
            <Label>Data Subject Access (days)</Label>
            <Input type="number" value={policyData.data_subject_access_days} onChange={(e) => setPolicyData({ ...policyData, data_subject_access_days: parseInt(e.target.value) || 30 })} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.consent_required_for_processing} onChange={(e) => setPolicyData({ ...policyData, consent_required_for_processing: e.target.checked })} />
            Consent for Processing
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.consent_required_for_marketing} onChange={(e) => setPolicyData({ ...policyData, consent_required_for_marketing: e.target.checked })} />
            Consent for Marketing
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.right_to_erasure} onChange={(e) => setPolicyData({ ...policyData, right_to_erasure: e.target.checked })} />
            Right to Erasure
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.data_protection_officer_required} onChange={(e) => setPolicyData({ ...policyData, data_protection_officer_required: e.target.checked })} />
            DPO Required
          </label>
        </div>

        <Separator />
        <p className="text-sm font-semibold">Tax Configuration</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.withholding_tax_applicable} onChange={(e) => setPolicyData({ ...policyData, withholding_tax_applicable: e.target.checked })} />
            Withholding Tax Applicable
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.digital_services_tax} onChange={(e) => setPolicyData({ ...policyData, digital_services_tax: e.target.checked })} />
            Digital Services Tax
          </label>
        </div>

        <Separator />
        <p className="text-sm font-semibold">Fiscal & Reporting</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Document Language</Label>
            <Select value={policyData.document_language} onChange={(e) => setPolicyData({ ...policyData, document_language: e.target.value })}>
              <option value="en">English</option>
              <option value="sw">Swahili</option>
              <option value="fr">French</option>
              <option value="ar">Arabic</option>
              <option value="pt">Portuguese</option>
            </Select>
          </div>
          <div>
            <Label>Fiscal Year Start Month</Label>
            <Select value={String(policyData.fiscal_year_start_month)} onChange={(e) => setPolicyData({ ...policyData, fiscal_year_start_month: parseInt(e.target.value) })}>
              {["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].map((m, i) => (
                <option key={i + 1} value={i + 1}>{m} ({i + 1})</option>
              ))}
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>VAT Return Frequency</Label>
            <Select value={policyData.vat_return_frequency} onChange={(e) => setPolicyData({ ...policyData, vat_return_frequency: e.target.value })}>
              <option value="MONTHLY">Monthly</option>
              <option value="QUARTERLY">Quarterly</option>
              <option value="BIANNUAL">Bi-Annual</option>
              <option value="ANNUAL">Annual</option>
            </Select>
          </div>
          <div>
            <Label>Reporting Currency</Label>
            <Input value={policyData.reporting_currency} onChange={(e) => setPolicyData({ ...policyData, reporting_currency: e.target.value.toUpperCase() })} placeholder="e.g. KES" maxLength={3} className="uppercase" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.statutory_audit_required} onChange={(e) => setPolicyData({ ...policyData, statutory_audit_required: e.target.checked })} />
            Statutory Audit Required
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.auto_compliance_checks} onChange={(e) => setPolicyData({ ...policyData, auto_compliance_checks: e.target.checked })} />
            Auto Compliance Checks
          </label>
        </div>

        <Separator />
        <p className="text-sm font-semibold">Trial & Review</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Default Trial Days</Label>
            <Input type="number" value={policyData.default_trial_days} onChange={(e) => setPolicyData({ ...policyData, default_trial_days: parseInt(e.target.value) || 0 })} />
          </div>
          <div>
            <Label>Grace Period Days</Label>
            <Input type="number" value={policyData.grace_period_days} onChange={(e) => setPolicyData({ ...policyData, grace_period_days: parseInt(e.target.value) || 0 })} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Escalation Contact</Label>
            <Input value={policyData.escalation_contact} onChange={(e) => setPolicyData({ ...policyData, escalation_contact: e.target.value })} placeholder="compliance@bos.africa" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.manual_review_required} onChange={(e) => setPolicyData({ ...policyData, manual_review_required: e.target.checked })} />
            Manual Review Required
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.active} onChange={(e) => setPolicyData({ ...policyData, active: e.target.checked })} />
            Active
          </label>
        </div>
      </FormDialog>

      {/* ═══ Review Profile Dialog ═══ */}
      <FormDialog
        open={!!reviewTarget}
        onClose={() => setReviewTarget(null)}
        title="Review Compliance Profile"
        description={`Review ${reviewTarget?.legal_name || ""} (${reviewTarget?.country_code})`}
        onSubmit={handleReview}
        submitLabel={reviewDecision === "approve" ? "Approve" : "Reject"}
        loading={reviewing}
      >
        <div>
          <Label>Decision</Label>
          <Select value={reviewDecision} onChange={(e) => setReviewDecision(e.target.value as "approve" | "reject")}>
            <option value="approve">Approve</option>
            <option value="reject">Reject</option>
          </Select>
        </div>
        <div>
          <Label>Reason / Notes</Label>
          <Textarea
            value={reviewReason}
            onChange={(e) => setReviewReason(e.target.value)}
            placeholder={reviewDecision === "approve" ? "Verification notes (optional)" : "Reason for rejection (required)"}
            required={reviewDecision === "reject"}
          />
        </div>
      </FormDialog>

      {toast && (
        <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />
      )}
    </div>
  );
}
