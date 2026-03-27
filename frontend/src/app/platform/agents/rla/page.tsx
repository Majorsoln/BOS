"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { FormDialog } from "@/components/shared/form-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge, Textarea,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import {
  getAgents, registerAgent, suspendAgent, reinstateAgent, terminateAgent,
} from "@/lib/api/agents";
import { getRegions } from "@/lib/api/saas";
import { REGIONS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import {
  Shield, MapPin, Plus, XCircle, Play, AlertTriangle, Building2, CheckCircle2, Users,
} from "lucide-react";

type ToastState = { message: string; variant: "success" | "error" } | null;

export default function RegionLicenseAgentsPage() {
  const qc = useQueryClient();
  const [toast, setToast] = useState<ToastState>(null);
  const [showAppoint, setShowAppoint] = useState(false);
  const [showSuspend, setShowSuspend] = useState<string | null>(null);
  const [showTerminate, setShowTerminate] = useState<string | null>(null);

  const agents = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });

  const regions = useQuery({ queryKey: ["saas", "regions"], queryFn: getRegions });

  const appointMut = useMutation({
    mutationFn: registerAgent,
    onSuccess: () => {
      setShowAppoint(false);
      qc.invalidateQueries({ queryKey: ["saas", "agents"] });
      setToast({ message: "Region License Agent appointed", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to appoint agent", variant: "error" }),
  });

  const suspendMut = useMutation({
    mutationFn: suspendAgent,
    onSuccess: () => { setShowSuspend(null); qc.invalidateQueries({ queryKey: ["saas", "agents"] }); setToast({ message: "Agent suspended", variant: "success" }); },
    onError: () => setToast({ message: "Failed to suspend", variant: "error" }),
  });

  const reinstateMut = useMutation({
    mutationFn: reinstateAgent,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "agents"] }); setToast({ message: "Agent reinstated", variant: "success" }); },
    onError: () => setToast({ message: "Failed to reinstate", variant: "error" }),
  });

  const terminateMut = useMutation({
    mutationFn: terminateAgent,
    onSuccess: () => { setShowTerminate(null); qc.invalidateQueries({ queryKey: ["saas", "agents"] }); setToast({ message: "Agent terminated", variant: "success" }); },
    onError: () => setToast({ message: "Failed to terminate", variant: "error" }),
  });

  const agentList: Array<{
    agent_id: string; agent_name: string; agent_type: string;
    territory?: string; status: string; tenant_count?: number;
    contact_email: string; contact_phone?: string; created_at?: string;
    office_address?: string;
  }> = agents.data?.data ?? [];

  // Regions that already have an RLA
  const assignedRegions = new Set(agentList.filter((a) => a.status !== "TERMINATED").map((a) => a.territory).filter(Boolean));
  const availableRegions = REGIONS.filter((r) => !assignedRegions.has(r.code));

  const activeCount = agentList.filter((a) => a.status === "ACTIVE").length;
  const totalRegions = REGIONS.length;

  function handleAppoint(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    appointMut.mutate({
      agent_name: d.get("agent_name") as string,
      contact_email: d.get("contact_email") as string,
      contact_phone: d.get("contact_phone") as string,
      country: d.get("territory") as string,
      agent_type: "REGION_LICENSE_AGENT",
      notes: (d.get("notes") as string) || undefined,
    });
  }

  return (
    <div>
      <PageHeader
        title="Region License Agents"
        description="Each region has one licensed agent who manages compliance, collects revenue, and provides local support"
        actions={
          <Button onClick={() => setShowAppoint(true)} className="gap-2" disabled={availableRegions.length === 0}>
            <Plus className="h-4 w-4" />
            Appoint RLA
          </Button>
        }
      />

      {/* Stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active RLAs" value={activeCount} icon={Shield} />
        <StatCard title="Total Regions" value={totalRegions} icon={MapPin} />
        <StatCard title="Uncovered Regions" value={totalRegions - activeCount} icon={AlertTriangle} />
        <StatCard title="Total Tenants (RLA)" value={agentList.reduce((s, a) => s + (a.tenant_count ?? 0), 0)} icon={Users} />
      </div>

      {/* Doctrine Card */}
      <Card className="mb-6 border-bos-purple/20 bg-bos-purple-light/30">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Shield className="mt-0.5 h-5 w-5 text-bos-purple" />
            <div className="text-sm">
              <p className="font-semibold text-bos-purple">Region License Agent Doctrine</p>
              <ul className="mt-1 list-disc pl-4 text-neutral-600 dark:text-neutral-400 space-y-0.5">
                <li><strong>One per region</strong> — each region has exactly one RLA</li>
                <li><strong>Revenue collector</strong> — collects all subscription payments from tenants in their region</li>
                <li><strong>Compliance owner</strong> — responsible for local tax filings, e-invoicing, privacy compliance</li>
                <li><strong>Support lead</strong> — provides L1 support to tenants, escalates to Main Admin</li>
                <li><strong>Region must have active RLA</strong> before pricing/billing can be enabled</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agent Table */}
      <Card>
        <CardContent className="p-0">
          {agentList.length === 0 ? (
            <EmptyState title="No Region License Agents" description="Appoint your first RLA to open a region for business" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Region</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Tenants</TableHead>
                  <TableHead>Appointed</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agentList.map((a) => {
                  const region = REGIONS.find((r) => r.code === a.territory);
                  return (
                    <TableRow key={a.agent_id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center justify-center rounded-md bg-bos-purple/10 px-2 py-0.5 text-xs font-bold text-bos-purple">
                            {a.territory || "—"}
                          </span>
                          <span className="text-sm">{region?.name ?? ""}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <p className="font-medium">{a.agent_name}</p>
                      </TableCell>
                      <TableCell>
                        <p className="text-sm text-bos-silver-dark">{a.contact_email}</p>
                        <p className="text-xs text-bos-silver-dark">{a.contact_phone}</p>
                      </TableCell>
                      <TableCell className="text-center"><StatusBadge status={a.status} /></TableCell>
                      <TableCell className="text-right font-mono">{a.tenant_count ?? 0}</TableCell>
                      <TableCell className="text-sm text-bos-silver-dark">{formatDate(a.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          {a.status === "SUSPENDED" && (
                            <Button size="sm" variant="outline" onClick={() => reinstateMut.mutate({ agent_id: a.agent_id })} title="Reinstate">
                              <Play className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          {(a.status === "ACTIVE" || a.status === "PROBATION") && (
                            <Button size="sm" variant="outline" onClick={() => setShowSuspend(a.agent_id)} title="Suspend">
                              <Shield className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          {a.status !== "TERMINATED" && (
                            <Button size="sm" variant="destructive" onClick={() => setShowTerminate(a.agent_id)} title="Terminate">
                              <XCircle className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Appoint Dialog */}
      <FormDialog
        open={showAppoint}
        onClose={() => setShowAppoint(false)}
        title="Appoint Region License Agent"
        description="This agent will be the sole licensed operator for the selected region. They will handle compliance, revenue collection, and local support."
        onSubmit={handleAppoint}
        submitLabel="Appoint RLA"
        loading={appointMut.isPending}
        wide
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Region</Label>
            <Select name="territory" required>
              <option value="">Select region...</option>
              {availableRegions.map((r) => (
                <option key={r.code} value={r.code}>{r.code} — {r.name}</option>
              ))}
            </Select>
            {availableRegions.length === 0 && (
              <p className="mt-1 text-xs text-red-500">All regions have an assigned RLA</p>
            )}
          </div>
          <div>
            <Label>Agent / Company Name</Label>
            <Input name="agent_name" required placeholder="e.g. BOS Kenya Ltd" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Email</Label>
            <Input name="contact_email" type="email" required />
          </div>
          <div>
            <Label>Phone</Label>
            <Input name="contact_phone" required placeholder="+254..." />
          </div>
        </div>
        <div>
          <Label>Notes</Label>
          <Textarea name="notes" placeholder="Agreement details, office address, compliance certifications..." />
        </div>
      </FormDialog>

      {/* Suspend Dialog */}
      <FormDialog
        open={!!showSuspend}
        onClose={() => setShowSuspend(null)}
        title="Suspend Region License Agent"
        description="Suspending an RLA will freeze their region operations. Tenants can still use the system but no new sales can be processed by this agent."
        onSubmit={(e) => { e.preventDefault(); const d = new FormData(e.target as HTMLFormElement); suspendMut.mutate({ agent_id: showSuspend!, reason: d.get("reason") as string }); }}
        submitLabel="Suspend"
        loading={suspendMut.isPending}
      >
        <div>
          <Label>Reason</Label>
          <Textarea name="reason" required placeholder="Reason for suspension..." />
        </div>
      </FormDialog>

      {/* Terminate Dialog */}
      <FormDialog
        open={!!showTerminate}
        onClose={() => setShowTerminate(null)}
        title="Terminate Region License Agent"
        description="Termination is permanent. The region will become uncovered until a new RLA is appointed."
        onSubmit={(e) => { e.preventDefault(); const d = new FormData(e.target as HTMLFormElement); terminateMut.mutate({ agent_id: showTerminate!, reason: d.get("reason") as string }); }}
        submitLabel="Terminate"
        loading={terminateMut.isPending}
      >
        <div className="mb-3 flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Terminating an RLA removes them permanently. You must appoint a replacement before the region can resume operations.</span>
        </div>
        <div>
          <Label>Reason</Label>
          <Textarea name="reason" required placeholder="Reason for termination..." />
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
