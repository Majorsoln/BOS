"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, CardHeader, CardTitle, Badge, Select,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getAgents, getAgentPayouts } from "@/lib/api/agents";
import { getSubscriptions, getTrials } from "@/lib/api/saas";
import { useRegions } from "@/hooks/use-regions";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import {
  DollarSign, TrendingUp, Users, Wallet, BarChart3, Shield,
  UserCheck, ArrowUpRight, ArrowDownRight, Clock, PiggyBank,
  AlertTriangle, CreditCard, Building2, Eye,
} from "lucide-react";

type TabKey = "overview" | "collections" | "projections" | "ledger";

export default function FinanceDashboardPage() {
  const [tab, setTab] = useState<TabKey>("overview");

  const tabs: { key: TabKey; label: string }[] = [
    { key: "overview", label: "Revenue Overview" },
    { key: "collections", label: "RLA Collections" },
    { key: "projections", label: "Projections" },
    { key: "ledger", label: "Payouts Ledger" },
  ];

  return (
    <div>
      <PageHeader
        title="Finance — Platform Revenue"
        description="RLA collects money. Platform sees everything, sets payment rules, approves payouts."
      />

      {/* Doctrine */}
      <Card className="mb-6 border-green-200/50 bg-green-50/30 dark:border-green-800/30 dark:bg-green-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <PiggyBank className="mt-0.5 h-5 w-5 text-green-600" />
            <div className="text-sm">
              <p className="font-semibold text-green-700 dark:text-green-400">Finance Doctrine — All Revenue Must Be Reported</p>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-4">
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">RLA Collects</p>
                  <p className="text-xs text-bos-silver-dark">Tenant payments go through RLA</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">Platform Sees All</p>
                  <p className="text-xs text-bos-silver-dark">Revenue, commissions, remittances</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">Sets Rules</p>
                  <p className="text-xs text-bos-silver-dark">Settlement, thresholds, clawback</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">Approves Payouts</p>
                  <p className="text-xs text-bos-silver-dark">Agent commission disbursements</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="mb-6 flex gap-1 rounded-lg bg-bos-silver-light p-1 dark:bg-neutral-800 w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-white text-bos-purple shadow-sm dark:bg-neutral-900"
                : "text-bos-silver-dark hover:text-neutral-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <RevenueOverviewTab />}
      {tab === "collections" && <CollectionsTab />}
      {tab === "projections" && <ProjectionsTab />}
      {tab === "ledger" && <PlatformLedgerTab />}
    </div>
  );
}

/* ── Revenue Overview Tab ─────────────────────────────── */

function RevenueOverviewTab() {
  const { regions } = useRegions();
  const rlaQuery = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });
  const remoteQuery = useQuery({
    queryKey: ["saas", "agents", "REMOTE_AGENT"],
    queryFn: () => getAgents({ type: "REMOTE_AGENT" }),
  });
  const subsQuery = useQuery({
    queryKey: ["saas", "subscriptions", "all"],
    queryFn: () => getSubscriptions({ status: undefined }),
  });
  const payoutsQuery = useQuery({
    queryKey: ["saas", "agents", "payouts"],
    queryFn: () => getAgentPayouts({}),
  });

  type AgentRow = {
    agent_id: string; agent_name: string; agent_type: string; status: string;
    tenant_count?: number; active_tenant_count?: number;
    total_commission_earned?: string; pending_commission?: string;
    territory?: string; market_share_pct?: number;
  };

  const rlas: AgentRow[] = rlaQuery.data?.data ?? [];
  const remotes: AgentRow[] = remoteQuery.data?.data ?? [];
  const allAgents = [...rlas, ...remotes];
  const subList: Array<Record<string, unknown>> = subsQuery.data?.data ?? [];
  const payoutList: Array<Record<string, unknown>> = payoutsQuery.data?.data ?? [];

  const payingSubs = subList.filter((s) => s.status === "ACTIVE");
  const trialSubs = subList.filter((s) => s.status === "TRIAL");

  // Revenue estimates
  const monthlyRevenue = payingSubs.reduce((s, sub) => {
    const amt = parseFloat((sub.monthly_amount as string) || "0");
    return s + amt;
  }, 0);

  const totalCommissionsEarned = allAgents.reduce((s, a) => s + parseFloat(a.total_commission_earned || "0"), 0);
  const totalPendingPayouts = allAgents.reduce((s, a) => s + parseFloat(a.pending_commission || "0"), 0);
  const platformRevenue = monthlyRevenue - totalPendingPayouts;

  const pendingPayoutCount = payoutList.filter((p) => p.status === "PENDING").length;

  return (
    <div className="space-y-6">
      {/* Top-line stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          title="Monthly Revenue"
          value={monthlyRevenue > 0 ? monthlyRevenue.toLocaleString() : "—"}
          icon={DollarSign}
          description={`${payingSubs.length} paying tenants`}
        />
        <StatCard
          title="Platform Share"
          value={platformRevenue > 0 ? platformRevenue.toLocaleString() : "—"}
          icon={Building2}
          description="After agent commissions"
        />
        <StatCard
          title="Agent Commissions"
          value={totalCommissionsEarned.toLocaleString()}
          icon={Wallet}
          description={`${totalPendingPayouts.toLocaleString()} pending`}
        />
        <StatCard
          title="Pending Payouts"
          value={pendingPayoutCount}
          icon={Clock}
          description={
            <Link href="/platform/finance/approvals" className="text-bos-purple hover:underline">
              Review &rarr;
            </Link>
          }
        />
      </div>

      {/* Revenue flow */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Revenue Flow</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-5">
            <FlowCard
              icon={Users}
              label="Tenants Pay"
              value={`${payingSubs.length} active`}
              color="blue"
            />
            <FlowArrow />
            <FlowCard
              icon={Shield}
              label="RLA Collects"
              value={`${rlas.filter(a => a.status === "ACTIVE").length} regions`}
              color="purple"
            />
            <FlowArrow />
            <FlowCard
              icon={Building2}
              label="Platform Receives"
              value={platformRevenue > 0 ? platformRevenue.toLocaleString() : "—"}
              color="green"
            />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg border p-3 text-center">
              <p className="text-xs text-bos-silver-dark">Gross Revenue</p>
              <p className="text-lg font-bold font-mono">{monthlyRevenue.toLocaleString()}</p>
            </div>
            <div className="rounded-lg border p-3 text-center">
              <p className="text-xs text-bos-silver-dark">RLA Market Share</p>
              <p className="text-lg font-bold font-mono text-purple-600">
                {rlas.length > 0
                  ? `${Math.round(rlas.reduce((s, a) => s + (a.market_share_pct ?? 0), 0) / rlas.length)}% avg`
                  : "—"}
              </p>
            </div>
            <div className="rounded-lg border p-3 text-center">
              <p className="text-xs text-bos-silver-dark">Remote Commissions</p>
              <p className="text-lg font-bold font-mono text-green-600">
                {remotes.reduce((s, a) => s + parseFloat(a.total_commission_earned || "0"), 0).toLocaleString()}
              </p>
            </div>
            <div className="rounded-lg border p-3 text-center">
              <p className="text-xs text-bos-silver-dark">Pipeline (Trials)</p>
              <p className="text-lg font-bold font-mono text-amber-600">{trialSubs.length} tenants</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Revenue by Region */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Revenue by Region</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {rlas.length === 0 ? (
            <EmptyState title="No RLAs" description="Revenue tracking starts when RLAs are appointed" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Region</TableHead>
                  <TableHead>RLA</TableHead>
                  <TableHead className="text-center">Tenants</TableHead>
                  <TableHead className="text-center">Market Share</TableHead>
                  <TableHead className="text-right">RLA Earned</TableHead>
                  <TableHead className="text-right">RLA Pending</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rlas.map((a) => {
                  const region = regions.find((r) => r.code === a.territory);
                  return (
                    <TableRow key={a.agent_id}>
                      <TableCell>
                        <span className="font-medium">{a.territory}</span>
                        {region && <span className="ml-2 text-xs text-bos-silver-dark">{region.name}</span>}
                      </TableCell>
                      <TableCell>
                        <Link href={`/platform/agents/${a.agent_id}`} className="text-bos-purple hover:underline">
                          {a.agent_name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-center font-mono">{a.active_tenant_count ?? a.tenant_count ?? 0}</TableCell>
                      <TableCell className="text-center font-mono">{a.market_share_pct ?? "—"}%</TableCell>
                      <TableCell className="text-right font-mono">{parseFloat(a.total_commission_earned || "0").toLocaleString()}</TableCell>
                      <TableCell className="text-right font-mono">
                        {parseFloat(a.pending_commission || "0") > 0 ? (
                          <span className="text-amber-600">{parseFloat(a.pending_commission || "0").toLocaleString()}</span>
                        ) : "0"}
                      </TableCell>
                      <TableCell className="text-center"><StatusBadge status={a.status} /></TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/* ── RLA Collections Tab ──────────────────────────────── */

function CollectionsTab() {
  const [regionFilter, setRegionFilter] = useState("");
  const { regions } = useRegions();

  const rlaQuery = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });
  const payoutsQuery = useQuery({
    queryKey: ["saas", "agents", "payouts"],
    queryFn: () => getAgentPayouts({}),
  });

  type AgentRow = {
    agent_id: string; agent_name: string; status: string;
    territory?: string; tenant_count?: number; active_tenant_count?: number;
    total_commission_earned?: string; pending_commission?: string;
    market_share_pct?: number; license_number?: string;
  };

  const rlas: AgentRow[] = rlaQuery.data?.data ?? [];
  const payouts: Array<Record<string, unknown>> = payoutsQuery.data?.data ?? [];

  const filtered = regionFilter
    ? rlas.filter((a) => a.territory === regionFilter)
    : rlas;

  // Available regions
  const activeRegions = [...new Set(rlas.map((a) => a.territory).filter(Boolean))];

  return (
    <div className="space-y-6">
      {/* Filter */}
      <div className="flex gap-3">
        <Select value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)} className="w-48">
          <option value="">All Regions</option>
          {activeRegions.map((r) => (
            <option key={r} value={r}>{r} — {regions.find((reg) => reg.code === r)?.name || r}</option>
          ))}
        </Select>
      </div>

      {/* Collection cards per RLA */}
      {filtered.length === 0 ? (
        <EmptyState title="No RLAs" description="Collections are tracked per Region License Agent" />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {filtered.map((rla) => {
            const earned = parseFloat(rla.total_commission_earned || "0");
            const pending = parseFloat(rla.pending_commission || "0");
            const tenants = rla.active_tenant_count ?? rla.tenant_count ?? 0;
            const rlaPayouts = payouts.filter((p) => p.agent_id === rla.agent_id);
            const completedPayouts = rlaPayouts.filter((p) => p.status === "COMPLETED");
            const pendingPayouts = rlaPayouts.filter((p) => p.status === "PENDING");
            const region = regions.find((r) => r.code === rla.territory);

            return (
              <Card key={rla.agent_id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-sm">
                        <Link href={`/platform/agents/${rla.agent_id}`} className="text-bos-purple hover:underline">
                          {rla.agent_name}
                        </Link>
                      </CardTitle>
                      <p className="text-xs text-bos-silver-dark">
                        {rla.territory} {region ? `— ${region.name}` : ""} | {rla.license_number || "No license"}
                      </p>
                    </div>
                    <StatusBadge status={rla.status} />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs text-bos-silver-dark">Market Share</p>
                      <p className="font-mono font-bold text-purple-600">{rla.market_share_pct ?? "—"}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-bos-silver-dark">Active Tenants</p>
                      <p className="font-mono font-bold">{tenants}</p>
                    </div>
                    <div>
                      <p className="text-xs text-bos-silver-dark">Total Earned</p>
                      <p className="font-mono text-green-600">{earned.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-bos-silver-dark">Pending Payout</p>
                      <p className={`font-mono ${pending > 0 ? "text-amber-600" : ""}`}>{pending.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-bos-silver-dark">Completed Payouts</p>
                      <p className="font-mono">{completedPayouts.length}</p>
                    </div>
                    <div>
                      <p className="text-xs text-bos-silver-dark">Pending Approvals</p>
                      <p className={`font-mono ${pendingPayouts.length > 0 ? "text-red-600 font-bold" : ""}`}>
                        {pendingPayouts.length}
                      </p>
                    </div>
                  </div>

                  {/* Remittance health */}
                  <div className="mt-3 rounded-lg bg-neutral-50 p-2 dark:bg-neutral-900">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-bos-silver-dark">Collection Health</span>
                      <Badge variant={tenants > 0 ? (pending > earned * 0.5 ? "gold" : "success") : "outline"}>
                        {tenants === 0 ? "No Revenue" : pending > earned * 0.5 ? "High Pending" : "Healthy"}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Projections Tab ──────────────────────────────────── */

function ProjectionsTab() {
  const subsQuery = useQuery({
    queryKey: ["saas", "subscriptions", "all"],
    queryFn: () => getSubscriptions({ status: undefined }),
  });
  const trialsQuery = useQuery({
    queryKey: ["saas", "trials", "all"],
    queryFn: () => getTrials({ status: undefined }),
  });
  const rlaQuery = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });

  const subList: Array<Record<string, unknown>> = subsQuery.data?.data ?? [];
  const trialList: Array<Record<string, unknown>> = trialsQuery.data?.data ?? [];
  const rlas: Array<Record<string, unknown>> = rlaQuery.data?.data ?? [];

  const payingSubs = subList.filter((s) => s.status === "ACTIVE");
  const trialSubs = subList.filter((s) => s.status === "TRIAL");

  const currentMRR = payingSubs.reduce((s, sub) => s + parseFloat((sub.monthly_amount as string) || "0"), 0);

  // Projection: if X% of trials convert
  const trialValue = trialSubs.reduce((s, sub) => s + parseFloat((sub.monthly_amount as string) || "0"), 0);

  const convertedTrials = trialList.filter((t) => t.status === "CONVERTED").length;
  const totalTrials = trialList.length;
  const historicalConvRate = totalTrials > 0 ? convertedTrials / totalTrials : 0.3; // default 30%

  const projectedMRR = currentMRR + (trialValue * historicalConvRate);

  // ARR
  const currentARR = currentMRR * 12;
  const projectedARR = projectedMRR * 12;

  // Average RLA market share
  const avgMarketShare = rlas.length > 0
    ? rlas.reduce((s, a) => s + ((a.market_share_pct as number) ?? 0), 0) / rlas.length
    : 0;
  const platformShare = 100 - avgMarketShare;

  return (
    <div className="space-y-6">
      {/* Current vs Projected */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Current MRR" value={currentMRR.toLocaleString()} icon={DollarSign} description="Monthly Recurring Revenue" />
        <StatCard title="Current ARR" value={currentARR.toLocaleString()} icon={TrendingUp} description="Annual (MRR x 12)" />
        <StatCard
          title="Projected MRR"
          value={projectedMRR.toLocaleString()}
          icon={BarChart3}
          description={`If ${Math.round(historicalConvRate * 100)}% trials convert`}
        />
        <StatCard title="Projected ARR" value={projectedARR.toLocaleString()} icon={TrendingUp} description="Including trial conversions" />
      </div>

      {/* Revenue split projection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Revenue Split — Platform vs Agents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-lg border-2 border-green-200 bg-green-50 p-4 text-center dark:border-green-800 dark:bg-green-950">
              <p className="text-xs text-green-700 dark:text-green-400">Platform Revenue (est.)</p>
              <p className="text-2xl font-bold font-mono text-green-700 dark:text-green-400">
                {Math.round(currentMRR * (platformShare / 100)).toLocaleString()}
              </p>
              <p className="text-xs text-bos-silver-dark">{platformShare.toFixed(0)}% platform share</p>
            </div>
            <div className="rounded-lg border-2 border-purple-200 bg-purple-50 p-4 text-center dark:border-purple-800 dark:bg-purple-950">
              <p className="text-xs text-purple-700 dark:text-purple-400">RLA Market Share (est.)</p>
              <p className="text-2xl font-bold font-mono text-purple-700 dark:text-purple-400">
                {Math.round(currentMRR * (avgMarketShare / 100)).toLocaleString()}
              </p>
              <p className="text-xs text-bos-silver-dark">{avgMarketShare.toFixed(0)}% avg RLA share</p>
            </div>
            <div className="rounded-lg border-2 border-blue-200 bg-blue-50 p-4 text-center dark:border-blue-800 dark:bg-blue-950">
              <p className="text-xs text-blue-700 dark:text-blue-400">Trial Pipeline Value</p>
              <p className="text-2xl font-bold font-mono text-blue-700 dark:text-blue-400">
                {trialValue.toLocaleString()}
              </p>
              <p className="text-xs text-bos-silver-dark">{trialSubs.length} tenants on trial</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Conversion Funnel */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Trial Conversion Funnel</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-950">
              <p className="text-2xl font-bold text-blue-700 dark:text-blue-400">{totalTrials}</p>
              <p className="text-xs text-bos-silver-dark">Total Trials</p>
            </div>
            <div className="rounded-lg bg-amber-50 p-3 dark:bg-amber-950">
              <p className="text-2xl font-bold text-amber-700 dark:text-amber-400">
                {trialList.filter((t) => t.status === "ACTIVE").length}
              </p>
              <p className="text-xs text-bos-silver-dark">Active Trials</p>
            </div>
            <div className="rounded-lg bg-green-50 p-3 dark:bg-green-950">
              <p className="text-2xl font-bold text-green-700 dark:text-green-400">{convertedTrials}</p>
              <p className="text-xs text-bos-silver-dark">Converted</p>
            </div>
            <div className="rounded-lg bg-red-50 p-3 dark:bg-red-950">
              <p className="text-2xl font-bold text-red-700 dark:text-red-400">
                {trialList.filter((t) => t.status === "EXPIRED").length}
              </p>
              <p className="text-xs text-bos-silver-dark">Expired</p>
            </div>
          </div>
          <div className="mt-3 text-center text-sm text-bos-silver-dark">
            Historical conversion rate: <span className="font-bold text-green-600">{Math.round(historicalConvRate * 100)}%</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Platform Ledger Tab ──────────────────────────────── */

function PlatformLedgerTab() {
  const payoutsQuery = useQuery({
    queryKey: ["saas", "agents", "payouts"],
    queryFn: () => getAgentPayouts({}),
  });

  const payouts: Array<Record<string, unknown>> = payoutsQuery.data?.data ?? [];

  const completed = payouts.filter((p) => p.status === "COMPLETED");
  const pending = payouts.filter((p) => p.status === "PENDING");
  const rejected = payouts.filter((p) => p.status === "REJECTED" || p.status === "FAILED");

  const totalDisbursed = completed.reduce((s, p) => s + parseFloat((p.amount as string) || "0"), 0);
  const totalPending = pending.reduce((s, p) => s + parseFloat((p.amount as string) || "0"), 0);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Total Disbursed" value={totalDisbursed.toLocaleString()} icon={ArrowUpRight} description={`${completed.length} payouts`} />
        <StatCard title="Pending Approval" value={totalPending.toLocaleString()} icon={Clock} description={`${pending.length} requests`} />
        <StatCard title="Rejected" value={rejected.length.toString()} icon={AlertTriangle} />
        <StatCard title="Total Transactions" value={payouts.length.toString()} icon={CreditCard} />
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">All Payout Transactions</CardTitle>
            <div className="flex gap-4">
              <Link href="/platform/finance/ledger" className="text-sm text-bos-purple hover:underline">
                Revenue Ledger &rarr;
              </Link>
              <Link href="/platform/finance/approvals" className="text-sm text-bos-purple hover:underline">
                Approvals &rarr;
              </Link>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {payouts.length === 0 ? (
            <EmptyState title="No transactions" description="Payout transactions will appear here" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payouts.slice(0, 30).map((p, i) => (
                  <TableRow key={i}>
                    <TableCell className="text-sm font-medium">{(p.agent_name as string) || "—"}</TableCell>
                    <TableCell>
                      <Badge variant={(p.agent_type as string) === "REGION_LICENSE_AGENT" ? "purple" : "success"}>
                        {(p.agent_type as string) === "REGION_LICENSE_AGENT" ? "RLA" : "Remote"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{(p.period as string) || "—"}</TableCell>
                    <TableCell className="text-right font-mono">{parseFloat((p.amount as string) || "0").toLocaleString()}</TableCell>
                    <TableCell className="text-xs">{(p.currency as string) || "—"}</TableCell>
                    <TableCell className="text-xs">{(p.method as string) || "—"}</TableCell>
                    <TableCell className="text-center"><StatusBadge status={p.status as string} /></TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{p.requested_at ? formatDate(p.requested_at as string) : "—"}</TableCell>
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

/* ── Shared Components ────────────────────────────────── */

function FlowCard({ icon: Icon, label, value, color }: { icon: typeof Users; label: string; value: string; color: string }) {
  const bgMap: Record<string, string> = {
    blue: "bg-blue-50 dark:bg-blue-950",
    purple: "bg-purple-50 dark:bg-purple-950",
    green: "bg-green-50 dark:bg-green-950",
  };
  const textMap: Record<string, string> = {
    blue: "text-blue-700 dark:text-blue-400",
    purple: "text-purple-700 dark:text-purple-400",
    green: "text-green-700 dark:text-green-400",
  };
  return (
    <div className={`rounded-lg ${bgMap[color]} p-4 text-center`}>
      <Icon className={`mx-auto h-6 w-6 ${textMap[color]}`} />
      <p className={`mt-1 text-sm font-semibold ${textMap[color]}`}>{label}</p>
      <p className="mt-0.5 text-xs text-bos-silver-dark">{value}</p>
    </div>
  );
}

function FlowArrow() {
  return (
    <div className="hidden sm:flex items-center justify-center">
      <ArrowUpRight className="h-5 w-5 text-bos-silver-dark rotate-45" />
    </div>
  );
}
