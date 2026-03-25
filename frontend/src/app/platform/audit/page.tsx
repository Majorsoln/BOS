"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Input,
  Select,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Badge,
} from "@/components/ui";
import { getAuditLog, getTenantAuditHistory } from "@/lib/api/platform";
import { FileText, Search, RefreshCw, User, Server, Shield, Clock } from "lucide-react";

const EVENT_TYPE_LABELS: Record<string, string> = {
  "platform.audit.tenant.onboarded.v1": "Tenant Onboarded",
  "platform.audit.tenant.activated.v1": "Tenant Activated",
  "platform.audit.tenant.suspended.v1": "Tenant Suspended",
  "platform.audit.tenant.reinstated.v1": "Tenant Reinstated",
  "platform.audit.tenant.terminated.v1": "Tenant Terminated",
  "platform.audit.plan.assigned.v1": "Plan Assigned",
  "platform.audit.plan.upgraded.v1": "Plan Upgraded",
  "platform.audit.region_pack.applied.v1": "Region Pack Applied",
  "platform.audit.flag.toggled.v1": "Flag Toggled",
  "platform.audit.kill_switch.activated.v1": "Kill Switch",
  "platform.audit.schema.migrated.v1": "Schema Migrated",
  "platform.audit.key.rotated.v1": "Key Rotated",
  "platform.audit.rollout.started.v1": "Rollout Started",
  "platform.audit.rollout.completed.v1": "Rollout Completed",
  "platform.audit.compliance_pack.versioned.v1": "Pack Versioned",
};

const EVENT_TYPE_OPTIONS = [
  { value: "", label: "All Event Types" },
  ...Object.entries(EVENT_TYPE_LABELS).map(([value, label]) => ({ value, label })),
];

const ACTOR_TYPE_BADGE: Record<string, "purple" | "warning" | "secondary"> = {
  PLATFORM_ADMIN: "purple",
  SYSTEM: "secondary",
  AUTOMATION: "warning",
};

const SUBJECT_TYPE_ICON: Record<string, typeof User> = {
  TENANT: User,
  PLAN: FileText,
  REGION_PACK: Server,
  FLAG: Shield,
  SCHEMA: Server,
};

interface AuditEntry {
  entry_id: string;
  event_type: string;
  actor_id: string;
  actor_type: string;
  issued_at: string;
  subject_type: string;
  subject_id: string;
  payload: Record<string, unknown>;
  correlation_id: string | null;
  region_code: string | null;
  notes: string | null;
}

export default function PlatformAuditPage() {
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [subjectFilter, setSubjectFilter] = useState("");
  const [searchMode, setSearchMode] = useState<"recent" | "subject" | "event_type">("recent");
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null);

  const auditQuery = useQuery({
    queryKey: ["platform", "audit", searchMode, eventTypeFilter, subjectFilter],
    queryFn: () => {
      if (searchMode === "subject" && subjectFilter) {
        return getTenantAuditHistory(subjectFilter);
      }
      const params: Record<string, string> = { limit: "100" };
      if (eventTypeFilter) params.event_type = eventTypeFilter;
      if (subjectFilter && searchMode !== "subject") params.subject_id = subjectFilter;
      return getAuditLog(params);
    },
  });

  const entries: AuditEntry[] = auditQuery.data?.data ?? [];

  return (
    <div>
      <PageHeader
        title="Platform Audit Log"
        description="Immutable record of all platform-level operations"
        actions={
          <Button variant="outline" size="sm" onClick={() => auditQuery.refetch()}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>
        }
      />

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex-1 min-w-[200px]">
              <label className="mb-1 block text-xs font-medium text-neutral-500">Event Type</label>
              <Select
                value={eventTypeFilter}
                onChange={(e) => {
                  setEventTypeFilter(e.target.value);
                  if (e.target.value) setSearchMode("event_type");
                  else setSearchMode("recent");
                }}
              >
                {EVENT_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </Select>
            </div>
            <div className="flex-1 min-w-[200px]">
              <label className="mb-1 block text-xs font-medium text-neutral-500">Subject / Tenant ID</label>
              <div className="flex gap-2">
                <Input
                  placeholder="Enter UUID..."
                  value={subjectFilter}
                  onChange={(e) => setSubjectFilter(e.target.value)}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (subjectFilter) setSearchMode("subject");
                    auditQuery.refetch();
                  }}
                >
                  <Search className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setEventTypeFilter("");
                setSubjectFilter("");
                setSearchMode("recent");
              }}
            >
              Clear Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Summary Stats */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Card className="p-4">
          <div className="text-sm text-neutral-500">Total Entries</div>
          <div className="text-2xl font-bold">{entries.length}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-neutral-500">Unique Actors</div>
          <div className="text-2xl font-bold">
            {new Set(entries.map((e) => e.actor_id)).size}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-neutral-500">Event Types</div>
          <div className="text-2xl font-bold">
            {new Set(entries.map((e) => e.event_type)).size}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-neutral-500">Regions</div>
          <div className="text-2xl font-bold">
            {new Set(entries.filter((e) => e.region_code).map((e) => e.region_code)).size}
          </div>
        </Card>
      </div>

      {/* Audit Log Table */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Entries</CardTitle>
        </CardHeader>
        <CardContent>
          {auditQuery.isLoading ? (
            <div className="py-8 text-center text-neutral-400">Loading audit log...</div>
          ) : entries.length === 0 ? (
            <div className="py-8 text-center text-neutral-400">No audit entries found.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Event</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Region</TableHead>
                  <TableHead>Notes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry) => {
                  const SubjIcon = SUBJECT_TYPE_ICON[entry.subject_type] || FileText;
                  const isExpanded = expandedEntry === entry.entry_id;
                  return (
                    <>
                      <TableRow
                        key={entry.entry_id}
                        className="cursor-pointer"
                        onClick={() => setExpandedEntry(isExpanded ? null : entry.entry_id)}
                      >
                        <TableCell className="whitespace-nowrap text-xs">
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3 text-neutral-400" />
                            {new Date(entry.issued_at).toLocaleString()}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={
                            entry.event_type.includes("terminated") || entry.event_type.includes("kill_switch")
                              ? "destructive"
                              : entry.event_type.includes("suspended")
                                ? "warning"
                                : entry.event_type.includes("onboarded") || entry.event_type.includes("activated")
                                  ? "success"
                                  : "secondary"
                          }>
                            {EVENT_TYPE_LABELS[entry.event_type] || entry.event_type.split(".").slice(-2, -1)[0]}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Badge variant={ACTOR_TYPE_BADGE[entry.actor_type] || "secondary"}>
                              {entry.actor_type}
                            </Badge>
                            <span className="text-xs text-neutral-400 truncate max-w-[80px]" title={entry.actor_id}>
                              {entry.actor_id.slice(0, 8)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <SubjIcon className="h-3.5 w-3.5 text-neutral-400" />
                            <span className="text-xs font-medium">{entry.subject_type}</span>
                            <span className="text-xs text-neutral-400 truncate max-w-[80px]" title={entry.subject_id}>
                              {entry.subject_id.slice(0, 8)}...
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {entry.region_code ? (
                            <Badge variant="outline">{entry.region_code}</Badge>
                          ) : (
                            <span className="text-xs text-neutral-300">--</span>
                          )}
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate text-xs text-neutral-500">
                          {entry.notes || "--"}
                        </TableCell>
                      </TableRow>
                      {isExpanded && (
                        <TableRow key={`${entry.entry_id}-detail`}>
                          <TableCell colSpan={6}>
                            <div className="rounded-md bg-neutral-50 p-4 dark:bg-neutral-900">
                              <div className="grid grid-cols-2 gap-4 text-xs">
                                <div>
                                  <span className="font-medium text-neutral-500">Entry ID:</span>{" "}
                                  <code className="text-xs">{entry.entry_id}</code>
                                </div>
                                <div>
                                  <span className="font-medium text-neutral-500">Correlation ID:</span>{" "}
                                  <code className="text-xs">{entry.correlation_id || "none"}</code>
                                </div>
                                <div>
                                  <span className="font-medium text-neutral-500">Full Actor ID:</span>{" "}
                                  <code className="text-xs">{entry.actor_id}</code>
                                </div>
                                <div>
                                  <span className="font-medium text-neutral-500">Full Subject ID:</span>{" "}
                                  <code className="text-xs">{entry.subject_id}</code>
                                </div>
                              </div>
                              <div className="mt-3">
                                <span className="text-xs font-medium text-neutral-500">Payload:</span>
                                <pre className="mt-1 max-h-40 overflow-auto rounded bg-neutral-100 p-2 text-xs dark:bg-neutral-800">
                                  {JSON.stringify(entry.payload, null, 2)}
                                </pre>
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </>
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
