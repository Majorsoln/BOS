"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import {
  Button, Card, CardContent, CardHeader, CardTitle,
  Badge, Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
  Input,
} from "@/components/ui";
import { getAgent, suspendAgent, reinstateAgent, terminateAgent, grantGovernance, revokeGovernance } from "@/lib/api/agents";
import { formatDate } from "@/lib/utils";
import {
  Users, DollarSign, Shield, TrendingUp, Pause, Play, XCircle,
  ArrowLeft, FileText, AlertTriangle,
} from "lucide-react";
import Link from "next/link";

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);
  const [showSuspend, setShowSuspend] = useState(false);
  const [showTerminate, setShowTerminate] = useState(false);
  const [suspendReason, setSuspendReason] = useState("");
  const [terminateReason, setTerminateReason] = useState("");

  const query = useQuery({
    queryKey: ["saas", "agents", id],
    queryFn: () => getAgent(id),
    enabled: !!id,
  });

  const agent = query.data?.data;

  const suspendMut = useMutation({
    mutationFn: () => suspendAgent({ agent_id: id, reason: suspendReason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saas", "agents", id] });
      setShowSuspend(false);
      setToast({ message: "Agent suspended", variant: "success" });
    },
  });

  const reinstateMut = useMutation({
    mutationFn: () => reinstateAgent({ agent_id: id }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saas", "agents", id] });
      setToast({ message: "Agent reinstated", variant: "success" });
    },
  });

  const terminateMut = useMutation({
    mutationFn: () => terminateAgent({ agent_id: id, reason: terminateReason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saas", "agents", id] });
      setShowTerminate(false);
      setToast({ message: "Agent terminated", variant: "success" });
    },
  });

  if (query.isLoading) return <div className="p-8 text-center text-bos-silver-dark">Loading agent...</div>;
  if (!agent) return <div className="p-8 text-center text-bos-silver-dark">Agent not found</div>;

  const isRLA = agent.agent_type === "REGION_LICENSE_AGENT";
  const agentTypeLabel = isRLA ? "Region License Agent" : "Remote Agent";
  const backHref = isRLA ? "/platform/agents/rla" : "/platform/agents/remote";

  const activeTenants = (agent.tenants ?? []).filter((t: { is_active: boolean }) => t.is_active).length;
  const totalCommission = parseFloat(agent.total_commission_earned || "0");
  const pendingCommission = parseFloat(agent.pending_commission || "0");

  return (
    <div>
      <Link href={backHref} className="mb-4 inline-flex items-center gap-1 text-sm text-bos-purple hover:underline">
        <ArrowLeft className="h-4 w-4" /> Back to {agentTypeLabel}s
      </Link>

      <PageHeader
        title={agent.agent_name}
        description={`${agentTypeLabel} — ${agent.contact_email}`}
        action={
          <div className="flex gap-2">
            {agent.status === "ACTIVE" && (
              <Button variant="outline" size="sm" onClick={() => setShowSuspend(true)}>
                <Pause className="mr-1 h-4 w-4" /> Suspend
              </Button>
            )}
            {agent.status === "SUSPENDED" && (
              <Button variant="outline" size="sm" onClick={() => reinstateMut.mutate()}>
                <Play className="mr-1 h-4 w-4" /> Reinstate
              </Button>
            )}
            {agent.status !== "TERMINATED" && (
              <Button variant="destructive" size="sm" onClick={() => setShowTerminate(true)}>
                <XCircle className="mr-1 h-4 w-4" /> Terminate
              </Button>
            )}
          </div>
        }
      />

      {toast && (
        <div className={`mb-4 rounded-md p-3 text-sm ${toast.variant === "success" ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}>
          {toast.message}
          <button onClick={() => setToast(null)} className="ml-2 font-bold">x</button>
        </div>
      )}

      {/* Key Stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Status" value={agent.status} icon={Shield} />
        <StatCard title="Active Tenants" value={activeTenants} icon={Users} />
        <StatCard title="Total Earned" value={totalCommission.toLocaleString()} icon={TrendingUp} />
        <StatCard title="Pending Payout" value={pendingCommission.toLocaleString()} icon={DollarSign} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Profile Card */}
        <Card>
          <CardHeader><CardTitle>Profile</CardTitle></CardHeader>
          <CardContent>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-bos-silver-dark">Agent Type</dt>
                <dd><Badge variant="purple">{agentTypeLabel}</Badge></dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-bos-silver-dark">Status</dt>
                <dd><StatusBadge status={agent.status} /></dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-bos-silver-dark">Contact Person</dt>
                <dd>{agent.contact_person || "—"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-bos-silver-dark">Email</dt>
                <dd>{agent.contact_email}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-bos-silver-dark">Phone</dt>
                <dd>{agent.contact_phone || "—"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-bos-silver-dark">Tier</dt>
                <dd><Badge variant={agent.tier === "GOLD" ? "warning" : "outline"}>{agent.tier}</Badge></dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-bos-silver-dark">Commission Rate</dt>
                <dd className="font-mono">{(parseFloat(agent.commission_rate || "0") * 100).toFixed(0)}%</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-bos-silver-dark">Regions</dt>
                <dd className="flex flex-wrap gap-1">
                  {(agent.region_codes ?? []).map((r: string) => (
                    <Badge key={r} variant="outline">{r}</Badge>
                  ))}
                  {(!agent.region_codes || agent.region_codes.length === 0) && "—"}
                </dd>
              </div>
              {agent.territory && (
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Territory</dt>
                  <dd><Badge variant="purple">{agent.territory}</Badge></dd>
                </div>
              )}
              {isRLA && agent.license_number && (
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">License Number</dt>
                  <dd className="font-mono text-xs">{agent.license_number}</dd>
                </div>
              )}
              {isRLA && agent.market_share_pct != null && (
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Market Share</dt>
                  <dd className="font-mono">{agent.market_share_pct}%</dd>
                </div>
              )}
              {isRLA && agent.max_platform_discount_pct != null && (
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Max Platform Discount</dt>
                  <dd className="font-mono">{agent.max_platform_discount_pct}%</dd>
                </div>
              )}
              {isRLA && agent.max_trial_days != null && (
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Max Trial Days</dt>
                  <dd className="font-mono">{agent.max_trial_days}</dd>
                </div>
              )}
            </dl>
          </CardContent>
        </Card>

        {/* Governance Card */}
        <Card>
          <CardHeader><CardTitle>Governance</CardTitle></CardHeader>
          <CardContent>
            {agent.governance ? (
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Governance Role</dt>
                  <dd><Badge variant="purple">{agent.governance.governance_role}</Badge></dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Governance Status</dt>
                  <dd><StatusBadge status={agent.governance.governance_status} /></dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Can File Taxes</dt>
                  <dd>{agent.governance.can_file_taxes ? "Yes" : "No"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Can Appoint Sub-agents</dt>
                  <dd>{agent.governance.can_appoint_sub_agents ? "Yes" : "No"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Max Tenants</dt>
                  <dd className="font-mono">{agent.governance.max_tenants || "Unlimited"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Training Completed</dt>
                  <dd>{agent.governance.compliance_training_completed ? "Yes" : "Pending"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Last Audit</dt>
                  <dd>{agent.governance.last_audit_date || "Never"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-bos-silver-dark">Next Audit Due</dt>
                  <dd>{agent.governance.next_audit_due || "Not scheduled"}</dd>
                </div>
                <div>
                  <dt className="mb-2 text-bos-silver-dark">Permissions ({agent.governance.permissions?.length ?? 0})</dt>
                  <dd className="flex flex-wrap gap-1">
                    {(agent.governance.permissions ?? []).map((p: { permission_code: string }) => (
                      <Badge key={p.permission_code} variant="outline" className="text-xs">
                        {p.permission_code.replace(/_/g, " ")}
                      </Badge>
                    ))}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-bos-silver-dark">
                No governance role assigned. This agent operates as a standard remote agent.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tenants */}
      <Card className="mt-6">
        <CardHeader><CardTitle>Attributed Tenants ({(agent.tenants ?? []).length})</CardTitle></CardHeader>
        <CardContent className="p-0">
          {(agent.tenants ?? []).length === 0 ? (
            <div className="p-6 text-center text-sm text-bos-silver-dark">No tenants attributed to this agent yet</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Business ID</TableHead>
                  <TableHead className="text-center">Active</TableHead>
                  <TableHead>Linked At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(agent.tenants ?? []).map((t: { business_id: string; is_active: boolean; linked_at: string }) => (
                  <TableRow key={t.business_id}>
                    <TableCell className="font-mono text-sm">{t.business_id}</TableCell>
                    <TableCell className="text-center">
                      <StatusBadge status={t.is_active ? "ACTIVE" : "INACTIVE"} />
                    </TableCell>
                    <TableCell className="text-sm text-bos-silver-dark">{formatDate(t.linked_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Commission History */}
      <Card className="mt-6">
        <CardHeader><CardTitle>Commission History (Last 20)</CardTitle></CardHeader>
        <CardContent className="p-0">
          {(agent.commission_history ?? []).length === 0 ? (
            <div className="p-6 text-center text-sm text-bos-silver-dark">No commission records yet</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead className="text-center">Type</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(agent.commission_history ?? []).map((c: { amount: string; currency: string; period: string; is_clawback: boolean }, i: number) => (
                  <TableRow key={i}>
                    <TableCell className="font-mono text-sm">{c.period}</TableCell>
                    <TableCell className={`text-right font-mono ${c.is_clawback ? "text-red-600" : ""}`}>
                      {c.is_clawback ? "-" : ""}{parseFloat(c.amount).toLocaleString()}
                    </TableCell>
                    <TableCell>{c.currency}</TableCell>
                    <TableCell className="text-center">
                      {c.is_clawback ? (
                        <Badge variant="destructive">Clawback</Badge>
                      ) : (
                        <Badge variant="success">Commission</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Payouts */}
      <Card className="mt-6">
        <CardHeader><CardTitle>Payouts</CardTitle></CardHeader>
        <CardContent className="p-0">
          {(agent.payouts ?? []).length === 0 ? (
            <div className="p-6 text-center text-sm text-bos-silver-dark">No payout records</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Payout ID</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(agent.payouts ?? []).map((p: { payout_id: string; amount: string; currency: string; status: string }) => (
                  <TableRow key={p.payout_id}>
                    <TableCell className="font-mono text-xs">{p.payout_id}</TableCell>
                    <TableCell className="text-right font-mono">{parseFloat(p.amount).toLocaleString()}</TableCell>
                    <TableCell>{p.currency}</TableCell>
                    <TableCell className="text-center"><StatusBadge status={p.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Suspend Dialog */}
      <Dialog open={showSuspend} onOpenChange={setShowSuspend}>
        <DialogContent>
          <DialogHeader><DialogTitle>Suspend Agent</DialogTitle></DialogHeader>
          <p className="text-sm text-bos-silver-dark">This will suspend {agent.agent_name} from all operations.</p>
          <Input placeholder="Reason for suspension" value={suspendReason} onChange={(e) => setSuspendReason(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSuspend(false)}>Cancel</Button>
            <Button variant="destructive" onClick={() => suspendMut.mutate()} disabled={!suspendReason || suspendMut.isPending}>
              {suspendMut.isPending ? "Suspending..." : "Suspend"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Terminate Dialog */}
      <Dialog open={showTerminate} onOpenChange={setShowTerminate}>
        <DialogContent>
          <DialogHeader><DialogTitle>Terminate Agent</DialogTitle></DialogHeader>
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
            <AlertTriangle className="mb-1 inline h-4 w-4" /> This action is irreversible. The agent will lose all governance roles and cannot be reinstated.
          </div>
          <Input placeholder="Reason for termination" value={terminateReason} onChange={(e) => setTerminateReason(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTerminate(false)}>Cancel</Button>
            <Button variant="destructive" onClick={() => terminateMut.mutate()} disabled={!terminateReason || terminateMut.isPending}>
              {terminateMut.isPending ? "Terminating..." : "Terminate"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
