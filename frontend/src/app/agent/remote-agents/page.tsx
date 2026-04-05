"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, CardHeader, CardTitle, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getAgents } from "@/lib/api/agents";
import { UserCheck, Users, TrendingUp, DollarSign, Award } from "lucide-react";

export default function RemoteAgentsPage() {
  // TODO: Filter by current RLA's region from auth context
  const agentsQuery = useQuery({
    queryKey: ["agent", "remote-agents"],
    queryFn: () => getAgents({ type: "REMOTE_AGENT" }),
  });

  type Agent = {
    agent_id: string; agent_name: string; status: string; tier: string;
    commission_rate?: string; tenant_count?: number; active_tenant_count?: number;
    total_commission_earned?: string; pending_commission?: string;
    contact_email?: string; contact_phone?: string;
    region_codes?: string[];
  };

  const agents: Agent[] = agentsQuery.data?.data ?? [];
  const active = agents.filter((a) => a.status === "ACTIVE" || a.status === "PROBATION");
  const totalTenants = agents.reduce((s, a) => s + (a.active_tenant_count ?? a.tenant_count ?? 0), 0);
  const totalEarned = agents.reduce((s, a) => s + parseFloat(a.total_commission_earned || "0"), 0);

  return (
    <div>
      <PageHeader
        title="Remote Agents"
        description="Remote agents selling BOS subscriptions in your region. You earn from their sales too."
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Total Agents" value={agents.length} icon={UserCheck} />
        <StatCard title="Active Agents" value={active.length} icon={UserCheck} description="Active or on probation" />
        <StatCard title="Tenants via Agents" value={totalTenants} icon={Users} />
        <StatCard title="Agent Commissions" value={totalEarned.toLocaleString()} icon={DollarSign} />
      </div>

      {/* Agent Doctrine */}
      <Card className="mt-4 border-blue-200/50 bg-blue-50/30 dark:border-blue-800/30 dark:bg-blue-950/20">
        <CardContent className="pt-6">
          <p className="text-sm text-blue-700 dark:text-blue-400">
            <strong>How Remote Agents work:</strong> They sell BOS subscriptions in your region.
            You receive your market share on every sale they make. They earn their commission.
            BOS calculates the distribution for every sale automatically.
          </p>
        </CardContent>
      </Card>

      {/* Agents Table */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-sm">All Remote Agents ({agents.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {agents.length === 0 ? (
            <EmptyState title="No remote agents" description="Remote agents operating in your region will appear here" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead className="text-center">Tier</TableHead>
                  <TableHead className="text-center">Commission</TableHead>
                  <TableHead className="text-center">Tenants</TableHead>
                  <TableHead className="text-right">Earned</TableHead>
                  <TableHead className="text-right">Pending</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.map((a) => (
                  <TableRow key={a.agent_id}>
                    <TableCell className="font-medium">{a.agent_name}</TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{a.contact_email || "—"}</TableCell>
                    <TableCell className="text-center">
                      <Badge variant={a.tier === "GOLD" ? "warning" : a.tier === "SILVER" ? "purple" : "outline"}>
                        {a.tier}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center font-mono">
                      {a.commission_rate ? `${(parseFloat(a.commission_rate) * 100).toFixed(0)}%` : "—"}
                    </TableCell>
                    <TableCell className="text-center font-mono">{a.active_tenant_count ?? a.tenant_count ?? 0}</TableCell>
                    <TableCell className="text-right font-mono text-green-600">
                      {parseFloat(a.total_commission_earned || "0").toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {parseFloat(a.pending_commission || "0") > 0 ? (
                        <span className="text-amber-600">{parseFloat(a.pending_commission || "0").toLocaleString()}</span>
                      ) : "0"}
                    </TableCell>
                    <TableCell className="text-center"><StatusBadge status={a.status} /></TableCell>
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
