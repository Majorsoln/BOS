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
  Plus,
  UserPlus,
  ArrowRight,
  DollarSign,
  FileText,
  Activity,
  ClipboardCheck,
  BadgeCheck,
  Shield,
  AlertTriangle,
  Scale,
} from "lucide-react";

export default function PlatformDashboardPage() {
  const promos = useQuery({ queryKey: ["saas", "promos"], queryFn: getPromos });
  const agents = useQuery({ queryKey: ["saas", "agents"], queryFn: () => getAgents() });
  const subs = useQuery({ queryKey: ["saas", "subscriptions"], queryFn: () => getSubscriptions() });

  const activePromos = promos.data?.data?.filter((p: { status: string }) => p.status === "ACTIVE")?.length ?? "—";
  const allAgents = agents.data?.data ?? [];
  const activeAgents = allAgents.filter((a: { status: string }) => a.status === "ACTIVE" || a.status === "PROBATION")?.length ?? "—";
  const globalAgents = allAgents.filter((a: { agent_type: string; status: string }) => a.agent_type === "GLOBAL" && (a.status === "ACTIVE" || a.status === "PROBATION"))?.length ?? 0;
  const regionalAgents = allAgents.filter((a: { agent_type: string; status: string }) => a.agent_type === "REGIONAL" && (a.status === "ACTIVE" || a.status === "PROBATION"))?.length ?? 0;

  const allSubs = subs.data?.data ?? [];
  const activeTenants = allSubs.filter((s: { status: string }) => s.status === "ACTIVE")?.length ?? "—";
  const trialTenants = allSubs.filter((s: { status: string }) => s.status === "TRIAL")?.length ?? "—";

  return (
    <div>
      <PageHeader
        title="Platform Dashboard"
        description="Overview of BOS platform status and key metrics"
      />

      {/* Row 1 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Active Tenants" value={activeTenants} icon={Users} description="Paying subscribers" />
        <StatCard title="Tenants on Trial" value={trialTenants} icon={Clock} description="Free trial period" />
        <StatCard
          title="Active Agents"
          value={activeAgents}
          icon={UserCheck}
          description={`${globalAgents} global, ${regionalAgents} regional`}
        />
        <StatCard title="Active Promotions" value={activePromos} icon={Tag} />
      </div>

      {/* Row 2 */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Services" value="5" icon={Package} description="Retail, Restaurant, Hotel, Workshop, HR" />
        <StatCard title="Pending Payouts" value="—" icon={DollarSign} description="Agent commission payouts" />
        <StatCard title="Monthly Revenue" value="—" icon={TrendingUp} description="Estimated from active subs" />
        <StatCard title="Trial Conversion" value="—" icon={TrendingUp} description="Converted / total trials" />
      </div>

      {/* ACMV Quick Actions */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Audit, Compliance, Monitoring & Verification</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <QuickActionCard
          title="Audit Log"
          description="View immutable platform audit trail"
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
          title="Review Queue"
          description="Pending compliance profiles to review"
          href="/platform/reviews"
          icon={ClipboardCheck}
        />
        <QuickActionCard
          title="Verification"
          description="Verification rates and bottleneck metrics"
          href="/platform/verification"
          icon={BadgeCheck}
        />
      </div>

      {/* Governance */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Governance</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickActionCard
          title="Region Agents"
          description="Two-level governance: delegate compliance to region agents"
          href="/platform/governance/agents"
          icon={Shield}
        />
        <QuickActionCard
          title="Escalations"
          description="Issues escalated from Region Agents requiring resolution"
          href="/platform/governance/escalations"
          icon={AlertTriangle}
        />
        <QuickActionCard
          title="Compliance Audit"
          description="Immutable evidence trail for all compliance decisions"
          href="/platform/governance/audit"
          icon={Scale}
        />
      </div>

      {/* Quick Actions */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Quick Actions</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickActionCard
          title="Manage Service Pricing"
          description="Set or update monthly rates for BOS services per region"
          href="/platform/services"
          icon={Package}
        />
        <QuickActionCard
          title="Register New Agent"
          description="Register a new agent for tenant acquisition"
          href="/platform/agents"
          icon={UserPlus}
        />
        <QuickActionCard
          title="Create Promotion"
          description="Create a promo code for tenants"
          href="/platform/promotions"
          icon={Plus}
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
  icon: typeof Plus;
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
