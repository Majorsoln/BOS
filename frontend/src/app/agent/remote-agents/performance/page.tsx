"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, CardHeader, CardTitle, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getAgents } from "@/lib/api/agents";
import { Award, TrendingUp, Users, BarChart3 } from "lucide-react";

export default function AgentPerformancePage() {
  const agentsQuery = useQuery({
    queryKey: ["agent", "remote-agents"],
    queryFn: () => getAgents({ type: "REMOTE_AGENT" }),
  });

  type Agent = {
    agent_id: string; agent_name: string; tier: string; status: string;
    active_tenant_count?: number; tenant_count?: number;
    total_commission_earned?: string;
  };

  const agents: Agent[] = (agentsQuery.data?.data ?? [])
    .filter((a: Agent) => a.status === "ACTIVE" || a.status === "PROBATION")
    .sort((a: Agent, b: Agent) =>
      (b.active_tenant_count ?? b.tenant_count ?? 0) - (a.active_tenant_count ?? a.tenant_count ?? 0)
    );

  const topAgent = agents[0];
  const avgTenants = agents.length > 0
    ? Math.round(agents.reduce((s, a) => s + (a.active_tenant_count ?? a.tenant_count ?? 0), 0) / agents.length)
    : 0;

  return (
    <div>
      <PageHeader
        title="Agent Performance — Utendaji wa Mawakala"
        description="Leaderboard and metrics for remote agents in your region."
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Top Agent" value={topAgent?.agent_name ?? "—"} icon={Award} />
        <StatCard title="Active Agents" value={agents.length} icon={Users} />
        <StatCard title="Avg Tenants/Agent" value={avgTenants} icon={BarChart3} />
        <StatCard title="Total Agent Revenue" value={
          agents.reduce((s, a) => s + parseFloat(a.total_commission_earned || "0"), 0).toLocaleString()
        } icon={TrendingUp} />
      </div>

      <Card className="mt-6">
        <CardHeader><CardTitle className="text-sm">Leaderboard — Bao la Utendaji</CardTitle></CardHeader>
        <CardContent className="p-0">
          {agents.length === 0 ? (
            <EmptyState title="No agents" description="Agent performance data will appear here" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead className="text-center">Tier</TableHead>
                  <TableHead className="text-center">Tenants</TableHead>
                  <TableHead className="text-right">Earned</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.map((a, i) => (
                  <TableRow key={a.agent_id}>
                    <TableCell className="font-bold text-bos-silver-dark">
                      {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i + 1}`}
                    </TableCell>
                    <TableCell className="font-medium">{a.agent_name}</TableCell>
                    <TableCell className="text-center">
                      <Badge variant={a.tier === "GOLD" ? "warning" : a.tier === "SILVER" ? "purple" : "outline"}>{a.tier}</Badge>
                    </TableCell>
                    <TableCell className="text-center font-mono">{a.active_tenant_count ?? a.tenant_count ?? 0}</TableCell>
                    <TableCell className="text-right font-mono text-green-600">
                      {parseFloat(a.total_commission_earned || "0").toLocaleString()}
                    </TableCell>
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
