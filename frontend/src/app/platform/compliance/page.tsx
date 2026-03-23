"use client";

import { useEffect, useState } from "react";
import { PlatformShell } from "@/components/layout/platform-shell";
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
  display_name: string;
  required_documents: string[];
  required_fields: string[];
  review_required: boolean;
  auto_activate: boolean;
}

interface ComplianceProfileType {
  profile_id: string;
  business_id: string;
  country_code: string;
  status: string;
  submitted_data: Record<string, string>;
  submitted_at: string | null;
  submitted_by: string;
  activated_at: string | null;
  suspended_at: string | null;
  suspended_reason: string;
  decisions: Array<{
    decision: string;
    reviewer_id: string;
    reason: string;
    decided_at: string;
  }>;
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
  const [packs, setPacks] = useState<CompliancePack[]>([]);
  const [packsLoading, setPacksLoading] = useState(false);
  const [packRegion, setPackRegion] = useState("");
  const [showPublish, setShowPublish] = useState(false);
  const [publishData, setPublishData] = useState({
    region_code: "", display_name: "", effective_date: "", change_summary: "",
    tax_code: "", tax_rate: "", tax_description: "",
    require_sequential_number: true, require_tax_number: true,
    require_qr_code: false, number_prefix_format: "RCP-{YYYY}-{NNNNN}",
    financial_records_years: "7", audit_log_years: "7", personal_data_years: "5",
    region_law_reference: "",
    required_invoice_fields: "business_name,tax_id,date,invoice_number,line_items,total",
    optional_invoice_fields: "customer_tax_id,po_number,delivery_date",
  });
  const [publishing, setPublishing] = useState(false);

  // ── Policies tab state ──
  const [policies, setPolicies] = useState<CountryPolicyType[]>([]);
  const [policiesLoading, setPoliciesLoading] = useState(false);
  const [showAddPolicy, setShowAddPolicy] = useState(false);
  const [policyData, setPolicyData] = useState({
    country_code: "", display_name: "",
    required_documents: "business_registration,tax_pin",
    required_fields: "business_name,physical_address,tax_number",
    review_required: true, auto_activate: false,
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

  // ── Load packs ──
  async function loadPacks() {
    setPacksLoading(true);
    try {
      const res = await listCompliancePacks(packRegion || undefined);
      setPacks(res.packs || []);
    } catch {
      setToast({ message: "Failed to load compliance packs", variant: "error" });
    } finally {
      setPacksLoading(false);
    }
  }

  // ── Load policies ──
  async function loadPolicies() {
    setPoliciesLoading(true);
    try {
      const res = await listCountryPolicies();
      setPolicies(res.policies || []);
    } catch {
      setToast({ message: "Failed to load country policies", variant: "error" });
    } finally {
      setPoliciesLoading(false);
    }
  }

  useEffect(() => {
    if (tab === "packs") loadPacks();
    if (tab === "policies") loadPolicies();
  }, [tab]);

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
        }] : [],
        receipt_requirements: {
          require_sequential_number: publishData.require_sequential_number,
          require_tax_number: publishData.require_tax_number,
          require_qr_code: publishData.require_qr_code,
          number_prefix_format: publishData.number_prefix_format,
        },
        data_retention: {
          financial_records_years: parseInt(publishData.financial_records_years) || 7,
          audit_log_years: parseInt(publishData.audit_log_years) || 7,
          personal_data_years: parseInt(publishData.personal_data_years) || 5,
          region_law_reference: publishData.region_law_reference,
        },
        required_invoice_fields: publishData.required_invoice_fields.split(",").map((s) => s.trim()).filter(Boolean),
        optional_invoice_fields: publishData.optional_invoice_fields.split(",").map((s) => s.trim()).filter(Boolean),
        change_summary: publishData.change_summary,
      });
      setToast({ message: "Compliance pack published", variant: "success" });
      setShowPublish(false);
      loadPacks();
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
        display_name: policyData.display_name,
        required_documents: policyData.required_documents.split(",").map((s) => s.trim()).filter(Boolean),
        required_fields: policyData.required_fields.split(",").map((s) => s.trim()).filter(Boolean),
        review_required: policyData.review_required,
        auto_activate: policyData.auto_activate,
      });
      setToast({ message: `Policy for ${policyData.country_code} saved`, variant: "success" });
      setShowAddPolicy(false);
      loadPolicies();
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
    <PlatformShell>
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
            <Button size="sm" variant="outline" onClick={loadPacks}>Refresh</Button>
            <Button size="sm" onClick={() => setShowPublish(true)}>Publish New Pack</Button>
          </div>

          <Card>
            <CardContent className="pt-6">
              {packsLoading ? (
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
            <Button size="sm" variant="outline" onClick={loadPolicies}>Refresh</Button>
          </div>

          <Card>
            <CardContent className="pt-6">
              {policiesLoading ? (
                <p className="text-sm text-neutral-400">Loading...</p>
              ) : policies.length === 0 ? (
                <EmptyState title="No country policies" description="Configure compliance policies per country" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Country</TableHead>
                      <TableHead>Required Documents</TableHead>
                      <TableHead>Required Fields</TableHead>
                      <TableHead>Review</TableHead>
                      <TableHead>Auto-Activate</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {policies.map((p) => (
                      <TableRow key={p.country_code}>
                        <TableCell className="font-medium">{p.country_code} — {p.display_name}</TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {(p.required_documents || []).map((d) => (
                              <Badge key={d} variant="outline" className="text-xs">{d}</Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {(p.required_fields || []).map((f) => (
                              <Badge key={f} variant="secondary" className="text-xs">{f}</Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>{p.review_required ? <Badge variant="warning">Manual</Badge> : <Badge variant="success">Auto</Badge>}</TableCell>
                        <TableCell>{p.auto_activate ? "Yes" : "No"}</TableCell>
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
                    <CardTitle>{profile.submitted_data?.business_name || profile.business_id}</CardTitle>
                    <CardDescription>
                      {profile.country_code} | Business: {profile.business_id.slice(0, 12)}...
                    </CardDescription>
                  </div>
                  <Badge variant={STATE_BADGE_VARIANT[profile.status?.toLowerCase()] || "outline"} className="text-sm">
                    {profile.status}
                  </Badge>
                </CardHeader>
                <CardContent>
                  {/* Submitted data fields */}
                  <div className="mb-4 grid grid-cols-2 gap-3 text-sm">
                    {Object.entries(profile.submitted_data || {}).map(([key, val]) => (
                      <div key={key}>
                        <span className="text-neutral-400">{key.replace(/_/g, " ")}:</span>{" "}
                        <span className="font-medium">{val}</span>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div><span className="text-neutral-400">Submitted:</span> {formatDate(profile.submitted_at)}</div>
                    <div><span className="text-neutral-400">Activated:</span> {profile.activated_at ? formatDate(profile.activated_at) : "Not yet"}</div>
                    <div><span className="text-neutral-400">Submitted by:</span> {profile.submitted_by?.slice(0, 12) || "\u2014"}</div>
                  </div>

                  {profile.suspended_reason && (
                    <div className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
                      Suspension reason: {profile.suspended_reason}
                    </div>
                  )}

                  <Separator className="my-4" />

                  {/* Action buttons based on status */}
                  <div className="flex gap-2">
                    {profile.status === "SUBMITTED" && (
                      <Button size="sm" onClick={() => { setReviewTarget(profile); setReviewDecision("approve"); }}>
                        Review
                      </Button>
                    )}
                    {profile.status === "APPROVED" && (
                      <Button size="sm" onClick={() => handleProfileAction("activate")}>
                        Activate
                      </Button>
                    )}
                    {profile.status === "ACTIVE" && (
                      <Button size="sm" variant="destructive" onClick={() => handleProfileAction("suspend", "Admin suspension")}>
                        Suspend
                      </Button>
                    )}
                    {profile.status === "SUSPENDED" && (
                      <Button size="sm" onClick={() => handleProfileAction("reactivate", "Admin reactivation")}>
                        Reactivate
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Decisions Audit Log */}
              <Card>
                <CardHeader>
                  <CardTitle>Review Decisions (Audit Log)</CardTitle>
                </CardHeader>
                <CardContent>
                  {(!profile.decisions || profile.decisions.length === 0) ? (
                    <p className="text-sm text-neutral-400">No review decisions recorded</p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Decision</TableHead>
                          <TableHead>Reviewer</TableHead>
                          <TableHead>Reason</TableHead>
                          <TableHead>Date</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {profile.decisions.map((d, i) => (
                          <TableRow key={i}>
                            <TableCell>
                              <Badge variant={d.decision === "approve" ? "success" : "destructive"}>
                                {d.decision.toUpperCase()}
                              </Badge>
                            </TableCell>
                            <TableCell className="font-mono text-xs">{d.reviewer_id?.slice(0, 12)}...</TableCell>
                            <TableCell className="max-w-[200px] truncate text-sm">{d.reason || "\u2014"}</TableCell>
                            <TableCell className="text-sm">{formatDate(d.decided_at)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
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
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label>Tax Code</Label>
            <Input value={publishData.tax_code} onChange={(e) => setPublishData({ ...publishData, tax_code: e.target.value })} placeholder="VAT" />
          </div>
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
              setPolicyData({ ...policyData, country_code: e.target.value, display_name: region ? `${region.name} Compliance Policy` : "" });
            }} required>
              <option value="">-- Select --</option>
              {REGIONS.map((r) => (
                <option key={r.code} value={r.code}>{r.code} — {r.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Display Name</Label>
            <Input value={policyData.display_name} onChange={(e) => setPolicyData({ ...policyData, display_name: e.target.value })} required />
          </div>
        </div>

        <div>
          <Label>Required Documents (comma-separated)</Label>
          <Input
            value={policyData.required_documents}
            onChange={(e) => setPolicyData({ ...policyData, required_documents: e.target.value })}
            placeholder="business_registration, tax_pin, id_copy"
          />
          <p className="mt-1 text-xs text-neutral-400">Document types the tenant must provide during onboarding</p>
        </div>

        <div>
          <Label>Required Fields (comma-separated)</Label>
          <Input
            value={policyData.required_fields}
            onChange={(e) => setPolicyData({ ...policyData, required_fields: e.target.value })}
            placeholder="business_name, physical_address, tax_number"
          />
          <p className="mt-1 text-xs text-neutral-400">Data fields the tenant must submit in their compliance profile</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.review_required} onChange={(e) => setPolicyData({ ...policyData, review_required: e.target.checked })} />
            Manual Review Required
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={policyData.auto_activate} onChange={(e) => setPolicyData({ ...policyData, auto_activate: e.target.checked })} />
            Auto-Activate (skip review)
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
    </PlatformShell>
  );
}
