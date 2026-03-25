"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui";
import { getComplianceStats } from "@/lib/api/platform";
import {
  RefreshCw,
  CheckCircle,
  XCircle,
  Shield,
  Users,
  MapPin,
  AlertTriangle,
  BarChart3,
  Clock,
  FileCheck,
} from "lucide-react";

const STATE_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: "Draft", color: "bg-neutral-100 text-neutral-600" },
  submitted: { label: "Submitted", color: "bg-blue-100 text-blue-700" },
  under_review: { label: "Under Review", color: "bg-purple-100 text-purple-700" },
  verified: { label: "Verified", color: "bg-green-100 text-green-700" },
  active: { label: "Active", color: "bg-green-200 text-green-800" },
  rejected: { label: "Rejected", color: "bg-red-100 text-red-700" },
  restricted: { label: "Restricted", color: "bg-orange-100 text-orange-700" },
  suspended: { label: "Suspended", color: "bg-yellow-100 text-yellow-700" },
  blocked: { label: "Blocked", color: "bg-red-200 text-red-800" },
  deactivated: { label: "Deactivated", color: "bg-neutral-200 text-neutral-500" },
};

interface ComplianceStats {
  total_profiles: number;
  state_counts: Record<string, number>;
  country_counts: Record<string, number>;
  verification_counts: {
    tax_id_verified: number;
    company_reg_verified: number;
    address_verified: number;
    billing_eligible: number;
  };
  stuck_profiles: number;
  stuck_profile_ids: string[];
  rejection_reasons: Record<string, number>;
}

export default function VerificationDashboardPage() {
  const statsQuery = useQuery({
    queryKey: ["platform", "compliance", "stats"],
    queryFn: getComplianceStats,
    refetchInterval: 60_000,
  });

  const stats: ComplianceStats | null = statsQuery.data?.data ?? null;

  const totalProfiles = stats?.total_profiles ?? 0;
  const verCounts = stats?.verification_counts ?? {
    tax_id_verified: 0,
    company_reg_verified: 0,
    address_verified: 0,
    billing_eligible: 0,
  };
  const stateCounts = stats?.state_counts ?? {};
  const countryCounts = stats?.country_counts ?? {};
  const rejectionReasons = stats?.rejection_reasons ?? {};
  const stuckCount = stats?.stuck_profiles ?? 0;

  // Derived metrics
  const activeCount = (stateCounts["active"] ?? 0) + (stateCounts["verified"] ?? 0);
  const pendingCount = (stateCounts["submitted"] ?? 0) + (stateCounts["under_review"] ?? 0);
  const rejectedCount = stateCounts["rejected"] ?? 0;
  const verificationRate = totalProfiles > 0
    ? Math.round((activeCount / totalProfiles) * 100)
    : 0;

  return (
    <div>
      <PageHeader
        title="Verification Dashboard"
        description="Compliance verification rates, bottlenecks, and country-level metrics"
        actions={
          <Button variant="outline" size="sm" onClick={() => statsQuery.refetch()}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>
        }
      />

      {/* KPI Row 1 */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Profiles" value={totalProfiles} icon={Users} />
        <StatCard
          title="Verification Rate"
          value={`${verificationRate}%`}
          icon={CheckCircle}
          description={`${activeCount} active of ${totalProfiles} total`}
        />
        <StatCard
          title="Pending Review"
          value={pendingCount}
          icon={Clock}
          description="Submitted + under review"
        />
        <StatCard
          title="Stuck Profiles"
          value={stuckCount}
          icon={AlertTriangle}
          description="Submitted >7 days ago"
        />
      </div>

      {/* KPI Row 2 */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Tax ID Verified"
          value={verCounts.tax_id_verified}
          icon={FileCheck}
          description={totalProfiles > 0 ? `${Math.round((verCounts.tax_id_verified / totalProfiles) * 100)}% of total` : ""}
        />
        <StatCard
          title="Company Reg Verified"
          value={verCounts.company_reg_verified}
          icon={Shield}
          description={totalProfiles > 0 ? `${Math.round((verCounts.company_reg_verified / totalProfiles) * 100)}% of total` : ""}
        />
        <StatCard
          title="Address Verified"
          value={verCounts.address_verified}
          icon={MapPin}
          description={totalProfiles > 0 ? `${Math.round((verCounts.address_verified / totalProfiles) * 100)}% of total` : ""}
        />
        <StatCard
          title="Billing Eligible"
          value={verCounts.billing_eligible}
          icon={BarChart3}
          description={totalProfiles > 0 ? `${Math.round((verCounts.billing_eligible / totalProfiles) * 100)}% of total` : ""}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* State Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Profile State Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(stateCounts).length === 0 ? (
              <div className="py-8 text-center text-neutral-400">No profile data.</div>
            ) : (
              <div className="space-y-3">
                {Object.entries(stateCounts)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .map(([state, count]) => {
                    const cfg = STATE_LABELS[state] || { label: state, color: "bg-neutral-100 text-neutral-600" };
                    const pct = totalProfiles > 0 ? Math.round(((count as number) / totalProfiles) * 100) : 0;
                    return (
                      <div key={state} className="flex items-center gap-3">
                        <div className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.color}`}>
                          {cfg.label}
                        </div>
                        <div className="flex-1">
                          <div className="h-2 rounded-full bg-neutral-100 dark:bg-neutral-800">
                            <div
                              className="h-2 rounded-full bg-bos-purple transition-all"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                        <div className="w-20 text-right text-sm font-medium">
                          {count as number} <span className="text-xs text-neutral-400">({pct}%)</span>
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Country Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Profiles by Country</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(countryCounts).length === 0 ? (
              <div className="py-8 text-center text-neutral-400">No country data.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Country</TableHead>
                    <TableHead>Profiles</TableHead>
                    <TableHead>Share</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(countryCounts)
                    .sort(([, a], [, b]) => (b as number) - (a as number))
                    .map(([code, count]) => (
                      <TableRow key={code}>
                        <TableCell>
                          <div className="flex items-center gap-1.5">
                            <MapPin className="h-3.5 w-3.5 text-neutral-400" />
                            <Badge variant="outline">{code}</Badge>
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">{count as number}</TableCell>
                        <TableCell className="text-neutral-400">
                          {totalProfiles > 0 ? `${Math.round(((count as number) / totalProfiles) * 100)}%` : "0%"}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Rejection Reasons */}
      {Object.keys(rejectionReasons).length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-500" />
              Rejection Reasons
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Reason</TableHead>
                  <TableHead>Count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(rejectionReasons)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .map(([reason, count]) => (
                    <TableRow key={reason}>
                      <TableCell className="text-sm">{reason}</TableCell>
                      <TableCell>
                        <Badge variant="destructive">{count as number}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Stuck Profiles Alert */}
      {stuckCount > 0 && (
        <Card className="mt-6 border-l-4 border-l-orange-500">
          <CardContent className="flex items-center gap-4 p-5">
            <AlertTriangle className="h-8 w-8 text-orange-500" />
            <div>
              <h3 className="font-bold text-orange-700">
                {stuckCount} Profile{stuckCount > 1 ? "s" : ""} Stuck in Queue
              </h3>
              <p className="text-sm text-neutral-500">
                These profiles were submitted more than 7 days ago and are still pending review.
                Visit the{" "}
                <a href="/platform/reviews" className="text-bos-purple underline">
                  Review Queue
                </a>{" "}
                to process them.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
