"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge, Textarea,
} from "@/components/ui";
import {
  getAgents, registerAgent, promoteToRegional, suspendAgent, reinstateAgent,
  terminateAgent, getAgentPayouts, approvePayout, getTransferRequests,
  approveTransfer, denyTransfer, getCostShareRequests, decideCostShare,
  getCommissionRanges, setCommissionRanges,
} from "@/lib/api/agents";
import { REGIONS, AGENT_TYPES, DEFAULT_COMMISSION_RANGES, PAYOUT_METHODS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import {
  UserPlus, UserCheck, Shield, XCircle, Play, Globe, Building2,
  DollarSign, ArrowLeftRight, Percent, AlertTriangle, Check, X,
} from "lucide-react";

type TabKey = "list" | "register" | "commissions" | "payouts" | "transfers" | "cost-share";

export default function AgentManagementPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("list");
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const tabs: { key: TabKey; label: string }[] = [
    { key: "list", label: "Agent List" },
    { key: "register", label: "Register Agent" },
    { key: "commissions", label: "Commission Settings" },
    { key: "payouts", label: "Payouts" },
    { key: "transfers", label: "Transfers" },
    { key: "cost-share", label: "Cost-Share Requests" },
  ];

  return (
    <div>
      <PageHeader
        title="Agent Management"
        description="Register, manage, promote, and compensate agents"
      />

      <div className="mb-6 flex gap-1 rounded-lg bg-bos-silver-light p-1 dark:bg-neutral-800 w-fit flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-white text-bos-purple shadow-sm dark:bg-neutral-900"
                : "text-bos-silver-dark hover:text-neutral-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "list" && <AgentList onToast={setToast} />}
      {activeTab === "register" && <RegisterAgent onToast={setToast} />}
      {activeTab === "commissions" && <CommissionSettings onToast={setToast} />}
      {activeTab === "payouts" && <PayoutsList onToast={setToast} />}
      {activeTab === "transfers" && <TransfersList onToast={setToast} />}
      {activeTab === "cost-share" && <CostShareList onToast={setToast} />}

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

type ToastFn = (t: { message: string; variant: "success" | "error" }) => void;

/* ── Agent List ──────────────────────────────────────────── */

function AgentList({ onToast }: { onToast: ToastFn }) {
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showPromote, setShowPromote] = useState<string | null>(null);
  const [showSuspend, setShowSuspend] = useState<string | null>(null);
  const [showTerminate, setShowTerminate] = useState<string | null>(null);

  const agents = useQuery({
    queryKey: ["saas", "agents", typeFilter, statusFilter],
    queryFn: () => getAgents({
      type: typeFilter || undefined,
      status: statusFilter || undefined,
    }),
  });

  const promoteMut = useMutation({
    mutationFn: promoteToRegional,
    onSuccess: () => { setShowPromote(null); onToast({ message: "Agent promoted to Regional", variant: "success" }); queryClient.invalidateQueries({ queryKey: ["saas", "agents"] }); },
    onError: () => onToast({ message: "Failed to promote agent", variant: "error" }),
  });

  const suspendMut = useMutation({
    mutationFn: suspendAgent,
    onSuccess: () => { setShowSuspend(null); onToast({ message: "Agent suspended", variant: "success" }); queryClient.invalidateQueries({ queryKey: ["saas", "agents"] }); },
    onError: () => onToast({ message: "Failed to suspend", variant: "error" }),
  });

  const reinstateMut = useMutation({
    mutationFn: reinstateAgent,
    onSuccess: () => { onToast({ message: "Agent reinstated", variant: "success" }); queryClient.invalidateQueries({ queryKey: ["saas", "agents"] }); },
    onError: () => onToast({ message: "Failed to reinstate", variant: "error" }),
  });

  const terminateMut = useMutation({
    mutationFn: terminateAgent,
    onSuccess: () => { setShowTerminate(null); onToast({ message: "Agent terminated", variant: "success" }); queryClient.invalidateQueries({ queryKey: ["saas", "agents"] }); },
    onError: () => onToast({ message: "Failed to terminate", variant: "error" }),
  });

  const agentList = agents.data?.data ?? [];

  function handlePromote(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    promoteMut.mutate({
      agent_id: showPromote!,
      territory: d.get("territory") as string,
      regional_override_pct: Number(d.get("regional_override_pct")),
      office_address: d.get("office_address") as string,
      agreement_start_date: d.get("agreement_start_date") as string,
      agreement_duration_months: Number(d.get("agreement_duration_months")),
    });
  }

  function handleSuspend(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    suspendMut.mutate({ agent_id: showSuspend!, reason: d.get("reason") as string });
  }

  function handleTerminate(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    terminateMut.mutate({ agent_id: showTerminate!, reason: d.get("reason") as string });
  }

  return (
    <>
      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-40">
          <option value="">All Types</option>
          {AGENT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </Select>
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
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Agent</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Territory</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Tenants</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Joined</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Actions</th>
                </tr>
              </thead>
              <tbody>
                {agentList.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-bos-silver-dark">No agents found</td></tr>
                )}
                {agentList.map((a: {
                  agent_id: string; agent_name: string; agent_type: string;
                  territory?: string; status: string; tenant_count?: number;
                  contact_email: string; created_at?: string;
                }) => (
                  <tr key={a.agent_id} className="border-b border-bos-silver/10 hover:bg-bos-silver-light/50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium">{a.agent_name}</p>
                        <p className="text-xs text-bos-silver-dark">{a.contact_email}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={a.agent_type === "REGIONAL" ? "purple" : "outline"}>
                        {a.agent_type === "REGIONAL" && <Building2 className="mr-1 inline h-3 w-3" />}
                        {a.agent_type === "GLOBAL" && <Globe className="mr-1 inline h-3 w-3" />}
                        {a.agent_type}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-bos-silver-dark">{a.territory ?? "—"}</td>
                    <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                    <td className="px-4 py-3 text-right font-mono">{a.tenant_count ?? 0}</td>
                    <td className="px-4 py-3 text-bos-silver-dark">{formatDate(a.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        {a.agent_type === "GLOBAL" && a.status === "ACTIVE" && (
                          <Button size="sm" variant="outline" onClick={() => setShowPromote(a.agent_id)} title="Promote to Regional">
                            <Building2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
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
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Promote to Regional Dialog */}
      <FormDialog
        open={!!showPromote}
        onClose={() => setShowPromote(null)}
        title="Promote to Regional Agent"
        description="Convert this Global Agent to a Regional Agent with territory and override commission."
        onSubmit={handlePromote}
        submitLabel="Promote"
        loading={promoteMut.isPending}
        wide
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="territory">Territory</Label>
            <Select id="territory" name="territory" className="mt-1" required>
              <option value="">Select country...</option>
              {REGIONS.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="regional_override_pct">Regional Override %</Label>
            <Input id="regional_override_pct" name="regional_override_pct" type="number" min={1} max={15} defaultValue={7} required className="mt-1" />
          </div>
          <div className="col-span-2">
            <Label htmlFor="office_address">Office Address</Label>
            <Input id="office_address" name="office_address" required className="mt-1" placeholder="Physical office address in territory" />
          </div>
          <div>
            <Label htmlFor="agreement_start_date">Agreement Start Date</Label>
            <Input id="agreement_start_date" name="agreement_start_date" type="date" required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="agreement_duration_months">Duration (months)</Label>
            <Input id="agreement_duration_months" name="agreement_duration_months" type="number" min={6} max={60} defaultValue={12} required className="mt-1" />
          </div>
        </div>
      </FormDialog>

      {/* Suspend Dialog */}
      <FormDialog
        open={!!showSuspend}
        onClose={() => setShowSuspend(null)}
        title="Suspend Agent"
        description="Agent will lose dashboard access. Tenants will not be affected. Commission accrual is frozen."
        onSubmit={handleSuspend}
        submitLabel="Suspend"
        loading={suspendMut.isPending}
      >
        <div>
          <Label htmlFor="suspend_reason">Reason</Label>
          <Textarea id="suspend_reason" name="reason" required className="mt-1" placeholder="Reason for suspension..." />
        </div>
      </FormDialog>

      {/* Terminate Dialog */}
      <FormDialog
        open={!!showTerminate}
        onClose={() => setShowTerminate(null)}
        title="Terminate Agent"
        description="This is permanent and cannot be reversed. Tenants will be asked to choose a new agent. Accrued commission up to today will be paid out."
        onSubmit={handleTerminate}
        submitLabel="Terminate"
        loading={terminateMut.isPending}
      >
        <div className="mb-3 flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Termination is permanent. The agent will lose all future commission. Accrued unpaid commission will be settled.</span>
        </div>
        <div>
          <Label htmlFor="terminate_reason">Reason</Label>
          <Textarea id="terminate_reason" name="reason" required className="mt-1" placeholder="Reason for termination..." />
        </div>
      </FormDialog>
    </>
  );
}

/* ── Register Agent ──────────────────────────────────────── */

function RegisterAgent({ onToast }: { onToast: ToastFn }) {
  const queryClient = useQueryClient();

  const registerMut = useMutation({
    mutationFn: registerAgent,
    onSuccess: () => { onToast({ message: "Agent registered (probation)", variant: "success" }); queryClient.invalidateQueries({ queryKey: ["saas", "agents"] }); },
    onError: () => onToast({ message: "Failed to register agent", variant: "error" }),
  });

  function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    registerMut.mutate({
      agent_name: d.get("agent_name") as string,
      contact_email: d.get("contact_email") as string,
      contact_phone: d.get("contact_phone") as string,
      country: d.get("country") as string,
      agent_type: "GLOBAL",
      notes: (d.get("notes") as string) || undefined,
    });
    form.reset();
  }

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-bos-purple" />
            <CardTitle>Register New Agent</CardTitle>
          </div>
          <p className="text-xs text-bos-silver-dark mt-1">
            New agents start as Global Agents in PROBATION status. They must onboard 5 tenants within 90 days.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <Label htmlFor="agent_name">Agent Name</Label>
              <Input id="agent_name" name="agent_name" required className="mt-1" placeholder="Individual or company name" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="contact_email">Email</Label>
                <Input id="contact_email" name="contact_email" type="email" required className="mt-1" />
              </div>
              <div>
                <Label htmlFor="contact_phone">Phone</Label>
                <Input id="contact_phone" name="contact_phone" required className="mt-1" placeholder="+254..." />
              </div>
            </div>
            <div>
              <Label htmlFor="country">Country</Label>
              <Select id="country" name="country" className="mt-1" required>
                <option value="">Select country...</option>
                {REGIONS.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
              </Select>
            </div>
            <div>
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea id="notes" name="notes" className="mt-1" placeholder="Internal notes about this agent..." />
            </div>
            <Button type="submit" disabled={registerMut.isPending} className="w-full">
              {registerMut.isPending ? "Registering..." : "Register Agent"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Commission Settings ─────────────────────────────────── */

function CommissionSettings({ onToast }: { onToast: ToastFn }) {
  const queryClient = useQueryClient();
  const commissionsQuery = useQuery({ queryKey: ["saas", "commission-ranges"], queryFn: getCommissionRanges });

  const saveMut = useMutation({
    mutationFn: setCommissionRanges,
    onSuccess: () => { onToast({ message: "Commission ranges saved", variant: "success" }); queryClient.invalidateQueries({ queryKey: ["saas", "commission-ranges"] }); },
    onError: () => onToast({ message: "Failed to save", variant: "error" }),
  });

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    const ranges = DEFAULT_COMMISSION_RANGES.map((r, i) => ({
      min_tenants: r.min_tenants,
      max_tenants: r.max_tenants,
      rate_pct: Number(d.get(`rate_${i}`)),
    }));
    saveMut.mutate({
      ranges,
      residual_rate_pct: Number(d.get("residual_rate_pct")),
      first_year_bonus_pct: Number(d.get("first_year_bonus_pct")),
    });
  }

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Percent className="h-5 w-5 text-bos-purple" />
            <CardTitle>Commission Ranges</CardTitle>
          </div>
          <p className="text-xs text-bos-silver-dark mt-1">
            Volume-based commission rates applied to all agents. Agent earns commission only after platform collects payment from tenant.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            {DEFAULT_COMMISSION_RANGES.map((r, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-sm w-32 text-bos-silver-dark">{r.min_tenants}–{r.max_tenants > 999 ? "∞" : r.max_tenants} tenants</span>
                <Input name={`rate_${i}`} type="number" min={1} max={50} defaultValue={r.rate_pct} className="w-20" />
                <span className="text-sm text-bos-silver-dark">%</span>
              </div>
            ))}
            <div className="border-t border-bos-silver/20 pt-4 space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-sm w-32 text-bos-silver-dark">Residual rate</span>
                <Input name="residual_rate_pct" type="number" min={0} max={10} defaultValue={3} className="w-20" />
                <span className="text-sm text-bos-silver-dark">% (permanent, after tenant transfer)</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm w-32 text-bos-silver-dark">First year bonus</span>
                <Input name="first_year_bonus_pct" type="number" min={0} max={10} defaultValue={0} className="w-20" />
                <span className="text-sm text-bos-silver-dark">% (extra for first 12 months)</span>
              </div>
            </div>
            <Button type="submit" disabled={saveMut.isPending} className="w-full">
              {saveMut.isPending ? "Saving..." : "Save Commission Settings"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Payouts ─────────────────────────────────────────────── */

function PayoutsList({ onToast }: { onToast: ToastFn }) {
  const queryClient = useQueryClient();
  const payouts = useQuery({ queryKey: ["saas", "payouts"], queryFn: () => getAgentPayouts() });

  const approveMut = useMutation({
    mutationFn: approvePayout,
    onSuccess: () => { onToast({ message: "Payout approved", variant: "success" }); queryClient.invalidateQueries({ queryKey: ["saas", "payouts"] }); },
    onError: () => onToast({ message: "Failed to approve payout", variant: "error" }),
  });

  const payoutList = payouts.data?.data ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-bos-purple" />
          <CardTitle className="text-base">Commission Payouts</CardTitle>
        </div>
        <p className="text-xs text-bos-silver-dark mt-1">
          Agent commission is paid out AFTER platform collects from tenant. Review and approve pending payouts.
        </p>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Agent</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Period</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Amount</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Method</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Action</th>
              </tr>
            </thead>
            <tbody>
              {payoutList.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-bos-silver-dark">No pending payouts</td></tr>
              )}
              {payoutList.map((p: {
                payout_id: string; agent_name: string; period: string;
                amount: number; currency: string; method: string; status: string;
              }) => (
                <tr key={p.payout_id} className="border-b border-bos-silver/10">
                  <td className="px-4 py-3 font-medium">{p.agent_name}</td>
                  <td className="px-4 py-3 text-bos-silver-dark">{p.period}</td>
                  <td className="px-4 py-3 text-right font-mono">{p.currency} {p.amount?.toLocaleString()}</td>
                  <td className="px-4 py-3">{p.method}</td>
                  <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3 text-right">
                    {p.status === "PENDING" && (
                      <Button size="sm" onClick={() => approveMut.mutate({ payout_id: p.payout_id })} disabled={approveMut.isPending}>
                        <Check className="mr-1 h-3.5 w-3.5" /> Approve
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

/* ── Transfers ───────────────────────────────────────────── */

function TransfersList({ onToast }: { onToast: ToastFn }) {
  const queryClient = useQueryClient();
  const [showDeny, setShowDeny] = useState<string | null>(null);
  const transfers = useQuery({ queryKey: ["saas", "transfers"], queryFn: () => getTransferRequests() });

  const approveMut = useMutation({
    mutationFn: approveTransfer,
    onSuccess: () => { onToast({ message: "Transfer approved", variant: "success" }); queryClient.invalidateQueries({ queryKey: ["saas", "transfers"] }); },
    onError: () => onToast({ message: "Failed to approve", variant: "error" }),
  });

  const denyMut = useMutation({
    mutationFn: denyTransfer,
    onSuccess: () => { setShowDeny(null); onToast({ message: "Transfer denied", variant: "success" }); queryClient.invalidateQueries({ queryKey: ["saas", "transfers"] }); },
    onError: () => onToast({ message: "Failed to deny", variant: "error" }),
  });

  const transferList = transfers.data?.data ?? [];

  function handleDeny(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    denyMut.mutate({ transfer_id: showDeny!, reason: d.get("reason") as string });
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ArrowLeftRight className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Tenant Transfer Requests</CardTitle>
          </div>
          <p className="text-xs text-bos-silver-dark mt-1">
            When a tenant requests to switch agents and the current agent refuses, the request escalates here.
            Original agent keeps earning until agreement period expires, plus permanent residual.
          </p>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Tenant</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">From Agent</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">To Agent</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Reason</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Actions</th>
                </tr>
              </thead>
              <tbody>
                {transferList.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-bos-silver-dark">No pending transfers</td></tr>
                )}
                {transferList.map((t: {
                  transfer_id: string; tenant_name: string; from_agent: string;
                  to_agent: string; reason: string; status: string;
                }) => (
                  <tr key={t.transfer_id} className="border-b border-bos-silver/10">
                    <td className="px-4 py-3 font-medium">{t.tenant_name}</td>
                    <td className="px-4 py-3">{t.from_agent}</td>
                    <td className="px-4 py-3">{t.to_agent}</td>
                    <td className="px-4 py-3 text-xs text-bos-silver-dark max-w-xs truncate">{t.reason}</td>
                    <td className="px-4 py-3"><StatusBadge status={t.status} /></td>
                    <td className="px-4 py-3 text-right">
                      {t.status === "PENDING" && (
                        <div className="flex justify-end gap-1">
                          <Button size="sm" onClick={() => approveMut.mutate({ transfer_id: t.transfer_id })} disabled={approveMut.isPending}>
                            <Check className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => setShowDeny(t.transfer_id)}>
                            <X className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <FormDialog
        open={!!showDeny}
        onClose={() => setShowDeny(null)}
        title="Deny Transfer"
        onSubmit={handleDeny}
        submitLabel="Deny Transfer"
        loading={denyMut.isPending}
      >
        <div>
          <Label htmlFor="deny_reason">Reason</Label>
          <Textarea id="deny_reason" name="reason" required className="mt-1" />
        </div>
      </FormDialog>
    </>
  );
}

/* ── Cost-Share Requests ─────────────────────────────────── */

function CostShareList({ onToast }: { onToast: ToastFn }) {
  const queryClient = useQueryClient();
  const requests = useQuery({ queryKey: ["saas", "cost-share"], queryFn: () => getCostShareRequests() });
  const [showDecide, setShowDecide] = useState<string | null>(null);

  const decideMut = useMutation({
    mutationFn: decideCostShare,
    onSuccess: () => { setShowDecide(null); onToast({ message: "Decision saved", variant: "success" }); queryClient.invalidateQueries({ queryKey: ["saas", "cost-share"] }); },
    onError: () => onToast({ message: "Failed to save decision", variant: "error" }),
  });

  const requestList = requests.data?.data ?? [];

  function handleDecide(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    decideMut.mutate({
      request_id: showDecide!,
      decision: d.get("decision") as "APPROVED" | "ADJUSTED" | "REJECTED",
      platform_share_pct: Number(d.get("platform_share_pct")) || undefined,
      notes: (d.get("notes") as string) || undefined,
    });
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Percent className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Promotion Cost-Share Requests</CardTitle>
          </div>
          <p className="text-xs text-bos-silver-dark mt-1">
            Agents can request the platform to share promotion costs. Platform promotions never affect agent margin.
          </p>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Agent</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Description</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Cost</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Requested Share</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Action</th>
                </tr>
              </thead>
              <tbody>
                {requestList.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-bos-silver-dark">No requests</td></tr>
                )}
                {requestList.map((r: {
                  request_id: string; agent_name: string; description: string;
                  total_cost: number; currency: string; requested_share_pct: number; status: string;
                }) => (
                  <tr key={r.request_id} className="border-b border-bos-silver/10">
                    <td className="px-4 py-3 font-medium">{r.agent_name}</td>
                    <td className="px-4 py-3 text-xs max-w-xs truncate">{r.description}</td>
                    <td className="px-4 py-3 text-right font-mono">{r.currency} {r.total_cost?.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">{r.requested_share_pct}%</td>
                    <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                    <td className="px-4 py-3 text-right">
                      {r.status === "PENDING" && (
                        <Button size="sm" variant="outline" onClick={() => setShowDecide(r.request_id)}>
                          Review
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <FormDialog
        open={!!showDecide}
        onClose={() => setShowDecide(null)}
        title="Review Cost-Share Request"
        onSubmit={handleDecide}
        submitLabel="Submit Decision"
        loading={decideMut.isPending}
      >
        <div>
          <Label htmlFor="cs_decision">Decision</Label>
          <Select id="cs_decision" name="decision" className="mt-1" required>
            <option value="APPROVED">Approve (as requested)</option>
            <option value="ADJUSTED">Adjust (change share %)</option>
            <option value="REJECTED">Reject</option>
          </Select>
        </div>
        <div>
          <Label htmlFor="cs_platform_share">Platform Share % (for adjustments)</Label>
          <Input id="cs_platform_share" name="platform_share_pct" type="number" min={0} max={100} className="mt-1" />
        </div>
        <div>
          <Label htmlFor="cs_notes">Notes</Label>
          <Textarea id="cs_notes" name="notes" className="mt-1" />
        </div>
      </FormDialog>
    </>
  );
}
