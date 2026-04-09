"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle, Badge } from "@/components/ui";
import { getMyAgreement, getAgentContract } from "@/lib/api/agents";
import { useAgentAuthStore } from "@/stores/agent-auth-store";
import {
  FileSignature, Calendar, MapPin, DollarSign, Users, ShieldCheck,
  AlertTriangle, CheckCircle, Clock, Lock,
} from "lucide-react";

const HARDCODED_TERM_LABELS: Record<string, string> = {
  remittance_deadline_days: "Remittance Deadline",
  tenant_continuity_guaranteed: "Tenant Continuity Guarantee",
  region_exclusivity: "Region Exclusivity",
  platform_audit_right: "Platform Audit Right",
  compliance_ownership_by_rla: "Regional Compliance Ownership",
  sub_agent_requires_platform_approval: "Sub-Agent Requires Platform Approval",
  price_bound_enforcement: "Price Bound Enforcement",
  commission_on_all_regional_tenants: "Commission on All Regional Tenants",
  platform_can_terminate_with_notice_days: "Termination Notice (days)",
  dispute_resolution: "Dispute Resolution",
  governing_law: "Governing Law",
};

function formatTermValue(key: string, value: unknown): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (key === "remittance_deadline_days" || key === "platform_can_terminate_with_notice_days") {
    return `${value} days`;
  }
  return String(value);
}

function getContractStatusConfig(status: string | null) {
  switch (status) {
    case "ACTIVE": return { label: "Active", color: "bg-green-50 text-green-700", icon: CheckCircle };
    case "DRAFT": return { label: "Awaiting Signature", color: "bg-amber-50 text-amber-700", icon: Clock };
    case "SUSPENDED": return { label: "Suspended", color: "bg-red-50 text-red-700", icon: AlertTriangle };
    case "TERMINATED_REVERSIBLE": return { label: "Terminated (Reversible)", color: "bg-orange-50 text-orange-700", icon: AlertTriangle };
    case "TERMINATED_PERMANENT": return { label: "Terminated (Permanent)", color: "bg-red-100 text-red-800", icon: Lock };
    case "REDUCED_COMMISSION": return { label: "Reduced Commission Terms", color: "bg-amber-100 text-amber-800", icon: AlertTriangle };
    case "EXPIRED": return { label: "Expired", color: "bg-neutral-100 text-neutral-500", icon: Clock };
    default: return { label: "No Contract", color: "bg-neutral-100 text-neutral-400", icon: FileSignature };
  }
}

export default function AgentAgreementPage() {
  const { agentId } = useAgentAuthStore();

  const agreement = useQuery({ queryKey: ["agent", "agreement"], queryFn: getMyAgreement });
  const contractQuery = useQuery({
    queryKey: ["agent", "contract", agentId],
    queryFn: () => getAgentContract(agentId),
    enabled: !!agentId,
  });

  const a = agreement.data?.data ?? {};
  const contract = contractQuery.data?.data ?? null;

  const contractCfg = getContractStatusConfig(contract?.status ?? null);
  const StatusIcon = contractCfg.icon;

  const generatedTerms = contract?.generated_terms ?? {};
  const hardcodedTerms = contract?.hardcoded_terms ?? {};

  return (
    <div>
      <PageHeader
        title="My Agreement"
        description="Your franchise contract terms, commission structure, and compliance obligations."
      />

      {/* Contract status banner */}
      {contract && (
        <Card className={`mb-6 border ${
          contract.status === "ACTIVE" ? "border-green-200 bg-green-50/40" :
          contract.status === "DRAFT" ? "border-amber-200 bg-amber-50/40" :
          "border-red-200 bg-red-50/40"
        }`}>
          <CardContent className="pt-5">
            <div className="flex items-start gap-3">
              <StatusIcon className={`mt-0.5 h-5 w-5 ${
                contract.status === "ACTIVE" ? "text-green-600" :
                contract.status === "DRAFT" ? "text-amber-600" : "text-red-600"
              }`} />
              <div>
                <p className="font-semibold text-sm">
                  Franchise Contract — <span className={`rounded px-1.5 py-0.5 text-xs font-bold uppercase ${contractCfg.color}`}>{contractCfg.label}</span>
                </p>
                <div className="mt-2 grid grid-cols-2 gap-x-8 gap-y-1 text-xs text-neutral-600 dark:text-neutral-400 sm:grid-cols-4">
                  <span>Region: <strong>{contract.region_code}</strong></span>
                  <span>Version: <strong>v{contract.version}</strong></span>
                  {contract.generated_at && <span>Issued: <strong>{new Date(contract.generated_at).toLocaleDateString()}</strong></span>}
                  {contract.signed_at && <span>Signed: <strong>{new Date(contract.signed_at).toLocaleDateString()}</strong></span>}
                  {contract.expires_at && <span>Expires: <strong>{new Date(contract.expires_at).toLocaleDateString()}</strong></span>}
                  {contract.signed_by_name && <span>Signed by: <strong>{contract.signed_by_name}</strong></span>}
                </div>

                {/* Reduced-commission term info */}
                {contract.status === "REDUCED_COMMISSION" && (
                  <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
                    <strong>Reduced Commission Period:</strong>{" "}
                    {contract.reduced_commission_rate && `${(parseFloat(contract.reduced_commission_rate) * 100).toFixed(1)}% rate`}
                    {contract.reduced_commission_term_months && ` for ${contract.reduced_commission_term_months} months`}
                    {contract.reduced_commission_expires_at && ` — ends ${new Date(contract.reduced_commission_expires_at).toLocaleDateString()}`}
                  </div>
                )}

                {/* Termination info */}
                {contract.termination_reason && (
                  <div className="mt-2 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-800">
                    <strong>Termination Reason:</strong> {contract.termination_reason}
                  </div>
                )}

                {/* Draft — awaiting signature */}
                {contract.status === "DRAFT" && (
                  <p className="mt-2 text-xs text-amber-700 font-medium">
                    Contract has been generated. Please review all terms below and contact your Platform Admin to formally sign.
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agreement overview (legacy / fallback) */}
      <Card className="mb-6 border-bos-purple/20">
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileSignature className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Agreement Overview</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-xs text-bos-silver-dark">Agent Type</p>
              <Badge variant="outline" className="mt-1">{a.agent_type ?? "—"}</Badge>
            </div>
            <div>
              <p className="text-xs text-bos-silver-dark">Status</p>
              <div className="mt-1"><StatusBadge status={a.status ?? "UNKNOWN"} /></div>
            </div>
            <div>
              <p className="text-xs text-bos-silver-dark">Start Date</p>
              <p className="text-sm font-medium">{a.start_date ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs text-bos-silver-dark">Duration</p>
              <p className="text-sm font-medium">{a.duration_months ? `${a.duration_months} months` : "—"}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Commission Terms */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Commission Terms</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {contract?.status === "REDUCED_COMMISSION" && contract.reduced_commission_rate ? (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900 font-semibold">
                Currently on Reduced Commission Rate: {(parseFloat(contract.reduced_commission_rate) * 100).toFixed(1)}%
              </div>
            ) : null}
            <InfoRow label="Commission Rate" value={
              generatedTerms.commission_rate
                ? `${(generatedTerms.commission_rate * 100).toFixed(0)}%`
                : a.commission_rate ? `${a.commission_rate}%` : "—"
            } />
            <InfoRow label="Max Platform Discount" value={
              generatedTerms.max_platform_discount_pct
                ? `${generatedTerms.max_platform_discount_pct}%`
                : "—"
            } />
            <InfoRow label="Max Trial Days" value={
              generatedTerms.max_trial_days ? `${generatedTerms.max_trial_days} days` : "—"
            } />
            <InfoRow label="Contract Duration" value={
              generatedTerms.contract_duration_months
                ? `${generatedTerms.contract_duration_months} months`
                : a.duration_months ? `${a.duration_months} months` : "—"
            } />
            {generatedTerms.performance_targets && (
              <>
                <InfoRow label="Monthly Tenant Target" value={String(generatedTerms.performance_targets.monthly_tenant_target ?? 0)} />
                <InfoRow label="Monthly Revenue Target" value={String(generatedTerms.performance_targets.monthly_revenue_target ?? 0)} />
              </>
            )}
            <div className="mt-3 rounded-md bg-bos-silver-light p-3 text-xs text-bos-silver-dark dark:bg-neutral-900">
              <p className="font-semibold">Commission Scope:</p>
              <ul className="mt-1 list-inside list-disc space-y-1">
                <li>Earned on <strong>ALL tenants within your region</strong> — not just ones you onboarded</li>
                <li>Regional compliance responsibility is the basis for regional commission</li>
                <li>Commission paid only after platform collects from tenant</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Territory & Requirements */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Territory & Region</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <InfoRow label="Region Code" value={contract?.region_code ?? a.territory ?? "—"} />
            <InfoRow label="Exclusivity" value="One RLA per region — exclusive licence" />
            <InfoRow label="Office Address" value={a.office_address ?? "N/A"} />

            <div className="mt-3 rounded-md bg-bos-silver-light p-3 text-xs text-bos-silver-dark dark:bg-neutral-900">
              <p className="font-semibold">Regional Compliance Obligations:</p>
              <ul className="mt-1 list-inside list-disc space-y-1">
                <li>File all local tax returns on time</li>
                <li>Maintain e-invoicing compliance</li>
                <li>Data privacy regulations for your region</li>
                <li>Remit platform share within 5 days of collection</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Hardcoded Platform Terms */}
        {Object.keys(hardcodedTerms).length > 0 && (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-bos-purple" />
                <CardTitle className="text-base">Platform Terms (Non-Negotiable)</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p className="text-xs text-bos-silver-dark mb-3">
                These terms are set by the Platform and cannot be changed under any circumstances.
              </p>
              {Object.entries(hardcodedTerms).map(([key, value]) => (
                <InfoRow
                  key={key}
                  label={HARDCODED_TERM_LABELS[key] ?? key}
                  value={formatTermValue(key, value)}
                />
              ))}
            </CardContent>
          </Card>
        )}

        {/* Performance */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Performance Summary</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <InfoRow label="Total Tenants" value={String(a.total_tenants ?? 0)} />
            <InfoRow label="Active Tenants" value={String(a.active_tenants ?? 0)} />
            <InfoRow label="Trial Tenants" value={String(a.trial_tenants ?? 0)} />
            <InfoRow label="Lifetime Commission" value={a.lifetime_commission ?? "—"} />
            <InfoRow label="Total Payouts" value={a.total_payouts ?? "—"} />
          </CardContent>
        </Card>

        {/* Key Dates */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Key Dates</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <InfoRow label="Contract Generated" value={contract?.generated_at ? new Date(contract.generated_at).toLocaleDateString() : (a.start_date ?? "—")} />
            <InfoRow label="Contract Signed" value={contract?.signed_at ? new Date(contract.signed_at).toLocaleDateString() : "—"} />
            <InfoRow label="Contract Expires" value={contract?.expires_at ? new Date(contract.expires_at).toLocaleDateString() : (a.end_date ?? "Indefinite")} />
            <InfoRow label="Last Payout" value={a.last_payout_date ?? "—"} />
            <InfoRow label="Next Review" value={a.next_review_date ?? "—"} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-bos-silver-dark shrink-0">{label}</span>
      <span className="font-medium text-right">{value}</span>
    </div>
  );
}
