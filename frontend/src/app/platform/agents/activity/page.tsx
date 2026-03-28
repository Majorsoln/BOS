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
import { getAgents } from "@/lib/api/agents";
import { getTrials, getSubscriptions, getPromos } from "@/lib/api/saas";
import { REGIONS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import {
  Activity, Users, TrendingUp, AlertTriangle, Eye, Shield,
  UserCheck, Clock, DollarSign, Tag, BarChart3, CreditCard,
} from "lucide-react";

type TabKey = "health" | "service" | "contracts";

export default function AgentActivityPage() {
  const [tab, setTab] = useState<TabKey>("health");

  const tabs: { key: TabKey; label: string }[] = [
    { key: "health", label: "Business Health" },
    { key: "service", label: "Service Delivery" },
    { key: "contracts", label: "Contracts & Agreements" },
  ];

  return (
    <div>
      <PageHeader
        title="Agent Activity & Oversight"
        description="Everything agents do is reported here. Monitor business health, service delivery, and contract status."
      />

      {/* Doctrine */}
      <Card className="mb-6 border-blue-200/50 bg-blue-50/30 dark:border-blue-800/30 dark:bg-blue-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Eye className="mt-0.5 h-5 w-5 text-blue-600" />
            <div className="text-sm">
              <p className="font-semibold text-blue-700 dark:text-blue-400">Platform Oversight — Kila Kitu Kireportiwe</p>
              <ul className="mt-1 list-disc pl-4 text-neutral-600 dark:text-neutral-400 space-y-0.5">
                <li><strong>Business Health</strong> — how each agent&apos;s business is performing (tenants, revenue, growth)</li>
                <li><strong>Service Delivery</strong> — are agents supporting their tenants well? Escalations, response times</li>
                <li><strong>Contracts</strong> — all trial agreements, subscriptions, and promotions created by agents</li>
                <li><strong>Platform intervenes</strong> only when agents need support or violate policy</li>
              </ul>
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

      {tab === "health" && <HealthTab />}
      {tab === "service" && <ServiceTab />}
      {tab === "contracts" && <ContractsTab />}
    </div>
  );
}

/* ── Business Health Tab ──────────────────────────────── */

function HealthTab() {
  const rlaQuery = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });
  const remoteQuery = useQuery({
    queryKey: ["saas", "agents", "REMOTE_AGENT"],
    queryFn: () => getAgents({ type: "REMOTE_AGENT" }),
  });

  type AgentRow = {
    agent_id: string; agent_name: string; agent_type: string;
    status: string; tenant_count?: number; active_tenant_count?: number;
    total_commission_earned?: string; pending_commission?: string;
    territory?: string; tier?: string; market_share_pct?: number;
    license_number?: string;
  };

  const rlas: AgentRow[] = rlaQuery.data?.data ?? [];
  const remotes: AgentRow[] = remoteQuery.data?.data ?? [];
  const allAgents = [...rlas, ...remotes];
  const activeAgents = allAgents.filter((a) => a.status === "ACTIVE" || a.status === "PROBATION");

  const totalTenants = activeAgents.reduce((s, a) => s + (a.active_tenant_count ?? a.tenant_count ?? 0), 0);
  const totalEarned = allAgents.reduce((s, a) => s + parseFloat(a.total_commission_earned || "0"), 0);
  const totalPending = allAgents.reduce((s, a) => s + parseFloat(a.pending_commission || "0"), 0);

  // Agents with zero tenants (need attention)
  const zeroTenantAgents = activeAgents.filter((a) => (a.active_tenant_count ?? a.tenant_count ?? 0) === 0);

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active Agents" value={activeAgents.length} icon={Users} description={`${rlas.filter(a => a.status === "ACTIVE").length} RLA, ${remotes.filter(a => a.status === "ACTIVE" || a.status === "PROBATION").length} Remote`} />
        <StatCard title="Total Tenants" value={totalTenants} icon={TrendingUp} description="Across all agents" />
        <StatCard title="Commission Earned" value={totalEarned.toLocaleString()} icon={DollarSign} description="All-time" />
        <StatCard title="Needs Attention" value={zeroTenantAgents.length} icon={AlertTriangle} description="Zero tenants" />
      </div>

      {/* RLA Health */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Shield className="h-4 w-4 text-purple-600" /> Region License Agents — Business Health
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {rlas.length === 0 ? (
            <EmptyState title="No RLAs" description="Appoint Region License Agents first" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Region</TableHead>
                  <TableHead>License</TableHead>
                  <TableHead className="text-center">Market Share</TableHead>
                  <TableHead className="text-center">Tenants</TableHead>
                  <TableHead className="text-right">Earned</TableHead>
                  <TableHead className="text-right">Pending</TableHead>
                  <TableHead className="text-center">Health</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rlas.map((a) => {
                  const tenants = a.active_tenant_count ?? a.tenant_count ?? 0;
                  const health = tenants > 5 ? "HEALTHY" : tenants > 0 ? "GROWING" : "NEEDS_ATTENTION";
                  return (
                    <TableRow key={a.agent_id}>
                      <TableCell>
                        <Link href={`/platform/agents/${a.agent_id}`} className="font-medium text-bos-purple hover:underline">
                          {a.agent_name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{a.territory || "—"}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{a.license_number || "—"}</TableCell>
                      <TableCell className="text-center font-mono">{a.market_share_pct ?? "—"}%</TableCell>
                      <TableCell className="text-center font-mono">{tenants}</TableCell>
                      <TableCell className="text-right font-mono text-sm">{parseFloat(a.total_commission_earned || "0").toLocaleString()}</TableCell>
                      <TableCell className="text-right font-mono text-sm">{parseFloat(a.pending_commission || "0").toLocaleString()}</TableCell>
                      <TableCell className="text-center">
                        <Badge variant={health === "HEALTHY" ? "success" : health === "GROWING" ? "gold" : "destructive"}>
                          {health === "HEALTHY" ? "Healthy" : health === "GROWING" ? "Growing" : "Needs Attention"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Remote Agent Health */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <UserCheck className="h-4 w-4 text-green-600" /> Remote Agents — Business Health
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {remotes.length === 0 ? (
            <EmptyState title="No Remote Agents" description="Register remote agents to expand sales force" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-center">Tenants</TableHead>
                  <TableHead className="text-right">Earned</TableHead>
                  <TableHead className="text-right">Pending</TableHead>
                  <TableHead className="text-center">Health</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {remotes.map((a) => {
                  const tenants = a.active_tenant_count ?? a.tenant_count ?? 0;
                  const health = a.status === "PROBATION" ? (tenants >= 3 ? "ON_TRACK" : "AT_RISK") : tenants > 5 ? "HEALTHY" : tenants > 0 ? "GROWING" : "NEEDS_ATTENTION";
                  const healthLabel = health === "ON_TRACK" ? "On Track" : health === "AT_RISK" ? "At Risk" : health === "HEALTHY" ? "Healthy" : health === "GROWING" ? "Growing" : "Needs Attention";
                  const healthVariant = health === "ON_TRACK" || health === "HEALTHY" ? "success" : health === "GROWING" ? "gold" : "destructive";
                  return (
                    <TableRow key={a.agent_id}>
                      <TableCell>
                        <Link href={`/platform/agents/${a.agent_id}`} className="font-medium text-bos-purple hover:underline">
                          {a.agent_name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant={a.tier === "GOLD" ? "warning" : a.tier === "SILVER" ? "secondary" : "outline"}>
                          {a.tier || "BRONZE"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center"><StatusBadge status={a.status} /></TableCell>
                      <TableCell className="text-center font-mono">{tenants}</TableCell>
                      <TableCell className="text-right font-mono text-sm">{parseFloat(a.total_commission_earned || "0").toLocaleString()}</TableCell>
                      <TableCell className="text-right font-mono text-sm">{parseFloat(a.pending_commission || "0").toLocaleString()}</TableCell>
                      <TableCell className="text-center">
                        <Badge variant={healthVariant as "success" | "gold" | "destructive"}>{healthLabel}</Badge>
                      </TableCell>
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

/* ── Service Delivery Tab ─────────────────────────────── */

function ServiceTab() {
  const rlaQuery = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });
  const remoteQuery = useQuery({
    queryKey: ["saas", "agents", "REMOTE_AGENT"],
    queryFn: () => getAgents({ type: "REMOTE_AGENT" }),
  });

  const rlas: Array<Record<string, unknown>> = rlaQuery.data?.data ?? [];
  const remotes: Array<Record<string, unknown>> = remoteQuery.data?.data ?? [];
  const allAgents = [...rlas, ...remotes];
  const activeAgents = allAgents.filter((a) => a.status === "ACTIVE" || a.status === "PROBATION");

  // Service quality indicators
  const suspendedAgents = allAgents.filter((a) => a.status === "SUSPENDED");
  const probationAgents = allAgents.filter((a) => a.status === "PROBATION");

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active Agents" value={activeAgents.length} icon={UserCheck} description="Currently serving" />
        <StatCard title="On Probation" value={probationAgents.length} icon={Clock} description="Must onboard 5 tenants in 90 days" />
        <StatCard title="Suspended" value={suspendedAgents.length} icon={AlertTriangle} description="Operations frozen" />
        <StatCard title="Regions Covered" value={new Set(rlas.filter(a => a.status === "ACTIVE").map(a => a.territory)).size} icon={BarChart3} description="With active RLA" />
      </div>

      {/* Service quality per region */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Service Coverage by Region</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {rlas.length === 0 ? (
            <EmptyState title="No regions" description="Appoint RLAs to cover regions" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Region</TableHead>
                  <TableHead>RLA</TableHead>
                  <TableHead className="text-center">RLA Status</TableHead>
                  <TableHead className="text-center">Remote Agents</TableHead>
                  <TableHead className="text-center">Total Tenants</TableHead>
                  <TableHead className="text-center">Coverage</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rlas.map((rla) => {
                  const region = rla.territory as string;
                  const regionRemotes = remotes.filter((r) => {
                    const rcs = r.region_codes as string[] | undefined;
                    return rcs?.includes(region) || (r.territory === region);
                  });
                  const totalTenants = (rla.active_tenant_count as number ?? rla.tenant_count as number ?? 0) +
                    regionRemotes.reduce((s, r) => s + (r.active_tenant_count as number ?? r.tenant_count as number ?? 0), 0);
                  const regionInfo = REGIONS.find((r) => r.code === region);

                  return (
                    <TableRow key={rla.agent_id as string}>
                      <TableCell>
                        <div>
                          <span className="font-medium">{region}</span>
                          {regionInfo && <span className="ml-2 text-xs text-bos-silver-dark">{regionInfo.name}</span>}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Link href={`/platform/agents/${rla.agent_id as string}`} className="text-bos-purple hover:underline">
                          {rla.agent_name as string}
                        </Link>
                      </TableCell>
                      <TableCell className="text-center"><StatusBadge status={rla.status as string} /></TableCell>
                      <TableCell className="text-center font-mono">{regionRemotes.length}</TableCell>
                      <TableCell className="text-center font-mono">{totalTenants}</TableCell>
                      <TableCell className="text-center">
                        <Badge variant={rla.status === "ACTIVE" ? (totalTenants > 0 ? "success" : "gold") : "destructive"}>
                          {rla.status === "ACTIVE" ? (totalTenants > 0 ? "Active" : "No Tenants") : "Inactive"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Agents needing support */}
      {(suspendedAgents.length > 0 || probationAgents.length > 0) && (
        <Card className="border-amber-200 dark:border-amber-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400">
              <AlertTriangle className="h-4 w-4" /> Agents Needing Support
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {probationAgents.map((a) => (
                <div key={a.agent_id as string} className="flex items-center justify-between rounded-lg border p-3 text-sm">
                  <div>
                    <Link href={`/platform/agents/${a.agent_id as string}`} className="font-medium text-bos-purple hover:underline">
                      {a.agent_name as string}
                    </Link>
                    <p className="text-xs text-bos-silver-dark">On probation — needs 5 tenants in 90 days</p>
                  </div>
                  <Badge variant="gold">PROBATION</Badge>
                </div>
              ))}
              {suspendedAgents.map((a) => (
                <div key={a.agent_id as string} className="flex items-center justify-between rounded-lg border border-red-200 p-3 text-sm dark:border-red-800">
                  <div>
                    <Link href={`/platform/agents/${a.agent_id as string}`} className="font-medium text-bos-purple hover:underline">
                      {a.agent_name as string}
                    </Link>
                    <p className="text-xs text-red-600">Suspended — operations frozen</p>
                  </div>
                  <Badge variant="destructive">SUSPENDED</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ── Contracts & Agreements Tab ───────────────────────── */

function ContractsTab() {
  const [statusFilter, setStatusFilter] = useState("");

  const trials = useQuery({
    queryKey: ["saas", "trials", "all"],
    queryFn: () => getTrials({ status: undefined }),
  });
  const subs = useQuery({
    queryKey: ["saas", "subscriptions", "all"],
    queryFn: () => getSubscriptions({ status: undefined }),
  });
  const promos = useQuery({
    queryKey: ["saas", "promos"],
    queryFn: getPromos,
  });

  const trialList: Array<Record<string, unknown>> = trials.data?.data ?? [];
  const subList: Array<Record<string, unknown>> = subs.data?.data ?? [];
  const promoList: Array<Record<string, unknown>> = promos.data?.data ?? [];

  const activeTrials = trialList.filter((t) => t.status === "ACTIVE").length;
  const activeSubs = subList.filter((s) => s.status === "ACTIVE").length;
  const activePromos = promoList.filter((p) => p.status === "ACTIVE").length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <StatCard title="Active Trials" value={activeTrials} icon={Clock} description={`${trialList.length} total`} />
        <StatCard title="Active Subscriptions" value={activeSubs} icon={CreditCard} description={`${subList.length} total`} />
        <StatCard title="Active Promotions" value={activePromos} icon={Tag} description={`${promoList.length} total`} />
      </div>

      {/* All trial agreements */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Trial Agreements (Created by Agents)</CardTitle>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-36">
              <option value="">All</option>
              <option value="ACTIVE">Active</option>
              <option value="CONVERTED">Converted</option>
              <option value="EXPIRED">Expired</option>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {trialList.length === 0 ? (
            <EmptyState title="No trial agreements" description="Agreements appear when agents onboard tenants" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Business</TableHead>
                  <TableHead>Days</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Rate</TableHead>
                  <TableHead>Promo</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(statusFilter ? trialList.filter((t) => t.status === statusFilter) : trialList).map((t, i) => {
                  const rate = t.rate_snapshot as Record<string, unknown> | undefined;
                  return (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-xs">{(t.business_id as string)?.slice(0, 12)}...</TableCell>
                      <TableCell className="font-mono">
                        {t.trial_days as number}
                        {(t.bonus_days as number) > 0 && <span className="text-green-600"> +{t.bonus_days as number}</span>}
                      </TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">
                        {formatDate(t.trial_starts_at as string)} — {formatDate(t.trial_ends_at as string)}
                      </TableCell>
                      <TableCell className="text-xs font-mono">
                        {rate ? `${rate.currency} ${Number(rate.monthly_amount).toLocaleString()}` : "—"}
                      </TableCell>
                      <TableCell>
                        {t.promo_code ? <Badge variant="gold">{t.promo_code as string}</Badge> : "—"}
                      </TableCell>
                      <TableCell className="text-center"><StatusBadge status={t.status as string} /></TableCell>
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
