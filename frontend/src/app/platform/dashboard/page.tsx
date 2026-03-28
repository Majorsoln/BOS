"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Card, CardContent } from "@/components/ui";
import { getPromos, getSubscriptions } from "@/lib/api/saas";
import { getAgents } from "@/lib/api/agents";
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
} from "lucide-react";

export default function PlatformDashboardPage() {
  const promos = useQuery({ queryKey: ["saas", "promos"], queryFn: getPromos });
  const agents = useQuery({ queryKey: ["saas", "agents"], queryFn: () => getAgents() });
  const subs = useQuery({ queryKey: ["saas", "subscriptions"], queryFn: () => getSubscriptions() });

  const activePromos = promos.data?.data?.filter((p: { status: string }) => p.status === "ACTIVE")?.length ?? "—";
  const allAgents = agents.data?.data ?? [];
  const rlaAgents = allAgents.filter((a: { agent_type: string; status: string }) => a.agent_type === "REGION_LICENSE_AGENT" && (a.status === "ACTIVE" || a.status === "PROBATION"))?.length ?? 0;
  const remoteAgents = allAgents.filter((a: { agent_type: string; status: string }) => a.agent_type === "REMOTE_AGENT" && (a.status === "ACTIVE" || a.status === "PROBATION"))?.length ?? 0;
  const activeAgents = rlaAgents + remoteAgents;

  const allSubs = subs.data?.data ?? [];
  const activeTenants = allSubs.filter((s: { status: string }) => s.status === "ACTIVE")?.length ?? "—";
  const trialTenants = allSubs.filter((s: { status: string }) => s.status === "TRIAL")?.length ?? "—";

  return (
    <div>
      <PageHeader
        title="Platform Dashboard"
        description="Overview of BOS platform status and key metrics"
      />

      {/* Key Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Active Tenants" value={activeTenants} icon={Users} description="Paying subscribers" />
        <StatCard title="Tenants on Trial" value={trialTenants} icon={Clock} description="Free trial period" />
        <StatCard
          title="Active Agents"
          value={activeAgents}
          icon={UserCheck}
          description={`${rlaAgents} RLA, ${remoteAgents} remote`}
        />
        <StatCard title="Active Promotions" value={activePromos} icon={Tag} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Services" value="5" icon={Package} description="Retail, Restaurant, Hotel, Workshop, HR" />
        <StatCard title="Pending Payouts" value="—" icon={DollarSign} description="Agent commission payouts" />
        <StatCard title="Monthly Revenue" value="—" icon={TrendingUp} description="Estimated from active subs" />
        <StatCard title="Trial Conversion" value="—" icon={TrendingUp} description="Converted / total trials" />
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
          description="Immutable evidence trail for all compliance decisions"
          href="/platform/governance/audit"
          icon={Scale}
        />
      </div>

      {/* Agents */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Agent Management</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickActionCard
          title="Region License Agents"
          description="Appoint RLA with market share, license, discount limits"
          href="/platform/agents/rla"
          icon={Shield}
        />
        <QuickActionCard
          title="Remote Agents"
          description="Sell in any region with an active RLA, earn commission"
          href="/platform/agents/remote"
          icon={UserCheck}
        />
        <QuickActionCard
          title="Performance"
          description="Cross-agent leaderboard and performance metrics"
          href="/platform/agents/performance"
          icon={BarChart3}
        />
        <QuickActionCard
          title="Commissions & Payouts"
          description="Commission settings and payout approvals"
          href="/platform/agents/payouts"
          icon={DollarSign}
        />
        <QuickActionCard
          title="Escalations"
          description="Issues escalated from agents requiring resolution"
          href="/platform/agents/escalations"
          icon={AlertTriangle}
        />
      </div>

      {/* Pricing & Billing */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Pricing & Billing</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
          description="Manage trial agreements, subscriptions, and trial policy"
          href="/platform/subscriptions"
          icon={Briefcase}
        />
      </div>

      {/* Audit & Monitoring */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Audit & Monitoring</h2>
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
          title="Platform Promotions"
          description="Create and manage promo codes"
          href="/platform/promotions"
          icon={Tag}
        />
      </div>

      {/* Tenants */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Tenants</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
