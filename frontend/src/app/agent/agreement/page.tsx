"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle, Badge } from "@/components/ui";
import { getMyAgreement } from "@/lib/api/agents";
import { FileSignature, Calendar, MapPin, DollarSign, Users } from "lucide-react";

export default function AgentAgreementPage() {
  const agreement = useQuery({ queryKey: ["agent", "agreement"], queryFn: getMyAgreement });
  const a = agreement.data?.data ?? {};

  return (
    <div>
      <PageHeader
        title="My Agreement"
        description="Your agent agreement terms and status"
      />

      {/* Agreement Status */}
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
            <InfoRow label="Commission Model" value="Volume-based (tiered)" />
            <InfoRow label="Current Rate" value={a.commission_rate ? `${a.commission_rate}%` : "—"} />
            <InfoRow label="Regional Override" value={a.regional_override_pct ? `+${a.regional_override_pct}%` : "N/A"} />
            <InfoRow label="Residual Rate" value={a.residual_rate_pct ? `${a.residual_rate_pct}%` : "—"} />
            <InfoRow label="First-Year Bonus" value={a.first_year_bonus_pct ? `+${a.first_year_bonus_pct}%` : "—"} />
            <div className="mt-3 rounded-md bg-bos-silver-light p-3 text-xs text-bos-silver-dark dark:bg-neutral-900">
              <p className="font-semibold">Commission Rules:</p>
              <ul className="mt-1 list-inside list-disc space-y-1">
                <li>Commission paid only after platform collects from tenant</li>
                <li>First onboarding/training for new tenants is FREE</li>
                <li>Regional override applies to all tenants in your territory</li>
                <li>Residual commission continues after tenant transfer</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Territory & Requirements */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Territory & Requirements</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <InfoRow label="Territory" value={a.territory ?? "Global (no territory)"} />
            <InfoRow label="Office Address" value={a.office_address ?? "N/A (remote)"} />
            <InfoRow label="Country" value={a.country ?? "—"} />

            <div className="mt-3 rounded-md bg-bos-silver-light p-3 text-xs text-bos-silver-dark dark:bg-neutral-900">
              <p className="font-semibold">Probation Requirements (90 days):</p>
              <ul className="mt-1 list-inside list-disc space-y-1">
                <li>Minimum 5 onboarded tenants</li>
                <li>Complete all required training modules</li>
                <li>Maintain L1 support response SLA</li>
              </ul>
            </div>
          </CardContent>
        </Card>

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
            <InfoRow label="Agreement Start" value={a.start_date ?? "—"} />
            <InfoRow label="Probation Ends" value={a.probation_end_date ?? "—"} />
            <InfoRow label="Agreement Expires" value={a.end_date ?? "Indefinite"} />
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
    <div className="flex items-center justify-between">
      <span className="text-bos-silver-dark">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
