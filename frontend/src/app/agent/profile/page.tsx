"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  Card, CardContent, CardHeader, CardTitle, Badge,
} from "@/components/ui";
import { getMyAgreement } from "@/lib/api/agents";
import {
  Building2, Shield, Scale, FileText, MapPin, Phone, Mail,
  Calendar, Percent, Users, Award, CheckCircle,
} from "lucide-react";

export default function ProfilePage() {
  const agreementQuery = useQuery({
    queryKey: ["agent", "agreement"],
    queryFn: getMyAgreement,
  });

  const agreement = agreementQuery.data?.data ?? {};

  const profile = {
    agent_name: agreement.agent_name || "—",
    agent_type: agreement.agent_type || "REGION_LICENSE_AGENT",
    status: agreement.status || "ACTIVE",
    territory: agreement.territory || "—",
    license_number: agreement.license_number || "—",
    market_share_pct: agreement.market_share_pct ?? "—",
    commission_rate: agreement.commission_rate ?? "—",
    max_platform_discount_pct: agreement.max_platform_discount_pct ?? "—",
    max_trial_days: agreement.max_trial_days ?? "—",
    contact_person: agreement.contact_person || "—",
    contact_email: agreement.contact_email || "—",
    contact_phone: agreement.contact_phone || "—",
    tier: agreement.tier || "BRONZE",
    created_at: agreement.created_at || "—",
    contract_start: agreement.contract_start || "—",
    contract_end: agreement.contract_end || "—",
  };

  return (
    <div>
      <PageHeader
        title="Profile & License — Wasifu na Leseni"
        description="Your RLA profile, contract terms, and license details."
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Territory" value={profile.territory} icon={MapPin} />
        <StatCard title="Market Share" value={`${profile.market_share_pct}%`} icon={Percent} />
        <StatCard title="License" value={profile.license_number} icon={Shield} />
        <StatCard title="Tier" value={profile.tier} icon={Award} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Business Profile */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Building2 className="h-4 w-4" /> Business Profile</CardTitle></CardHeader>
          <CardContent>
            <dl className="space-y-3 text-sm">
              <ProfileField label="Business Name" value={profile.agent_name} />
              <ProfileField label="Agent Type" value={
                <Badge variant="purple">
                  {profile.agent_type === "REGION_LICENSE_AGENT" ? "Region License Agent" : "Remote Agent"}
                </Badge>
              } />
              <ProfileField label="Status" value={<StatusBadge status={profile.status} />} />
              <ProfileField label="Territory / Region" value={<Badge variant="outline">{profile.territory}</Badge>} />
              <ProfileField label="Tier" value={
                <Badge variant={profile.tier === "GOLD" ? "warning" : profile.tier === "SILVER" ? "purple" : "outline"}>
                  {profile.tier}
                </Badge>
              } />
              <ProfileField label="Contact Person" value={profile.contact_person} />
              <ProfileField label="Email" value={profile.contact_email} icon={Mail} />
              <ProfileField label="Phone" value={profile.contact_phone} icon={Phone} />
            </dl>
          </CardContent>
        </Card>

        {/* License & Contract */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Scale className="h-4 w-4" /> License & Contract</CardTitle></CardHeader>
          <CardContent>
            <dl className="space-y-3 text-sm">
              <ProfileField label="License Number" value={<span className="font-mono">{profile.license_number}</span>} />
              <ProfileField label="Market Share" value={<span className="font-mono font-bold text-blue-600">{profile.market_share_pct}%</span>} />
              <ProfileField label="Commission Rate" value={
                <span className="font-mono">{typeof profile.commission_rate === "number" ? `${(profile.commission_rate * 100).toFixed(0)}%` : profile.commission_rate}</span>
              } />
              <ProfileField label="Max Platform Discount" value={<span className="font-mono">{profile.max_platform_discount_pct}%</span>} />
              <ProfileField label="Max Trial Days" value={<span className="font-mono">{profile.max_trial_days} days</span>} />
              <ProfileField label="Contract Start" value={profile.contract_start} icon={Calendar} />
              <ProfileField label="Contract End" value={profile.contract_end} icon={Calendar} />
              <ProfileField label="Member Since" value={profile.created_at} icon={Calendar} />
            </dl>
          </CardContent>
        </Card>
      </div>

      {/* Governance Details */}
      {agreement.governance && (
        <Card className="mt-6">
          <CardHeader><CardTitle className="flex items-center gap-2"><Shield className="h-4 w-4" /> Governance Permissions</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div className="rounded-lg border p-3 text-center">
                <p className="text-xs text-bos-silver-dark">Can File Taxes</p>
                <p className="mt-1 font-medium">{agreement.governance.can_file_taxes ? "Yes" : "No"}</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-xs text-bos-silver-dark">Can Appoint Sub-agents</p>
                <p className="mt-1 font-medium">{agreement.governance.can_appoint_sub_agents ? "Yes" : "No"}</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-xs text-bos-silver-dark">Max Tenants</p>
                <p className="mt-1 font-mono font-medium">{agreement.governance.max_tenants || "Unlimited"}</p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-xs text-bos-silver-dark">Training Completed</p>
                <p className="mt-1">
                  {agreement.governance.compliance_training_completed ? (
                    <CheckCircle className="mx-auto h-5 w-5 text-green-600" />
                  ) : (
                    <span className="text-amber-600">Pending</span>
                  )}
                </p>
              </div>
            </div>
            {agreement.governance.permissions?.length > 0 && (
              <div className="mt-4">
                <p className="text-xs text-bos-silver-dark mb-2">Permissions ({agreement.governance.permissions.length})</p>
                <div className="flex flex-wrap gap-1">
                  {agreement.governance.permissions.map((p: { permission_code: string }) => (
                    <Badge key={p.permission_code} variant="outline" className="text-xs">
                      {p.permission_code.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Region Compliance */}
      <Card className="mt-6">
        <CardHeader><CardTitle className="flex items-center gap-2"><FileText className="h-4 w-4" /> Region Compliance Status</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-lg bg-green-50 p-4 dark:bg-green-950">
              <p className="text-xs text-green-700 dark:text-green-400">Business Registration</p>
              <p className="mt-1 text-sm font-medium">
                <CheckCircle className="inline h-4 w-4 text-green-600 mr-1" /> Verified
              </p>
            </div>
            <div className="rounded-lg bg-green-50 p-4 dark:bg-green-950">
              <p className="text-xs text-green-700 dark:text-green-400">Tax Registration</p>
              <p className="mt-1 text-sm font-medium">
                <CheckCircle className="inline h-4 w-4 text-green-600 mr-1" /> Verified
              </p>
            </div>
            <div className="rounded-lg bg-amber-50 p-4 dark:bg-amber-950">
              <p className="text-xs text-amber-700 dark:text-amber-400">Annual Audit</p>
              <p className="mt-1 text-sm font-medium text-amber-700">
                {agreement.governance?.next_audit_due || "Not scheduled"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ProfileField({ label, value, icon: Icon }: {
  label: string; value: React.ReactNode; icon?: typeof Building2;
}) {
  return (
    <div className="flex justify-between items-center">
      <dt className="text-bos-silver-dark flex items-center gap-1">
        {Icon && <Icon className="h-3 w-3" />} {label}
      </dt>
      <dd>{value}</dd>
    </div>
  );
}
