"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
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
  Select,
} from "@/components/ui";
import { getGovernanceEscalations } from "@/lib/api/platform";
import {
  AlertTriangle,
  RefreshCw,
  CheckCircle,
  Clock,
  Shield,
  Flag,
} from "lucide-react";
import { useState } from "react";

const SEVERITY_COLORS: Record<string, string> = {
  LOW: "bg-neutral-100 text-neutral-600",
  NORMAL: "bg-blue-100 text-blue-700",
  HIGH: "bg-orange-100 text-orange-700",
  CRITICAL: "bg-red-100 text-red-700",
};

const STATUS_COLORS: Record<string, { color: string; icon: typeof Clock }> = {
  OPEN: { color: "bg-orange-100 text-orange-700", icon: Clock },
  IN_PROGRESS: { color: "bg-blue-100 text-blue-700", icon: Flag },
  RESOLVED: { color: "bg-green-100 text-green-700", icon: CheckCircle },
  CLOSED: { color: "bg-neutral-100 text-neutral-600", icon: Shield },
};

export default function GovernanceEscalationsPage() {
  const [statusFilter, setStatusFilter] = useState("");

  const escalationsQuery = useQuery({
    queryKey: ["platform", "governance", "escalations", statusFilter],
    queryFn: () => getGovernanceEscalations({ status: statusFilter || undefined }),
    refetchInterval: 30_000,
  });

  const escalations = escalationsQuery.data?.data ?? [];

  const openCount = escalations.filter((e: { status: string }) => e.status === "OPEN").length;
  const criticalCount = escalations.filter((e: { severity: string }) => e.severity === "CRITICAL").length;

  return (
    <div>
      <PageHeader
        title="Compliance Escalations"
        description="Issues escalated from Region Agents to Main Admin requiring resolution"
        actions={
          <Button variant="outline" size="sm" onClick={() => escalationsQuery.refetch()}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>
        }
      />

      {/* Summary */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="border-l-4 border-l-orange-400 p-4">
          <div className="flex items-center gap-3">
            <Clock className="h-6 w-6 text-orange-500" />
            <div>
              <div className="text-2xl font-bold">{openCount}</div>
              <div className="text-sm text-neutral-500">Open Escalations</div>
            </div>
          </div>
        </Card>
        <Card className="border-l-4 border-l-red-400 p-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-6 w-6 text-red-500" />
            <div>
              <div className="text-2xl font-bold">{criticalCount}</div>
              <div className="text-sm text-neutral-500">Critical Severity</div>
            </div>
          </div>
        </Card>
        <Card className="border-l-4 border-l-green-400 p-4">
          <div className="flex items-center gap-3">
            <CheckCircle className="h-6 w-6 text-green-500" />
            <div>
              <div className="text-2xl font-bold">{escalations.length - openCount}</div>
              <div className="text-sm text-neutral-500">Resolved</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Filter */}
      <Card className="mb-6">
        <CardContent className="flex items-end gap-4 p-4">
          <div className="min-w-[200px]">
            <label className="mb-1 block text-xs font-medium text-neutral-500">Status</label>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Escalations Table */}
      <Card>
        <CardHeader>
          <CardTitle>Escalations ({escalations.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {escalationsQuery.isLoading ? (
            <div className="py-8 text-center text-neutral-400">Loading...</div>
          ) : escalations.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-neutral-400">
              <CheckCircle className="h-10 w-10 text-green-400" />
              <div className="text-lg font-medium text-green-600">No escalations</div>
              <div>All compliance matters are handled at the agent level.</div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Region</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Resolved</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {escalations.map((esc: {
                  escalation_id: string;
                  region_code: string;
                  agent_reseller_id: string;
                  subject_type: string;
                  subject_id: string;
                  description: string;
                  severity: string;
                  status: string;
                  created_at: string;
                  resolved_at: string;
                  resolved_by: string;
                }) => {
                  const sevColor = SEVERITY_COLORS[esc.severity] || SEVERITY_COLORS.NORMAL;
                  const statusCfg = STATUS_COLORS[esc.status] || STATUS_COLORS.OPEN;
                  const StatusIcon = statusCfg.icon;
                  return (
                    <TableRow key={esc.escalation_id}>
                      <TableCell className="font-mono text-xs">
                        {esc.escalation_id.slice(0, 8)}...
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{esc.region_code}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs">
                          <Badge variant="outline">{esc.subject_type}</Badge>
                          <div className="mt-0.5 text-neutral-400 truncate max-w-[100px]">
                            {esc.subject_id.slice(0, 12)}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="max-w-[200px] text-sm truncate">
                        {esc.description}
                      </TableCell>
                      <TableCell>
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${sevColor}`}>
                          {esc.severity}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <StatusIcon className="h-3.5 w-3.5" />
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${statusCfg.color}`}>
                            {esc.status}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-neutral-400">
                        {esc.created_at ? new Date(esc.created_at).toLocaleDateString() : "--"}
                      </TableCell>
                      <TableCell className="text-xs text-neutral-400">
                        {esc.resolved_at ? (
                          <div>
                            {new Date(esc.resolved_at).toLocaleDateString()}
                            <div className="text-neutral-300">by {esc.resolved_by?.slice(0, 8) || "—"}</div>
                          </div>
                        ) : "--"}
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
