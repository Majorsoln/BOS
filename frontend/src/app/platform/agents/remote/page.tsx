"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { FormDialog } from "@/components/shared/form-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Button, Card, CardContent, Input, Label, Select, Toast, Badge, Textarea,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import {
  getAgents, registerAgent, suspendAgent, reinstateAgent, terminateAgent,
} from "@/lib/api/agents";
import { REGIONS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import { UserCheck, Plus, XCircle, Play, Shield, AlertTriangle, Users, Globe } from "lucide-react";

type ToastState = { message: string; variant: "success" | "error" } | null;

export default function RemoteAgentsPage() {
  const qc = useQueryClient();
  const [toast, setToast] = useState<ToastState>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [showRegister, setShowRegister] = useState(false);
  const [showSuspend, setShowSuspend] = useState<string | null>(null);
  const [showTerminate, setShowTerminate] = useState<string | null>(null);

  const agents = useQuery({
    queryKey: ["saas", "agents", "REMOTE_AGENT", statusFilter],
    queryFn: () => getAgents({ type: "REMOTE_AGENT", status: statusFilter || undefined }),
  });

  // Fetch RLAs to know which regions are open
  const rlaQuery = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });

  const rlaList: Array<{ territory?: string; status: string }> = rlaQuery.data?.data ?? [];
  const openRegions = new Set(rlaList.filter((a) => a.status === "ACTIVE").map((a) => a.territory).filter(Boolean));

  const registerMut = useMutation({
    mutationFn: registerAgent,
    onSuccess: () => {
      setShowRegister(false);
      qc.invalidateQueries({ queryKey: ["saas", "agents"] });
      setToast({ message: "Remote Agent registered (probation)", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to register agent", variant: "error" }),
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
  }> = agents.data?.data ?? [];

  const activeCount = agentList.filter((a) => a.status === "ACTIVE").length;

  function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    registerMut.mutate({
      agent_name: d.get("agent_name") as string,
      contact_email: d.get("contact_email") as string,
      contact_phone: d.get("contact_phone") as string,
      country: d.get("country") as string,
      agent_type: "REMOTE_AGENT",
      notes: (d.get("notes") as string) || undefined,
    });
  }

  return (
    <div>
      <PageHeader
        title="Remote Agents"
        description="Remote Agents can sell and support tenants in any region that has an active Region License Agent"
        actions={
          <Button onClick={() => setShowRegister(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Register Remote Agent
          </Button>
        }
      />

      {/* Stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active Remote Agents" value={activeCount} icon={UserCheck} />
        <StatCard title="Total Registered" value={agentList.length} icon={Users} />
        <StatCard title="Open Regions" value={openRegions.size} icon={Globe} />
        <StatCard title="Total Tenants" value={agentList.reduce((s, a) => s + (a.tenant_count ?? 0), 0)} icon={Users} />
      </div>

      {/* Doctrine */}
      <Card className="mb-6 border-blue-200/50 bg-blue-50/30 dark:border-blue-800/30 dark:bg-blue-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Globe className="mt-0.5 h-5 w-5 text-blue-600" />
            <div className="text-sm">
              <p className="font-semibold text-blue-700 dark:text-blue-400">Remote Agent Doctrine</p>
              <ul className="mt-1 list-disc pl-4 text-neutral-600 dark:text-neutral-400 space-y-0.5">
                <li><strong>Can sell anywhere</strong> — in any region that has an active RLA</li>
                <li><strong>No territory lock</strong> — not bound to a single region</li>
                <li><strong>Commission per sale</strong> — earns commission on tenants they onboard</li>
                <li><strong>No compliance responsibility</strong> — compliance is handled by the region's RLA</li>
                <li><strong>Probation period</strong> — must onboard 5 tenants within 90 days</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
          <option value="">All Statuses</option>
          <option value="PROBATION">Probation</option>
          <option value="ACTIVE">Active</option>
          <option value="SUSPENDED">Suspended</option>
          <option value="TERMINATED">Terminated</option>
        </Select>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {agentList.length === 0 ? (
            <EmptyState title="No Remote Agents" description="Register your first remote agent to expand your sales force" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead>Base Country</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Tenants</TableHead>
                  <TableHead>Registered</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agentList.map((a) => {
                  const region = REGIONS.find((r) => r.code === a.territory);
                  return (
                    <TableRow key={a.agent_id}>
                      <TableCell className="font-medium">{a.agent_name}</TableCell>
                      <TableCell>
                        <p className="text-sm text-bos-silver-dark">{a.contact_email}</p>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{a.territory || "—"} {region?.name ? `— ${region.name}` : ""}</Badge>
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

      {/* Register Dialog */}
      <FormDialog
        open={showRegister}
        onClose={() => setShowRegister(false)}
        title="Register Remote Agent"
        description="Remote agents can sell in any region with an active RLA. They start in PROBATION."
        onSubmit={handleRegister}
        submitLabel="Register"
        loading={registerMut.isPending}
        wide
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Agent Name</Label>
            <Input name="agent_name" required placeholder="Individual or company name" />
          </div>
          <div>
            <Label>Base Country</Label>
            <Select name="country" required>
              <option value="">Select country...</option>
              {REGIONS.map((r) => (
                <option key={r.code} value={r.code}>{r.code} — {r.name}</option>
              ))}
            </Select>
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

        {openRegions.size > 0 && (
          <div className="rounded-lg bg-green-50 p-3 text-sm text-green-700 dark:bg-green-950 dark:text-green-300">
            <p className="font-medium">Open Regions ({openRegions.size}):</p>
            <p className="mt-1">{Array.from(openRegions).join(", ")}</p>
          </div>
        )}

        <div>
          <Label>Notes</Label>
          <Textarea name="notes" placeholder="Referral source, experience, etc." />
        </div>
      </FormDialog>

      {/* Suspend / Terminate Dialogs */}
      <FormDialog
        open={!!showSuspend}
        onClose={() => setShowSuspend(null)}
        title="Suspend Remote Agent"
        description="Commission accrual will be frozen. Existing tenants are not affected."
        onSubmit={(e) => { e.preventDefault(); const d = new FormData(e.target as HTMLFormElement); suspendMut.mutate({ agent_id: showSuspend!, reason: d.get("reason") as string }); }}
        submitLabel="Suspend"
        loading={suspendMut.isPending}
      >
        <div><Label>Reason</Label><Textarea name="reason" required /></div>
      </FormDialog>

      <FormDialog
        open={!!showTerminate}
        onClose={() => setShowTerminate(null)}
        title="Terminate Remote Agent"
        description="Permanent removal. Accrued commission will be settled."
        onSubmit={(e) => { e.preventDefault(); const d = new FormData(e.target as HTMLFormElement); terminateMut.mutate({ agent_id: showTerminate!, reason: d.get("reason") as string }); }}
        submitLabel="Terminate"
        loading={terminateMut.isPending}
      >
        <div className="mb-3 flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Termination is permanent and cannot be reversed.</span>
        </div>
        <div><Label>Reason</Label><Textarea name="reason" required /></div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
