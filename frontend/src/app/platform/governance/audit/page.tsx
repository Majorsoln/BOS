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
import { getComplianceAuditTrail } from "@/lib/api/platform";
import {
  FileText,
  RefreshCw,
  Shield,
  AlertTriangle,
  Scale,
  Lock,
  UserCheck,
} from "lucide-react";
import { useState } from "react";

const EVENT_BADGES: Record<string, { label: string; color: string; icon: typeof Shield }> = {
  "platform.audit.compliance.tax_decision.v1": { label: "Tax Decision", color: "bg-blue-100 text-blue-700", icon: Scale },
  "platform.audit.compliance.policy_change.v1": { label: "Policy Change", color: "bg-purple-100 text-purple-700", icon: FileText },
  "platform.audit.compliance.agent_action.v1": { label: "Agent Action", color: "bg-green-100 text-green-700", icon: UserCheck },
  "platform.audit.compliance.data_breach.v1": { label: "Data Breach", color: "bg-red-100 text-red-700", icon: AlertTriangle },
  "platform.audit.compliance.dsar_request.v1": { label: "DSAR Request", color: "bg-orange-100 text-orange-700", icon: Lock },
  "platform.audit.compliance.consent_recorded.v1": { label: "Consent", color: "bg-teal-100 text-teal-700", icon: Shield },
  "platform.audit.compliance.filing_submitted.v1": { label: "Tax Filing", color: "bg-indigo-100 text-indigo-700", icon: FileText },
  "platform.audit.compliance.escalation.v1": { label: "Escalation", color: "bg-yellow-100 text-yellow-700", icon: AlertTriangle },
};

export default function ComplianceAuditPage() {
  const [regionFilter, setRegionFilter] = useState("");

  const auditQuery = useQuery({
    queryKey: ["platform", "compliance", "audit", regionFilter],
    queryFn: () => getComplianceAuditTrail({ region_code: regionFilter || undefined, limit: 200 }),
    refetchInterval: 30_000,
  });

  const entries = auditQuery.data?.data ?? [];

  // Derive unique regions for filter
  const regions = [...new Set(entries.map((e: { region_code: string }) => e.region_code).filter(Boolean))].sort();

  return (
    <div>
      <PageHeader
        title="Compliance Audit Ledger"
        description="Immutable evidence trail for all compliance decisions, tax filings, data governance, and escalations"
        actions={
          <Button variant="outline" size="sm" onClick={() => auditQuery.refetch()}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>
        }
      />

      {/* Summary Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-l-4 border-l-blue-400 p-4">
          <div className="flex items-center gap-3">
            <Scale className="h-6 w-6 text-blue-500" />
            <div>
              <div className="text-2xl font-bold">
                {entries.filter((e: { event_type: string }) => e.event_type.includes("tax_decision")).length}
              </div>
              <div className="text-sm text-neutral-500">Tax Decisions</div>
            </div>
          </div>
        </Card>
        <Card className="border-l-4 border-l-purple-400 p-4">
          <div className="flex items-center gap-3">
            <FileText className="h-6 w-6 text-purple-500" />
            <div>
              <div className="text-2xl font-bold">
                {entries.filter((e: { event_type: string }) => e.event_type.includes("filing")).length}
              </div>
              <div className="text-sm text-neutral-500">Tax Filings</div>
            </div>
          </div>
        </Card>
        <Card className="border-l-4 border-l-red-400 p-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-6 w-6 text-red-500" />
            <div>
              <div className="text-2xl font-bold">
                {entries.filter((e: { event_type: string }) => e.event_type.includes("data_breach")).length}
              </div>
              <div className="text-sm text-neutral-500">Breach Reports</div>
            </div>
          </div>
        </Card>
        <Card className="border-l-4 border-l-orange-400 p-4">
          <div className="flex items-center gap-3">
            <Lock className="h-6 w-6 text-orange-500" />
            <div>
              <div className="text-2xl font-bold">
                {entries.filter((e: { event_type: string }) => e.event_type.includes("dsar") || e.event_type.includes("consent")).length}
              </div>
              <div className="text-sm text-neutral-500">Privacy Actions</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Filter */}
      <Card className="mb-6">
        <CardContent className="flex items-end gap-4 p-4">
          <div className="min-w-[200px]">
            <label className="mb-1 block text-xs font-medium text-neutral-500">Region</label>
            <Select value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)}>
              <option value="">All Regions</option>
              {regions.map((r) => (
                <option key={r as string} value={r as string}>{r as string}</option>
              ))}
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Audit Trail Table */}
      <Card>
        <CardHeader>
          <CardTitle>Compliance Audit Trail ({entries.length} entries)</CardTitle>
        </CardHeader>
        <CardContent>
          {auditQuery.isLoading ? (
            <div className="py-8 text-center text-neutral-400">Loading...</div>
          ) : entries.length === 0 ? (
            <div className="py-12 text-center text-neutral-400">
              <Shield className="mx-auto mb-2 h-10 w-10 text-neutral-300" />
              <div>No compliance audit entries yet.</div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Region</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry: {
                  entry_id: string;
                  event_type: string;
                  actor_id: string;
                  actor_type: string;
                  issued_at: string;
                  subject_type: string;
                  subject_id: string;
                  region_code: string;
                  payload: Record<string, unknown>;
                  notes: string;
                }) => {
                  const cfg = EVENT_BADGES[entry.event_type] || { label: entry.event_type, color: "bg-neutral-100 text-neutral-600", icon: FileText };
                  const Icon = cfg.icon;
                  return (
                    <TableRow key={entry.entry_id}>
                      <TableCell className="text-xs text-neutral-500 whitespace-nowrap">
                        {entry.issued_at ? new Date(entry.issued_at).toLocaleString() : "--"}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <Icon className="h-3.5 w-3.5 text-neutral-400" />
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${cfg.color}`}>
                            {cfg.label}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs">
                          <Badge variant="outline">{entry.actor_type}</Badge>
                          <div className="mt-0.5 text-neutral-400 truncate max-w-[120px]">{entry.actor_id}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs">
                          <span className="font-medium">{entry.subject_type}</span>
                          <div className="text-neutral-400 truncate max-w-[120px]">{entry.subject_id}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {entry.region_code ? <Badge variant="outline">{entry.region_code}</Badge> : "--"}
                      </TableCell>
                      <TableCell className="text-xs text-neutral-500 max-w-[200px] truncate">
                        {entry.notes || JSON.stringify(entry.payload).slice(0, 80)}
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
