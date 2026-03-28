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
import {
  Users, TrendingUp, Award, BarChart3, Shield, UserCheck, DollarSign,
} from "lucide-react";
import { StatusBadge } from "@/components/shared/status-badge";
import Link from "next/link";

export default function AgentPerformancePage() {
  const rlaQuery = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });
  const remoteQuery = useQuery({
    queryKey: ["saas", "agents", "REMOTE_AGENT"],
    queryFn: () => getAgents({ type: "REMOTE_AGENT" }),
  });
  const resellerQuery = useQuery({
    queryKey: ["saas", "agents", "RESELLER"],
    queryFn: () => getAgents({ type: "RESELLER" }),
  });

  type AgentRow = {
    agent_id: string; agent_name: string; agent_type: string;
    status: string; active_tenant_count: number; commission_rate: string;
    total_commission_earned: string; pending_commission: string;
    territory?: string; region_codes: string[]; tier: string;
  };

  const rlas: AgentRow[] = rlaQuery.data?.data ?? [];
  const remotes: AgentRow[] = remoteQuery.data?.data ?? [];
  const resellers: AgentRow[] = resellerQuery.data?.data ?? [];
  const allAgents = [...rlas, ...remotes, ...resellers];
  const activeAgents = allAgents.filter((a) => a.status === "ACTIVE" || a.status === "PROBATION");

  const totalTenants = activeAgents.reduce((s, a) => s + (a.active_tenant_count || 0), 0);
  const totalEarned = allAgents.reduce((s, a) => s + parseFloat(a.total_commission_earned || "0"), 0);
  const totalPending = allAgents.reduce((s, a) => s + parseFloat(a.pending_commission || "0"), 0);

  // Sort all agents by tenant count descending for leaderboard
  const leaderboard = [...activeAgents].sort((a, b) => (b.active_tenant_count || 0) - (a.active_tenant_count || 0));

  const agentTypeLabel = (t: string) =>
    t === "REGION_LICENSE_AGENT" ? "RLA" :
    t === "REMOTE_AGENT" ? "Remote" : "Reseller";

  const agentTypeColor = (t: string) =>
    t === "REGION_LICENSE_AGENT" ? "purple" :
    t === "REMOTE_AGENT" ? "success" : "warning";

  return (
    <div>
      <PageHeader
        title="Agent Performance"
        description="Cross-agent performance metrics, leaderboard, and health indicators"
      />

      {/* Summary Stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active Agents" value={activeAgents.length} icon={Users} description={`${rlas.filter(a => a.status === "ACTIVE").length} RLA, ${remotes.filter(a => a.status === "ACTIVE").length} Remote, ${resellers.filter(a => a.status === "ACTIVE").length} Reseller`} />
        <StatCard title="Total Tenants" value={totalTenants} icon={TrendingUp} description="Across all agents" />
        <StatCard title="Total Earned" value={totalEarned.toLocaleString()} icon={DollarSign} description="All-time commissions" />
        <StatCard title="Pending Payouts" value={totalPending.toLocaleString()} icon={DollarSign} description="Awaiting disbursement" />
      </div>

      {/* Agent Type Breakdown */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-sm"><Shield className="h-4 w-4 text-purple-600" /> Region License Agents</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-bos-silver-dark">Active</span><span className="font-mono">{rlas.filter(a => a.status === "ACTIVE").length}</span></div>
              <div className="flex justify-between"><span className="text-bos-silver-dark">Total Tenants</span><span className="font-mono">{rlas.reduce((s, a) => s + (a.active_tenant_count || 0), 0)}</span></div>
              <div className="flex justify-between"><span className="text-bos-silver-dark">Revenue Collected</span><span className="font-mono">{rlas.reduce((s, a) => s + parseFloat(a.total_commission_earned || "0"), 0).toLocaleString()}</span></div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-sm"><UserCheck className="h-4 w-4 text-green-600" /> Remote Agents</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-bos-silver-dark">Active</span><span className="font-mono">{remotes.filter(a => a.status === "ACTIVE").length}</span></div>
              <div className="flex justify-between"><span className="text-bos-silver-dark">Total Tenants</span><span className="font-mono">{remotes.reduce((s, a) => s + (a.active_tenant_count || 0), 0)}</span></div>
              <div className="flex justify-between"><span className="text-bos-silver-dark">Commission Earned</span><span className="font-mono">{remotes.reduce((s, a) => s + parseFloat(a.total_commission_earned || "0"), 0).toLocaleString()}</span></div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-sm"><Award className="h-4 w-4 text-amber-600" /> Resellers (Wakala)</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-bos-silver-dark">Active</span><span className="font-mono">{resellers.filter(a => a.status === "ACTIVE").length}</span></div>
              <div className="flex justify-between"><span className="text-bos-silver-dark">Total Tenants</span><span className="font-mono">{resellers.reduce((s, a) => s + (a.active_tenant_count || 0), 0)}</span></div>
              <div className="flex justify-between"><span className="text-bos-silver-dark">Commission Earned</span><span className="font-mono">{resellers.reduce((s, a) => s + parseFloat(a.total_commission_earned || "0"), 0).toLocaleString()}</span></div>
              <div className="flex justify-between">
                <span className="text-bos-silver-dark">Tier Split</span>
                <span className="flex gap-1">
                  <Badge variant="outline" className="text-xs">{resellers.filter(a => a.tier === "BRONZE").length} B</Badge>
                  <Badge variant="outline" className="text-xs">{resellers.filter(a => a.tier === "SILVER").length} S</Badge>
                  <Badge variant="warning" className="text-xs">{resellers.filter(a => a.tier === "GOLD").length} G</Badge>
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Leaderboard */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" /> Agent Leaderboard
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {leaderboard.length === 0 ? (
            <EmptyState title="No active agents" description="Register agents to see the leaderboard" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Region</TableHead>
                  <TableHead className="text-center">Tenants</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Commission Rate</TableHead>
                  <TableHead className="text-right">Total Earned</TableHead>
                  <TableHead className="text-right">Pending</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leaderboard.slice(0, 25).map((a, i) => (
                  <TableRow key={a.agent_id}>
                    <TableCell className="font-mono text-bos-silver-dark">
                      {i < 3 ? (
                        <span className={`font-bold ${i === 0 ? "text-amber-500" : i === 1 ? "text-gray-400" : "text-amber-700"}`}>
                          {i + 1}
                        </span>
                      ) : i + 1}
                    </TableCell>
                    <TableCell>
                      <Link href={`/platform/agents/${a.agent_id}`} className="font-medium text-bos-purple hover:underline">
                        {a.agent_name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant={agentTypeColor(a.agent_type) as "purple" | "success" | "warning"}>
                        {agentTypeLabel(a.agent_type)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {a.territory ? (
                          <Badge variant="outline">{a.territory}</Badge>
                        ) : (a.region_codes ?? []).length > 0 ? (
                          a.region_codes.slice(0, 3).map((rc) => (
                            <Badge key={rc} variant="outline" className="text-xs">{rc}</Badge>
                          ))
                        ) : (
                          <span className="text-xs text-bos-silver-dark">All</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-center font-mono">{a.active_tenant_count || 0}</TableCell>
                    <TableCell className="text-center"><StatusBadge status={a.status} /></TableCell>
                    <TableCell className="text-right font-mono">{(parseFloat(a.commission_rate || "0") * 100).toFixed(0)}%</TableCell>
                    <TableCell className="text-right font-mono text-sm">{parseFloat(a.total_commission_earned || "0").toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{parseFloat(a.pending_commission || "0").toLocaleString()}</TableCell>
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
