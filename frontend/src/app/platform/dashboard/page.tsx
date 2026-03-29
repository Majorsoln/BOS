"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Card, CardContent, CardHeader, CardTitle, Badge } from "@/components/ui";
import { getPromos, getSubscriptions, getTrials, getLedgerSummary } from "@/lib/api/saas";
import { getAgents, getAgentPayouts } from "@/lib/api/agents";
import {
  Users,
  Clock,
  UserCheck,
  Tag,
  Package,
  TrendingUp,
  ArrowRight,
  DollarSign,
  FileText,
  Activity,
  Shield,
  AlertTriangle,
  Scale,
  MapPin,
  ShieldCheck,
  Briefcase,
  BarChart3,
  Eye,
  PiggyBank,
  CheckCircle,
  Settings,
} from "lucide-react";

export default function PlatformDashboardPage() {
  const promos = useQuery({ queryKey: ["saas", "promos"], queryFn: getPromos });
  const agents = useQuery({ queryKey: ["saas", "agents"], queryFn: () => getAgents() });
  const subs = useQuery({ queryKey: ["saas", "subscriptions"], queryFn: () => getSubscriptions() });
  const trials = useQuery({ queryKey: ["saas", "trials"], queryFn: () => getTrials({}) });
  const payouts = useQuery({ queryKey: ["saas", "agents", "payouts"], queryFn: () => getAgentPayouts({}) });
  const now = new Date();
  const currentPeriod = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const ledgerSummary = useQuery({ queryKey: ["saas", "ledger", "summary", currentPeriod], queryFn: () => getLedgerSummary(currentPeriod) });

  const activePromos = promos.data?.data?.filter((p: { status: string }) => p.status === "ACTIVE")?.length ?? 0;
  const allAgents = agents.data?.data ?? [];
  const rlaAgents = allAgents.filter((a: { agent_type: string; status: string }) => a.agent_type === "REGION_LICENSE_AGENT" && (a.status === "ACTIVE" || a.status === "PROBATION"))?.length ?? 0;
  const remoteAgents = allAgents.filter((a: { agent_type: string; status: string }) => a.agent_type === "REMOTE_AGENT" && (a.status === "ACTIVE" || a.status === "PROBATION"))?.length ?? 0;
  const activeAgents = rlaAgents + remoteAgents;

  const suspendedAgents = allAgents.filter((a: { status: string }) => a.status === "SUSPENDED")?.length ?? 0;
  const probationAgents = allAgents.filter((a: { status: string }) => a.status === "PROBATION")?.length ?? 0;

  const allSubs = subs.data?.data ?? [];
  const activeTenants = allSubs.filter((s: { status: string }) => s.status === "ACTIVE")?.length ?? 0;
  const trialTenants = allSubs.filter((s: { status: string }) => s.status === "TRIAL")?.length ?? 0;

  const allTrials = trials.data?.data ?? [];
  const convertedTrials = allTrials.filter((t: { status: string }) => t.status === "CONVERTED")?.length ?? 0;
  const totalTrials = allTrials.length;
  const conversionRate = totalTrials > 0 ? `${Math.round((convertedTrials / totalTrials) * 100)}%` : "—";

  const allPayouts: Array<Record<string, unknown>> = payouts.data?.data ?? [];
  const pendingPayoutCount = allPayouts.filter((p) => p.status === "PENDING").length;

  const summary = ledgerSummary.data?.data as Record<string, unknown> | undefined;
  const monthlyGross = (summary?.total_gross as number) ?? 0;
  const platformShare = (summary?.total_platform_share as number) ?? 0;

  return (
    <div>
      <PageHeader
        title="Platform Administration"
        description="Oversee operations, manage agents, set limits. Authorize, don't operate."
      />

      {/* Oversight Doctrine */}
      <Card className="mb-6 border-bos-purple/20 bg-bos-purple-light/30 dark:border-bos-purple/10 dark:bg-bos-purple-light/10">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Eye className="mt-0.5 h-5 w-5 text-bos-purple" />
            <div className="text-sm">
              <p className="font-semibold text-bos-purple">Platform Doctrine: Authorize, Don&apos;t Operate</p>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">Set Limits</p>
                  <p className="text-xs text-bos-silver-dark">Trial policy, discount caps, rate governance</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">Oversee Agents</p>
                  <p className="text-xs text-bos-silver-dark">Activity, health, service delivery, escalations</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">Intervene When Needed</p>
                  <p className="text-xs text-bos-silver-dark">Adjust contracts, extend trials, deactivate promos</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Paying Tenants" value={activeTenants} icon={Users} description="Active subscribers" />
        <StatCard title="Tenants on Trial" value={trialTenants} icon={Clock} description="Onboarded by agents" />
        <StatCard
          title="Active Agents"
          value={activeAgents}
          icon={UserCheck}
          description={`${rlaAgents} RLA, ${remoteAgents} remote`}
        />
        <StatCard title="Trial Conversion" value={conversionRate} icon={TrendingUp} description={`${convertedTrials}/${totalTrials} trials converted`} />
      </div>

      {/* Agent Health Alerts */}
      {(suspendedAgents > 0 || probationAgents > 0) && (
        <Card className="mt-4 border-amber-200 dark:border-amber-800">
          <CardContent className="flex items-center gap-4 p-4">
            <AlertTriangle className="h-5 w-5 text-amber-600" />
            <div className="flex-1 text-sm">
              {suspendedAgents > 0 && (
                <span className="mr-4">
                  <Badge variant="destructive">{suspendedAgents} suspended</Badge> agent{suspendedAgents > 1 ? "s" : ""} need attention
                </span>
              )}
              {probationAgents > 0 && (
                <span>
                  <Badge variant="gold">{probationAgents} on probation</Badge> — monitor onboarding progress
                </span>
              )}
            </div>
            <Link href="/platform/agents/activity" className="text-sm text-bos-purple hover:underline">View Activity</Link>
          </CardContent>
        </Card>
      )}

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Active Promotions" value={activePromos} icon={Tag} description="Created by agents" />
        <StatCard title="Services" value="5" icon={Package} description="Retail, Restaurant, Hotel, Workshop, HR" />
        <StatCard
          title="Pending Payouts"
          value={pendingPayoutCount > 0 ? pendingPayoutCount : "—"}
          icon={DollarSign}
          description={pendingPayoutCount > 0 ? (
            <Link href="/platform/finance/approvals" className="text-bos-purple hover:underline">Review &rarr;</Link>
          ) : "Agent commissions"}
        />
        <StatCard
          title="Monthly Revenue"
          value={monthlyGross > 0 ? monthlyGross.toLocaleString() : "—"}
          icon={TrendingUp}
          description={platformShare > 0 ? `Platform: ${platformShare.toLocaleString()}` : (
            <Link href="/platform/finance/ledger" className="text-bos-purple hover:underline">Revenue Ledger &rarr;</Link>
          )}
        />
      </div>

      {/* Agent Management */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Agent Management</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickActionCard
          title="Region License Agents"
          description="Appoint RLAs with market share, license, discount limits"
          href="/platform/agents/rla"
          icon={Shield}
        />
        <QuickActionCard
          title="Remote Agents"
          description="Sell in any region with active RLA, earn commission"
          href="/platform/agents/remote"
          icon={UserCheck}
        />
        <QuickActionCard
          title="Activity & Oversight"
          description="Agent business health, service delivery, contracts"
          href="/platform/agents/activity"
          icon={Eye}
        />
        <QuickActionCard
          title="Performance"
          description="Cross-agent leaderboard and metrics"
          href="/platform/agents/performance"
          icon={BarChart3}
        />
        <QuickActionCard
          title="Escalations"
          description="Issues from agents requiring platform resolution"
          href="/platform/agents/escalations"
          icon={AlertTriangle}
        />
      </div>

      {/* Finance */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Finance — Pesa Zote</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickActionCard
          title="Revenue & Collections"
          description="All revenue, RLA collections, projections, platform ledger"
          href="/platform/finance"
          icon={PiggyBank}
        />
        <QuickActionCard
          title="Revenue Ledger"
          description="Per-sale breakdown: gross, tax, fees, net, shares, settlement"
          href="/platform/finance/ledger"
          icon={FileText}
        />
        <QuickActionCard
          title="Payout Approvals"
          description="Approve or reject agent commission payout requests"
          href="/platform/finance/approvals"
          icon={CheckCircle}
        />
        <QuickActionCard
          title="Payment Rules"
          description="Commission tiers, settlement schedules, clawback, thresholds"
          href="/platform/finance/rules"
          icon={Settings}
        />
      </div>

      {/* Oversight & Limits */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Oversight & Limits</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <QuickActionCard
          title="Services & Pricing"
          description="Set rates per region — only regions with active RLAs"
          href="/platform/pricing"
          icon={Package}
        />
        <QuickActionCard
          title="Rate Governance"
          description="Rate change history and 90-day notice enforcement"
          href="/platform/rates"
          icon={Scale}
        />
        <QuickActionCard
          title="Trials & Subscriptions"
          description="Oversee all trials and subs — agents create, platform monitors"
          href="/platform/subscriptions"
          icon={Briefcase}
        />
        <QuickActionCard
          title="Promotions"
          description="Monitor agent promos — deactivate if policy violated"
          href="/platform/promotions"
          icon={Tag}
        />
      </div>

      {/* Regions & Compliance */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Regions & Compliance</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickActionCard
          title="Region Registry"
          description="Manage operational regions and their configuration"
          href="/platform/regions"
          icon={MapPin}
        />
        <QuickActionCard
          title="Compliance Packs"
          description="Tax rules, data retention, receipt requirements per region"
          href="/platform/compliance"
          icon={ShieldCheck}
        />
        <QuickActionCard
          title="Compliance Audit"
          description="Immutable evidence trail for compliance decisions"
          href="/platform/governance/audit"
          icon={Scale}
        />
      </div>

      {/* Audit & Tenants */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Audit & Tenants</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickActionCard
          title="Audit Log"
          description="Immutable platform audit trail"
          href="/platform/audit"
          icon={FileText}
        />
        <QuickActionCard
          title="System Health"
          description="SLO monitoring and breach alerts"
          href="/platform/health"
          icon={Activity}
        />
        <QuickActionCard
          title="All Tenants"
          description="Browse and manage all registered tenants"
          href="/platform/tenants"
          icon={Users}
        />
      </div>
    </div>
  );
}

function QuickActionCard({
  title,
  description,
  href,
  icon: Icon,
}: {
  title: string;
  description: string;
  href: string;
  icon: typeof Users;
}) {
  return (
    <Link href={href}>
      <Card className="group cursor-pointer transition-shadow hover:shadow-md">
        <CardContent className="p-5">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-bos-purple-light transition-colors group-hover:bg-bos-purple group-hover:text-white">
              <Icon className="h-5 w-5 text-bos-purple group-hover:text-white" />
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
