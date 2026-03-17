"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Card, CardContent } from "@/components/ui";
import { getCombos, getPromos } from "@/lib/api/saas";
import { getAgents } from "@/lib/api/agents";
import {
  Users,
  Clock,
  UserCheck,
  Tag,
  Layers,
  TrendingUp,
  Plus,
  UserPlus,
  ArrowRight,
  DollarSign,
} from "lucide-react";

export default function PlatformDashboardPage() {
  const combos = useQuery({ queryKey: ["saas", "combos"], queryFn: getCombos });
  const promos = useQuery({ queryKey: ["saas", "promos"], queryFn: getPromos });
  const agents = useQuery({ queryKey: ["saas", "agents"], queryFn: () => getAgents() });

  const activeCombos = combos.data?.data?.filter((c: { status: string }) => c.status === "ACTIVE")?.length ?? "—";
  const activePromos = promos.data?.data?.filter((p: { status: string }) => p.status === "ACTIVE")?.length ?? "—";
  const allAgents = agents.data?.data ?? [];
  const activeAgents = allAgents.filter((a: { status: string }) => a.status === "ACTIVE" || a.status === "PROBATION")?.length ?? "—";
  const globalAgents = allAgents.filter((a: { agent_type: string; status: string }) => a.agent_type === "GLOBAL" && (a.status === "ACTIVE" || a.status === "PROBATION"))?.length ?? "—";
  const regionalAgents = allAgents.filter((a: { agent_type: string; status: string }) => a.agent_type === "REGIONAL" && (a.status === "ACTIVE" || a.status === "PROBATION"))?.length ?? "—";

  return (
    <div>
      <PageHeader
        title="Platform Dashboard"
        description="Overview of BOS platform status and key metrics"
      />

      {/* Stat Cards Row 1 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Active Tenants"
          value="—"
          icon={Users}
          description="Needs summary endpoint"
        />
        <StatCard
          title="Tenants on Trial"
          value="—"
          icon={Clock}
          description="Needs summary endpoint"
        />
        <StatCard
          title="Active Agents"
          value={activeAgents}
          icon={UserCheck}
          description={`${globalAgents} global, ${regionalAgents} regional`}
        />
        <StatCard
          title="Active Promotions"
          value={activePromos}
          icon={Tag}
        />
      </div>

      {/* Stat Cards Row 2 */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Engine Combos"
          value={activeCombos}
          icon={Layers}
        />
        <StatCard
          title="Pending Payouts"
          value="—"
          icon={DollarSign}
          description="Agent commission payouts"
        />
        <StatCard
          title="Monthly Revenue"
          value="—"
          icon={TrendingUp}
          description="Estimated from active subs"
        />
        <StatCard
          title="Trial Conversion"
          value="—"
          icon={TrendingUp}
          description="Converted / total trials"
        />
      </div>

      {/* Quick Actions */}
      <h2 className="mt-8 mb-4 text-lg font-semibold">Quick Actions</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickActionCard
          title="Register New Agent"
          description="Register a new Global Agent for tenant acquisition"
          href="/platform/agents"
          icon={UserPlus}
        />
        <QuickActionCard
          title="Create Promotion"
          description="Create a new promo code to attract customers"
          href="/platform/promotions"
          icon={Tag}
        />
        <QuickActionCard
          title="Define New Combo"
          description="Create a new engine combo package for tenants"
          href="/platform/combos"
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
