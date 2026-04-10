"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  Card, CardContent, CardHeader, CardTitle, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getAgentDashboard, getMyTenants, getMyCommissions, getRemittanceStatus } from "@/lib/api/agents";
import { getLedgerEntries } from "@/lib/api/saas";
import { useAgentAuthStore } from "@/stores/agent-auth-store";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import {
  Users, Clock, DollarSign, TrendingUp, UserPlus, BarChart3,
  Percent, AlertCircle, Shield, ArrowRight,
  BookOpen, Send, UserCheck, Tag, FileCheck, Building2,
  AlertTriangle, MapPin,
} from "lucide-react";

export default function AgentDashboardPage() {
  const { isRLA, agentId, regionCode } = useAgentAuthStore();

  const dash = useQuery({ queryKey: ["agent", "dashboard"], queryFn: getAgentDashboard });
  const tenants = useQuery({ queryKey: ["agent", "tenants"], queryFn: () => getMyTenants() });
  const commissions = useQuery({
    queryKey: ["agent", "commissions"],
    queryFn: () => getMyCommissions(),
    enabled: !isRLA,
  });
  const remittance = useQuery({
    queryKey: ["agent", "remittance", agentId],
    queryFn: () => getRemittanceStatus(agentId),
    enabled: isRLA && !!agentId,
  });
  const ledger = useQuery({
    queryKey: ["agent", "ledger", "recent"],
    queryFn: () => getLedgerEntries({ limit: 10 }),
    enabled: isRLA,
  });

  const d = dash.data?.data ?? {};
  const tenantList: Array<Record<string, unknown>> = tenants.data?.data ?? [];
  const activeCount = tenantList.filter((t) => t.status === "ACTIVE" || t.status === "TRIAL").length;
  const trialCount = tenantList.filter((t) => t.status === "TRIAL").length;
  const payingCount = tenantList.filter((t) => t.status === "ACTIVE").length;

  type LedgerEntry = {
    entry_id: string; tenant_name: string; gross_amount: number;
    net_distributable: number; currency: string; status: string; created_at: string;
  };
  const recentLedger: LedgerEntry[] = ledger.data?.data ?? [];

  type CommissionEntry = {
    commission_id: string; tenant_name: string; amount: number;
    currency: string; period: string; status: string; created_at: string;
  };
  const commissionList: CommissionEntry[] = commissions.data?.data ?? [];
  const remittanceData = remittance.data?.data ?? {} as Record<string, unknown>;
  const overdueCount = (remittanceData.overdue_count as number) ?? 0;

  const expiringTrials = tenantList.filter((t) => {
    if (t.status !== "TRIAL") return false;
    const expiresAt = t.trial_expires_at as string;
    if (!expiresAt) return false;
    const daysLeft = Math.ceil((new Date(expiresAt).getTime() - Date.now()) / 86400000);
    return daysLeft <= 14 && daysLeft >= 0;
  });

  /* ── Remote Agent View ──────────────────────────────────────── */
  if (!isRLA) {
    return (
      <div>
        <PageHeader
          title="My Dashboard"
          description="Your tenants, commissions, and activity at a glance."
        />

        {/* Identity Banner */}
        <Card className="mb-6 border-bos-purple/20 bg-bos-purple-light/30 dark:border-bos-purple/10 dark:bg-bos-purple-light/10">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <UserCheck className="mt-0.5 h-5 w-5 text-bos-purple" />
              <div className="text-sm">
                <p className="font-semibold text-bos-purple">BOS Remote Agent</p>
                <p className="mt-1 text-neutral-600 dark:text-neutral-400">
                  You operate under your Region License Agent. Tenants you onboard are attributed to you and commissions accrue automatically on each tenant payment.
                </p>
                {regionCode && (
                  <p className="mt-1 flex items-center gap-1 text-xs text-bos-silver-dark">
                    <MapPin className="h-3 w-3" /> Region: {regionCode}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* My Key Metrics */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            title="My Tenants"
            value={tenantList.length}
            icon={Users}
            description={`${payingCount} paying, ${trialCount} trials`}
          />
          <StatCard
            title="Active Tenants"
            value={activeCount}
            icon={UserPlus}
          />
          <StatCard
            title="This Month"
            value={d.month_commission ?? "—"}
            icon={TrendingUp}
            description="Commission earned"
          />
          <StatCard
            title="Pending Payout"
            value={d.pending_payout ?? "—"}
            icon={DollarSign}
            description="Accrued, not yet paid"
          />
        </div>

        {/* Expiring Trials */}
        {expiringTrials.length > 0 && (
          <Card className="mt-4 border-amber-200 dark:border-amber-800">
            <CardContent className="flex items-center gap-4 p-4">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              <div className="flex-1 text-sm">
                <Badge variant="gold">{expiringTrials.length}</Badge> trial{expiringTrials.length > 1 ? "s" : ""} expiring within 14 days — follow up to convert!
              </div>
              <Link href="/agent/trials" className="text-sm text-bos-purple hover:underline">View Trials</Link>
            </CardContent>
          </Card>
        )}

        {/* Quick Actions */}
        <h2 className="mt-8 mb-4 text-lg font-semibold">Quick Actions</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <QuickAction title="Onboard Tenant" description="Register a new business on BOS" href="/agent/onboard" icon={UserPlus} />
          <QuickAction title="My Commissions" description="Track your earnings per tenant" href="/agent/commissions" icon={TrendingUp} />
          <QuickAction title="Create Promotion" description="Offer promos to attract tenants" href="/agent/promotions" icon={Tag} />
          <QuickAction title="Profile & Contract" description="Your agent contract and settings" href="/agent/profile" icon={Building2} />
        </div>

        {/* Recent Commissions */}
        <h2 className="mt-8 mb-4 text-lg font-semibold">Recent Commissions</h2>
        <Card>
          <CardContent className="p-0">
            {commissionList.length === 0 ? (
              <EmptyState title="No commissions yet" description="Commissions appear here when your tenants pay" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tenant</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Currency</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {commissionList.slice(0, 8).map((c) => (
                    <TableRow key={c.commission_id}>
                      <TableCell className="text-sm font-medium">{c.tenant_name || "—"}</TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">{c.period}</TableCell>
                      <TableCell className="text-right font-mono text-green-600">{(c.amount || 0).toLocaleString()}</TableCell>
                      <TableCell className="text-xs">{c.currency}</TableCell>
                      <TableCell className="text-center"><StatusBadge status={c.status} /></TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">{c.created_at ? formatDate(c.created_at) : "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* My Tenants Preview */}
        <h2 className="mt-8 mb-4 text-lg font-semibold">My Tenants</h2>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Tenants I Manage</CardTitle>
              <Link href="/agent/tenants" className="text-sm text-bos-purple hover:underline">View All &rarr;</Link>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {tenantList.length === 0 ? (
              <EmptyState title="No tenants yet" description="Onboard your first tenant to get started" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Business</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead>City</TableHead>
                    <TableHead>Joined</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tenantList.slice(0, 5).map((t) => (
                    <TableRow key={t.business_id as string}>
                      <TableCell className="text-sm font-medium">{(t.business_name as string) || "—"}</TableCell>
                      <TableCell className="text-center"><StatusBadge status={t.status as string} /></TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">{(t.city as string) || "—"}</TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">{t.created_at ? formatDate(t.created_at as string) : "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  /* ── RLA View (full regional dashboard) ────────────────────── */
  return (
    <div>
      <PageHeader
        title="RLA Dashboard"
        description="Manage your region, tenants, agents, and all your revenue."
      />

      {/* RLA Doctrine */}
      <Card className="mb-6 border-bos-purple/20 bg-bos-purple-light/30 dark:border-bos-purple/10 dark:bg-bos-purple-light/10">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Shield className="mt-0.5 h-5 w-5 text-bos-purple" />
            <div className="text-sm">
              <p className="font-semibold text-bos-purple">Region License Agent</p>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-4">
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">Onboard Tenants</p>
                  <p className="text-xs text-bos-silver-dark">Create trials, convert to paying</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">Collect Revenue</p>
                  <p className="text-xs text-bos-silver-dark">Tenant payments flow through you</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">Manage Agents</p>
                  <p className="text-xs text-bos-silver-dark">Remote agents earn under your license</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">Remit to Platform</p>
                  <p className="text-xs text-bos-silver-dark">Send platform share, keep your cut</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics Row 1 */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          title="Total Tenants"
          value={d.total_tenants ?? tenantList.length}
          icon={Users}
          description={`${payingCount} paying, ${trialCount} trials`}
        />
        <StatCard
          title="Monthly Revenue"
          value={d.month_revenue ?? "—"}
          icon={DollarSign}
          description="From tenant subscriptions"
        />
        <StatCard
          title="My Commission"
          value={d.month_commission ?? "—"}
          icon={TrendingUp}
          description="Earned this month"
        />
        <StatCard
          title="Trial Conversion"
          value={d.conversion_rate ?? "—"}
          icon={BarChart3}
          description="Converted / total"
        />
      </div>

      {/* Key Metrics Row 2 */}
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          title="Active Tenants"
          value={d.active_tenants ?? activeCount}
          icon={UserPlus}
        />
        <StatCard
          title="Commission Rate"
          value={d.commission_rate ? `${d.commission_rate}%` : "—"}
          icon={Percent}
          description="Market share rate"
        />
        <StatCard
          title="Pending Payout"
          value={d.pending_payout ?? "—"}
          icon={DollarSign}
          description="Accrued, not yet paid"
        />
        <StatCard
          title="Tenants on Trial"
          value={d.trial_tenants ?? trialCount}
          icon={Clock}
        />
      </div>

      {/* Remittance Overdue Alert */}
      {overdueCount > 0 && (
        <Card className="mt-4 border-red-200 dark:border-red-800">
          <CardContent className="flex items-center gap-4 p-4">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <div className="flex-1 text-sm">
              <span className="font-semibold text-red-600">Remittance overdue!</span>{" "}
              {overdueCount} overdue remittance{overdueCount > 1 ? "s" : ""} — payout approval is blocked until cleared.
            </div>
            <Link href="/agent/revenue/remittance" className="text-sm text-red-600 hover:underline font-medium">Remit Now</Link>
          </CardContent>
        </Card>
      )}

      {/* Expiring Trials Alert */}
      {expiringTrials.length > 0 && (
        <Card className="mt-4 border-amber-200 dark:border-amber-800">
          <CardContent className="flex items-center gap-4 p-4">
            <AlertTriangle className="h-5 w-5 text-amber-600" />
            <div className="flex-1 text-sm">
              <Badge variant="gold">{expiringTrials.length}</Badge> trial{expiringTrials.length > 1 ? "s" : ""} expiring within 14 days — follow up to convert!
            </div>
            <Link href="/agent/trials" className="text-sm text-bos-purple hover:underline">View Trials</Link>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Quick Actions</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <QuickAction title="Onboard Tenant" description="Register a new business on BOS" href="/agent/onboard" icon={UserPlus} />
        <QuickAction title="Revenue Ledger" description="Per-sale breakdown and distribution" href="/agent/revenue/ledger" icon={BookOpen} />
        <QuickAction title="Remittance" description="Remit platform share" href="/agent/revenue/remittance" icon={Send} />
        <QuickAction title="My Agents" description="Remote agents in your region" href="/agent/remote-agents" icon={UserCheck} />
        <QuickAction title="Create Promotion" description="Offer promos to attract tenants" href="/agent/promotions" icon={Tag} />
        <QuickAction title="My Staff" description="Manage your office team" href="/agent/staff" icon={Users} />
        <QuickAction title="Compliance" description="Region compliance documents" href="/agent/compliance" icon={FileCheck} />
        <QuickAction title="Profile & License" description="Your license, contract, settings" href="/agent/profile" icon={Building2} />
      </div>

      {/* Recent Revenue Ledger */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Recent Revenue</h2>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Latest Ledger Entries</CardTitle>
            <Link href="/agent/revenue/ledger" className="text-sm text-bos-purple hover:underline">View All &rarr;</Link>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {recentLedger.length === 0 ? (
            <EmptyState title="No revenue yet" description="Revenue entries will appear here when tenants pay" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tenant</TableHead>
                  <TableHead className="text-right">Gross</TableHead>
                  <TableHead className="text-right">Net</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentLedger.slice(0, 5).map((e) => (
                  <TableRow key={e.entry_id}>
                    <TableCell className="text-sm font-medium">{e.tenant_name || "—"}</TableCell>
                    <TableCell className="text-right font-mono">{(e.gross_amount || 0).toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono text-green-600">{(e.net_distributable || 0).toLocaleString()}</TableCell>
                    <TableCell className="text-xs">{e.currency}</TableCell>
                    <TableCell className="text-center"><StatusBadge status={e.status} /></TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{e.created_at ? formatDate(e.created_at) : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function QuickAction({ title, description, href, icon: Icon }: {
  title: string; description: string; href: string; icon: typeof Users;
}) {
  return (
    <Link href={href}>
      <Card className="group cursor-pointer transition-shadow hover:shadow-md">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-bos-purple-light transition-colors group-hover:bg-bos-purple group-hover:text-white">
              <Icon className="h-4 w-4 text-bos-purple group-hover:text-white" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold">{title}</h3>
              <p className="mt-0.5 text-xs text-bos-silver-dark">{description}</p>
            </div>
            <ArrowRight className="mt-1 h-4 w-4 text-bos-silver opacity-0 transition-opacity group-hover:opacity-100" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
