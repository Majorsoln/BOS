"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { getAgentDashboard, getMyTenants } from "@/lib/api/agents";
import {
  Users, Clock, DollarSign, TrendingUp, UserPlus, BarChart3, Percent, AlertCircle,
} from "lucide-react";

export default function AgentDashboardPage() {
  const dash = useQuery({ queryKey: ["agent", "dashboard"], queryFn: getAgentDashboard });
  const tenants = useQuery({ queryKey: ["agent", "tenants"], queryFn: () => getMyTenants() });

  const d = dash.data?.data ?? {};
  const tenantList = tenants.data?.data ?? [];
  const activeCount = tenantList.filter((t: { status: string }) => t.status === "ACTIVE" || t.status === "TRIAL").length;
  const trialCount = tenantList.filter((t: { status: string }) => t.status === "TRIAL").length;

  return (
    <div>
      <PageHeader
        title="Agent Dashboard"
        description="Your tenants, revenue, and performance overview"
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="My Total Tenants"
          value={d.total_tenants ?? tenantList.length ?? "—"}
          icon={Users}
        />
        <StatCard
          title="Active Tenants"
          value={d.active_tenants ?? activeCount ?? "—"}
          icon={UserPlus}
        />
        <StatCard
          title="Tenants on Trial"
          value={d.trial_tenants ?? trialCount ?? "—"}
          icon={Clock}
        />
        <StatCard
          title="Commission Rate"
          value={d.commission_rate ? `${d.commission_rate}%` : "—"}
          icon={Percent}
          description="Based on tenant volume"
        />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="This Month Revenue"
          value={d.month_revenue ?? "—"}
          icon={DollarSign}
          description="Total tenant payments"
        />
        <StatCard
          title="My Commission"
          value={d.month_commission ?? "—"}
          icon={TrendingUp}
          description="Earned this month"
        />
        <StatCard
          title="Pending Payout"
          value={d.pending_payout ?? "—"}
          icon={DollarSign}
          description="Accrued, not yet paid"
        />
        <StatCard
          title="Trial Conversion"
          value={d.conversion_rate ?? "—"}
          icon={BarChart3}
          description="Converted / expired"
        />
      </div>

      {/* Notifications placeholder */}
      <div className="mt-8">
        <h2 className="mb-3 text-lg font-semibold">Notifications</h2>
        <div className="rounded-lg border border-bos-silver/20 bg-bos-silver-light p-6 text-center text-sm text-bos-silver-dark dark:bg-neutral-900">
          <AlertCircle className="mx-auto mb-2 h-5 w-5" />
          No new notifications
        </div>
      </div>
    </div>
  );
}
