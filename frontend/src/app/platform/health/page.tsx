"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui";
import { getHealthSLOs, getHealthBreaches, getHealthSummary, takeHealthSnapshot } from "@/lib/api/platform";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle,
  RefreshCw,
  Camera,
  Shield,
  Zap,
  Clock,
  Database,
  Wifi,
} from "lucide-react";

const STATUS_CONFIG: Record<string, { color: string; icon: typeof CheckCircle; badge: "success" | "warning" | "destructive" | "secondary" }> = {
  OK: { color: "text-green-600", icon: CheckCircle, badge: "success" },
  WARNING: { color: "text-orange-500", icon: AlertTriangle, badge: "warning" },
  BREACHED: { color: "text-red-600", icon: XCircle, badge: "destructive" },
  UNKNOWN: { color: "text-neutral-400", icon: HelpCircle, badge: "secondary" },
};

const SLO_ICONS: Record<string, typeof Activity> = {
  "persist_event.success_rate": Database,
  "hash_chain.integrity_violations": Shield,
  "command_latency.p95_ms": Zap,
  "command_latency.p99_ms": Clock,
  "api.error_rate_5xx": Wifi,
  "replay.duration_seconds": RefreshCw,
};

interface SLOEntry {
  slo_id: string;
  name: string;
  metric_name: string;
  threshold: number;
  warning_threshold: number | null;
  comparison: string;
  unit: string;
  status: string;
  current_value: number | null;
  last_recorded: string | null;
}

interface Breach {
  breach_id: string;
  slo_id: string;
  metric_name: string;
  observed_value: number;
  threshold: number;
  region_code: string | null;
  tenant_id: string | null;
  breached_at: string;
}

export default function PlatformHealthPage() {
  const queryClient = useQueryClient();

  const slosQuery = useQuery({
    queryKey: ["platform", "health", "slos"],
    queryFn: getHealthSLOs,
    refetchInterval: 30_000,
  });

  const breachesQuery = useQuery({
    queryKey: ["platform", "health", "breaches"],
    queryFn: getHealthBreaches,
    refetchInterval: 15_000,
  });

  const summaryQuery = useQuery({
    queryKey: ["platform", "health", "summary"],
    queryFn: getHealthSummary,
    refetchInterval: 30_000,
  });

  const snapshotMut = useMutation({
    mutationFn: takeHealthSnapshot,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform", "health"] });
    },
  });

  const slos: SLOEntry[] = slosQuery.data?.data ?? [];
  const breaches: Breach[] = breachesQuery.data?.data ?? [];
  const summary = summaryQuery.data?.data ?? {};

  // Compute overall status
  const statuses = slos.map((s) => s.status);
  const overallStatus = statuses.includes("BREACHED")
    ? "BREACHED"
    : statuses.includes("WARNING")
      ? "WARNING"
      : statuses.every((s) => s === "UNKNOWN")
        ? "UNKNOWN"
        : "OK";
  const OverallIcon = STATUS_CONFIG[overallStatus]?.icon ?? HelpCircle;

  const okCount = statuses.filter((s) => s === "OK").length;
  const warnCount = statuses.filter((s) => s === "WARNING").length;
  const breachCount = statuses.filter((s) => s === "BREACHED").length;

  return (
    <div>
      <PageHeader
        title="System Health & Monitoring"
        description="Platform SLO status, active breaches, and health metrics"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => slosQuery.refetch()}>
              <RefreshCw className="mr-1 h-4 w-4" />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={() => snapshotMut.mutate()}
              disabled={snapshotMut.isPending}
            >
              <Camera className="mr-1 h-4 w-4" />
              Take Snapshot
            </Button>
          </div>
        }
      />

      {/* Overall Status Banner */}
      <Card className={`mb-6 border-l-4 ${
        overallStatus === "OK" ? "border-l-green-500" :
        overallStatus === "WARNING" ? "border-l-orange-500" :
        overallStatus === "BREACHED" ? "border-l-red-500" :
        "border-l-neutral-300"
      }`}>
        <CardContent className="flex items-center gap-4 p-5">
          <OverallIcon className={`h-8 w-8 ${STATUS_CONFIG[overallStatus]?.color ?? "text-neutral-400"}`} />
          <div>
            <h2 className="text-lg font-bold">
              Platform Status: {overallStatus}
            </h2>
            <p className="text-sm text-neutral-500">
              {okCount} OK, {warnCount} warnings, {breachCount} breaches, {breaches.length} active
            </p>
          </div>
        </CardContent>
      </Card>

      {/* SLO Summary Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard title="SLOs OK" value={okCount} icon={CheckCircle} description="Within thresholds" />
        <StatCard title="SLOs Warning" value={warnCount} icon={AlertTriangle} description="Approaching thresholds" />
        <StatCard title="Active Breaches" value={breaches.length} icon={XCircle} description="Require attention" />
      </div>

      {/* SLO Detail Table */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Service Level Objectives</CardTitle>
        </CardHeader>
        <CardContent>
          {slosQuery.isLoading ? (
            <div className="py-8 text-center text-neutral-400">Loading SLOs...</div>
          ) : slos.length === 0 ? (
            <div className="py-8 text-center text-neutral-400">No SLO data available. Metrics have not been recorded yet.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>SLO</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Current Value</TableHead>
                  <TableHead>Threshold</TableHead>
                  <TableHead>Warning</TableHead>
                  <TableHead>Last Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {slos.map((slo) => {
                  const SloIcon = SLO_ICONS[slo.slo_id] || Activity;
                  const cfg = STATUS_CONFIG[slo.status] || STATUS_CONFIG.UNKNOWN;
                  const StatusIcon = cfg.icon;
                  return (
                    <TableRow key={slo.slo_id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <SloIcon className="h-4 w-4 text-neutral-400" />
                          <div>
                            <div className="text-sm font-medium">{slo.name}</div>
                            <div className="text-xs text-neutral-400">{slo.metric_name}</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <StatusIcon className={`h-4 w-4 ${cfg.color}`} />
                          <Badge variant={cfg.badge}>{slo.status}</Badge>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {slo.current_value !== null ? `${slo.current_value}${slo.unit}` : "--"}
                      </TableCell>
                      <TableCell className="font-mono text-sm text-neutral-500">
                        {slo.comparison === "gte" ? ">=" : slo.comparison === "lte" ? "<=" : "="}{" "}
                        {slo.threshold}{slo.unit}
                      </TableCell>
                      <TableCell className="font-mono text-sm text-neutral-400">
                        {slo.warning_threshold !== null ? `${slo.warning_threshold}${slo.unit}` : "--"}
                      </TableCell>
                      <TableCell className="text-xs text-neutral-400">
                        {slo.last_recorded
                          ? new Date(slo.last_recorded).toLocaleString()
                          : "Never"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Active Breaches */}
      {breaches.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Active Breaches
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>SLO</TableHead>
                  <TableHead>Observed</TableHead>
                  <TableHead>Threshold</TableHead>
                  <TableHead>Breached At</TableHead>
                  <TableHead>Region</TableHead>
                  <TableHead>Tenant</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {breaches.map((b) => (
                  <TableRow key={b.breach_id}>
                    <TableCell className="font-medium">{b.slo_id}</TableCell>
                    <TableCell className="font-mono text-sm text-red-600">
                      {b.observed_value}
                    </TableCell>
                    <TableCell className="font-mono text-sm text-neutral-500">
                      {b.threshold}
                    </TableCell>
                    <TableCell className="text-xs">
                      {new Date(b.breached_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {b.region_code ? <Badge variant="outline">{b.region_code}</Badge> : "--"}
                    </TableCell>
                    <TableCell className="text-xs text-neutral-400 truncate max-w-[100px]">
                      {b.tenant_id ? b.tenant_id.slice(0, 8) + "..." : "Platform"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
