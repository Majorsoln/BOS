"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { FormDialog } from "@/components/shared/form-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Button, Card, CardContent, CardHeader, CardTitle,
  Input, Label, Select, Toast, Badge, Textarea,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import {
  getAgents, registerAgent, suspendAgent, reinstateAgent,
  terminateAgentReversible, terminateAgentPermanent,
  reinstateAgentFull, reinstateAgentReduced,
  generateAgentContract, getPendingRlaRegions,
  listAgentHealthScores,
} from "@/lib/api/agents";
import { useRegions } from "@/hooks/use-regions";
import { formatDate } from "@/lib/utils";
import {
  Shield, MapPin, Plus, XCircle, Play, AlertTriangle, Users,
  Percent, FileText, RotateCcw, Ban, TrendingDown, Clock,
} from "lucide-react";
import Link from "next/link";

type ToastState = { message: string; variant: "success" | "error" } | null;

type TerminationMode = "reversible" | "permanent" | null;

export default function RegionLicenseAgentsPage() {
  const qc = useQueryClient();
  const [toast, setToast] = useState<ToastState>(null);
  const [showAppoint, setShowAppoint] = useState(false);
  const [showSuspend, setShowSuspend] = useState<string | null>(null);
  const [showTerminate, setShowTerminate] = useState<{ agent_id: string; mode: TerminationMode } | null>(null);
  const [showReinstate, setShowReinstate] = useState<{ agent_id: string; mode: "full" | "reduced" } | null>(null);
  const [showContract, setShowContract] = useState<string | null>(null); // agent_id for contract generation

  const agentsQuery = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });

  const pendingQuery = useQuery({
    queryKey: ["saas", "regions", "pending-rla"],
    queryFn: getPendingRlaRegions,
  });

  const now = new Date();
  const currentPeriod = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const healthQuery = useQuery({
    queryKey: ["saas", "agents", "health-scores", currentPeriod],
    queryFn: () => listAgentHealthScores({ period: currentPeriod }),
  });

  const appointMut = useMutation({
    mutationFn: registerAgent,
    onSuccess: (data) => {
      setShowAppoint(false);
      qc.invalidateQueries({ queryKey: ["saas", "agents"] });
      const license = data?.license_number ? ` License: ${data.license_number}` : "";
      setToast({ message: `RLA appointed successfully.${license}`, variant: "success" });
    },
    onError: () => setToast({ message: "Failed to appoint agent", variant: "error" }),
  });

  const suspendMut = useMutation({
    mutationFn: suspendAgent,
    onSuccess: () => {
      setShowSuspend(null);
      qc.invalidateQueries({ queryKey: ["saas", "agents"] });
      setToast({ message: "Agent suspended", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to suspend agent", variant: "error" }),
  });

  const reinstateFullMut = useMutation({
    mutationFn: reinstateAgentFull,
    onSuccess: () => {
      setShowReinstate(null);
      qc.invalidateQueries({ queryKey: ["saas", "agents"] });
      qc.invalidateQueries({ queryKey: ["saas", "regions", "pending-rla"] });
      setToast({ message: "Agent fully reinstated — original terms restored", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to reinstate agent", variant: "error" }),
  });

  const reinstateReducedMut = useMutation({
    mutationFn: reinstateAgentReduced,
    onSuccess: () => {
      setShowReinstate(null);
      qc.invalidateQueries({ queryKey: ["saas", "agents"] });
      qc.invalidateQueries({ queryKey: ["saas", "regions", "pending-rla"] });
      setToast({ message: "Agent reinstated under reduced commission terms", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to reinstate agent", variant: "error" }),
  });

  const terminateReversibleMut = useMutation({
    mutationFn: terminateAgentReversible,
    onSuccess: () => {
      setShowTerminate(null);
      qc.invalidateQueries({ queryKey: ["saas", "agents"] });
      qc.invalidateQueries({ queryKey: ["saas", "regions", "pending-rla"] });
      setToast({ message: "Agent reversibly terminated — tenants continue service without billing", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to terminate agent", variant: "error" }),
  });

  const terminatePermanentMut = useMutation({
    mutationFn: terminateAgentPermanent,
    onSuccess: () => {
      setShowTerminate(null);
      qc.invalidateQueries({ queryKey: ["saas", "agents"] });
      qc.invalidateQueries({ queryKey: ["saas", "regions", "pending-rla"] });
      setToast({ message: "Agent permanently terminated — licence revoked", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to terminate agent", variant: "error" }),
  });

  const contractMut = useMutation({
    mutationFn: generateAgentContract,
    onSuccess: () => {
      setShowContract(null);
      qc.invalidateQueries({ queryKey: ["saas", "agents"] });
      setToast({ message: "Contract generated — awaiting RLA signature", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to generate contract", variant: "error" }),
  });

  type AgentRow = {
    agent_id: string; agent_name: string; agent_type: string;
    territory?: string; status: string; active_tenant_count?: number;
    contact_email: string; contact_phone?: string; created_at?: string;
    market_share_pct?: number; license_number?: string;
    max_platform_discount_pct?: number; max_trial_days?: number;
    commission_rate?: string; contract_status?: string;
  };

  const agentList: AgentRow[] = agentsQuery.data?.data ?? [];
  const pendingRegions: Array<{ region_code: string; pending_since: string; termination_type: string }> =
    pendingQuery.data?.data ?? [];

  type HealthRow = { agent_id: string; region_code: string; total_score: number; grade: string; overdue_remittances: number; open_escalations: number };
  const healthScores: HealthRow[] = healthQuery.data?.data ?? [];
  const healthByRegion = Object.fromEntries(healthScores.map((h) => [h.region_code, h]));

  const GRADE_DOT: Record<string, string> = {
    GREEN:  "bg-green-500",
    AMBER:  "bg-amber-400",
    ORANGE: "bg-orange-500",
    RED:    "bg-red-600",
    BLACK:  "bg-neutral-900",
  };

  const { regions: allRegions } = useRegions({ onlyActive: true });

  const assignedRegions = new Set(
    agentList.filter((a) => a.status !== "TERMINATED_PERMANENT" && a.status !== "TERMINATED_REVERSIBLE").map((a) => a.territory).filter(Boolean)
  );
  const availableRegions = allRegions.filter((r) => !assignedRegions.has(r.code));

  const activeCount = agentList.filter((a) => a.status === "ACTIVE").length;
  const totalRegions = allRegions.length;

  function handleAppoint(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    appointMut.mutate({
      agent_name: d.get("agent_name") as string,
      contact_email: d.get("contact_email") as string,
      contact_phone: d.get("contact_phone") as string,
      agent_type: "REGION_LICENSE_AGENT",
      territory: d.get("territory") as string,
      contact_person: d.get("contact_person") as string,
      market_share_pct: parseInt(d.get("market_share_pct") as string || "30"),
      max_platform_discount_pct: parseInt(d.get("max_platform_discount_pct") as string || "15"),
      max_trial_days: parseInt(d.get("max_trial_days") as string || "180"),
    } as Parameters<typeof registerAgent>[0] & { market_share_pct: number; max_platform_discount_pct: number; max_trial_days: number });
  }

  function handleContractGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!showContract) return;
    const d = new FormData(e.target as HTMLFormElement);
    const agent = agentList.find((a) => a.agent_id === showContract);
    contractMut.mutate({
      agent_id: showContract,
      agent_name: agent?.agent_name ?? "",
      region_code: agent?.territory ?? "",
      commission_rate: parseFloat(d.get("commission_rate") as string) / 100,
      max_platform_discount_pct: parseInt(d.get("max_platform_discount_pct") as string || "15"),
      max_trial_days: parseInt(d.get("max_trial_days") as string || "180"),
      contract_duration_months: parseInt(d.get("contract_duration_months") as string || "24"),
      monthly_tenant_target: parseInt(d.get("monthly_tenant_target") as string || "0"),
      notes: d.get("notes") as string,
    });
  }

  function getTerminationLabel(status: string) {
    if (status === "TERMINATED_REVERSIBLE") return { label: "Reversible", color: "text-amber-700 bg-amber-50" };
    if (status === "TERMINATED_PERMANENT") return { label: "Permanent", color: "text-red-700 bg-red-50" };
    if (status === "REDUCED_COMMISSION") return { label: "Reduced Rate", color: "text-orange-700 bg-orange-50" };
    return null;
  }

  return (
    <div>
      <PageHeader
        title="Region License Agents"
        description="Each region has exactly one licensed agent — the regional franchisee who manages compliance, collects revenue, and provides local support."
        actions={
          <Button onClick={() => setShowAppoint(true)} className="gap-2" disabled={availableRegions.length === 0}>
            <Plus className="h-4 w-4" />
            Appoint RLA
          </Button>
        }
      />

      {/* Stats row */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active RLAs" value={activeCount} icon={Shield} />
        <StatCard title="Total Regions" value={totalRegions} icon={MapPin} />
        <StatCard title="Uncovered Regions" value={totalRegions - activeCount} icon={AlertTriangle} />
        <StatCard title="Total Tenants (RLA)" value={agentList.reduce((s, a) => s + (a.active_tenant_count ?? 0), 0)} icon={Users} />
      </div>

      {/* Pending-RLA regions alert */}
      {pendingRegions.length > 0 && (
        <Card className="mb-6 border-red-300 bg-red-50 dark:border-red-900 dark:bg-red-950/40">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-red-600" />
              <CardTitle className="text-sm text-red-800 dark:text-red-300">
                {pendingRegions.length} Region{pendingRegions.length > 1 ? "s" : ""} Without Active RLA
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Region</TableHead>
                  <TableHead>Termination Type</TableHead>
                  <TableHead>Pending Since</TableHead>
                  <TableHead className="text-right">Tenant Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pendingRegions.map((r) => {
                  const region = allRegions.find((x) => x.code === r.region_code);
                  return (
                    <TableRow key={r.region_code}>
                      <TableCell>
                        <Badge variant="purple">{r.region_code}</Badge>{" "}
                        <span className="text-sm">{region?.name ?? r.region_code}</span>
                      </TableCell>
                      <TableCell>
                        <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${r.termination_type === "PERMANENT" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                          {r.termination_type}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">
                        {new Date(r.pending_since).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className="text-xs font-medium text-green-700">Continuity Active — No Billing</span>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
            <p className="px-4 pb-3 pt-1 text-xs text-red-700 dark:text-red-400">
              Tenants in these regions continue service without billing until a new RLA is appointed.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Doctrine card */}
      <Card className="mb-6 border-bos-purple/20 bg-bos-purple-light/30">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Shield className="mt-0.5 h-5 w-5 text-bos-purple" />
            <div className="text-sm">
              <p className="font-semibold text-bos-purple">Franchisor Doctrine — One RLA Per Region</p>
              <div className="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2">
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">Regional Commission</p>
                  <p className="text-xs text-bos-silver-dark">RLA earns on ALL tenants in their region — not just ones they onboarded. Compliance responsibility is regional.</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">Guided Autonomy</p>
                  <p className="text-xs text-bos-silver-dark">RLA sets prices, promotions, trial days — within Platform-defined bounds. Platform holds the guardrails.</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">Tenant Continuity</p>
                  <p className="text-xs text-bos-silver-dark">Tenants NEVER lose service due to RLA termination. Billing pauses until a new RLA is assigned.</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-300">Three Termination Outcomes</p>
                  <p className="text-xs text-bos-silver-dark">Reversible (reinstate possible) · Permanent (licence revoked) · Reduced-rate reinstatement (lower share, fixed term)</p>
                </div>
              </div>
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
                  <TableHead>License</TableHead>
                  <TableHead className="text-center">Market Share</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Tenants</TableHead>
                  <TableHead className="text-center">Health</TableHead>
                  <TableHead className="text-center">Contract</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agentList.map((a) => {
                  const region = allRegions.find((r) => r.code === a.territory);
                  const termLabel = getTerminationLabel(a.status);
                  const isTerminated = a.status === "TERMINATED_REVERSIBLE" || a.status === "TERMINATED_PERMANENT";
                  const canReinstate = a.status === "TERMINATED_REVERSIBLE";
                  const canTerminate = !isTerminated && a.status !== "REDUCED_COMMISSION";

                  return (
                    <TableRow key={a.agent_id} className={isTerminated ? "opacity-60" : ""}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Badge variant="purple">{a.territory || "—"}</Badge>
                          <span className="text-sm">{region?.name ?? ""}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Link href={`/platform/agents/${a.agent_id}`} className="font-medium text-bos-purple hover:underline">
                          {a.agent_name}
                        </Link>
                        <p className="text-xs text-bos-silver-dark">{a.contact_email}</p>
                      </TableCell>
                      <TableCell>
                        {a.license_number ? (
                          <span className="font-mono text-xs">{a.license_number}</span>
                        ) : (
                          <span className="text-xs text-bos-silver-dark">Pending</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge variant="outline" className="font-mono">
                          {a.market_share_pct ?? 30}%
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        {termLabel ? (
                          <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${termLabel.color}`}>
                            {termLabel.label}
                          </span>
                        ) : (
                          <StatusBadge status={a.status} />
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono">{a.active_tenant_count ?? 0}</TableCell>
                      <TableCell className="text-center">
                        {a.territory && healthByRegion[a.territory] ? (() => {
                          const h = healthByRegion[a.territory];
                          return (
                            <div className="flex items-center justify-center gap-1.5" title={`Score: ${h.total_score}/100 | Remittance overdue: ${h.overdue_remittances} | Open escalations: ${h.open_escalations}`}>
                              <span className={`inline-block h-2 w-2 rounded-full ${GRADE_DOT[h.grade] ?? "bg-neutral-400"}`} />
                              <span className="font-mono text-xs">{h.total_score}</span>
                            </div>
                          );
                        })() : <span className="text-xs text-bos-silver-dark">—</span>}
                      </TableCell>
                      <TableCell className="text-center">
                        {a.contract_status ? (
                          <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                            a.contract_status === "ACTIVE" ? "bg-green-50 text-green-700" :
                            a.contract_status === "DRAFT" ? "bg-amber-50 text-amber-700" :
                            "bg-neutral-100 text-neutral-500"
                          }`}>
                            {a.contract_status}
                          </span>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-6 text-xs"
                            onClick={() => setShowContract(a.agent_id)}
                            title="Generate contract"
                          >
                            <FileText className="h-3 w-3 mr-1" /> Generate
                          </Button>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          {/* Reinstate options for TERMINATED_REVERSIBLE */}
                          {canReinstate && (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 gap-1 text-xs text-green-700 border-green-300"
                                onClick={() => setShowReinstate({ agent_id: a.agent_id, mode: "full" })}
                                title="Full reinstatement"
                              >
                                <RotateCcw className="h-3 w-3" /> Full
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 gap-1 text-xs text-amber-700 border-amber-300"
                                onClick={() => setShowReinstate({ agent_id: a.agent_id, mode: "reduced" })}
                                title="Reduced-rate reinstatement"
                              >
                                <TrendingDown className="h-3 w-3" /> Reduced
                              </Button>
                            </>
                          )}

                          {/* Suspend */}
                          {(a.status === "ACTIVE" || a.status === "PROBATION" || a.status === "REDUCED_COMMISSION") && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs"
                              onClick={() => setShowSuspend(a.agent_id)}
                              title="Suspend"
                            >
                              <Shield className="h-3.5 w-3.5" />
                            </Button>
                          )}

                          {/* Reinstate from suspension */}
                          {a.status === "SUSPENDED" && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs text-green-700 border-green-300"
                              onClick={() => reinstateFullMut.mutate({ agent_id: a.agent_id })}
                              title="Reinstate"
                            >
                              <Play className="h-3.5 w-3.5" />
                            </Button>
                          )}

                          {/* Terminate options */}
                          {canTerminate && (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 gap-1 text-xs text-amber-700 border-amber-300"
                                onClick={() => setShowTerminate({ agent_id: a.agent_id, mode: "reversible" })}
                                title="Reversible termination"
                              >
                                <XCircle className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                size="sm"
                                variant="destructive"
                                className="h-7 gap-1 text-xs"
                                onClick={() => setShowTerminate({ agent_id: a.agent_id, mode: "permanent" })}
                                title="Permanent termination"
                              >
                                <Ban className="h-3.5 w-3.5" />
                              </Button>
                            </>
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

      {/* ── Appoint RLA Dialog ──────────────────────────────────────────── */}
      <FormDialog
        open={showAppoint}
        onClose={() => setShowAppoint(false)}
        title="Appoint Region License Agent"
        description="Assign an RLA as the regional franchisee. System auto-generates a license number. A franchise contract will be generated separately."
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
                <option key={r.code} value={r.code}>{r.code} — {r.name} ({r.currency})</option>
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
            <Label>Contact Person</Label>
            <Input name="contact_person" required placeholder="Full name" />
          </div>
          <div>
            <Label>Email</Label>
            <Input name="contact_email" type="email" required />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Phone</Label>
            <Input name="contact_phone" required placeholder="+254..." />
          </div>
          <div>
            <Label>Market Share (%)</Label>
            <Input name="market_share_pct" type="number" min="5" max="50" defaultValue="30" required />
            <p className="mt-0.5 text-xs text-bos-silver-dark">% of regional revenue RLA retains</p>
          </div>
        </div>
        <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <h4 className="text-sm font-semibold text-amber-900 flex items-center gap-1.5">
            <Percent className="h-4 w-4" /> Platform Limits for this RLA
          </h4>
          <p className="mt-1 text-xs text-amber-700">Maximum values the RLA can set. RLA configures actual values within these limits.</p>
          <div className="mt-3 grid grid-cols-2 gap-4">
            <div>
              <Label className="text-amber-900">Max Platform-Funded Discount (%)</Label>
              <Input name="max_platform_discount_pct" type="number" min="0" max="50" defaultValue="15" />
            </div>
            <div>
              <Label className="text-amber-900">Max Trial Days</Label>
              <Input name="max_trial_days" type="number" min="0" max="365" defaultValue="180" />
            </div>
          </div>
        </div>
      </FormDialog>

      {/* ── Generate Contract Dialog ────────────────────────────────────── */}
      {showContract && (() => {
        const agent = agentList.find((a) => a.agent_id === showContract);
        return (
          <FormDialog
            open={!!showContract}
            onClose={() => setShowContract(null)}
            title="Generate Franchise Contract"
            description={`Generate a Platform-RLA franchise agreement for ${agent?.agent_name ?? "this RLA"} in region ${agent?.territory ?? ""}. Contract starts as DRAFT — RLA must sign to activate.`}
            onSubmit={handleContractGenerate}
            submitLabel="Generate Contract"
            loading={contractMut.isPending}
            wide
          >
            <div className="mb-3 rounded-lg border border-bos-purple/20 bg-bos-purple-light/20 p-3 text-xs text-bos-purple">
              <strong>Hardcoded platform terms (non-negotiable):</strong> 5-day remittance deadline · Tenant continuity guarantee · Region exclusivity · Platform audit right · Price bound enforcement · Regional compliance ownership
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Commission Rate (%)</Label>
                <Input name="commission_rate" type="number" min="5" max="50" defaultValue={agent?.market_share_pct ?? 30} required />
                <p className="mt-0.5 text-xs text-bos-silver-dark">RLA's share of regional revenue</p>
              </div>
              <div>
                <Label>Contract Duration (months)</Label>
                <Input name="contract_duration_months" type="number" min="6" max="60" defaultValue="24" required />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Max Platform-Funded Discount (%)</Label>
                <Input name="max_platform_discount_pct" type="number" min="0" max="50" defaultValue={agent?.max_platform_discount_pct ?? 15} />
              </div>
              <div>
                <Label>Max Trial Days</Label>
                <Input name="max_trial_days" type="number" min="0" max="365" defaultValue={agent?.max_trial_days ?? 180} />
              </div>
            </div>
            <div>
              <Label>Monthly Tenant Target</Label>
              <Input name="monthly_tenant_target" type="number" min="0" defaultValue="0" />
              <p className="mt-0.5 text-xs text-bos-silver-dark">Performance benchmark (informational)</p>
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea name="notes" placeholder="Any additional contract notes..." />
            </div>
          </FormDialog>
        );
      })()}

      {/* ── Suspend Dialog ──────────────────────────────────────────────── */}
      <FormDialog
        open={!!showSuspend}
        onClose={() => setShowSuspend(null)}
        title="Suspend Region License Agent"
        description="Suspending an RLA freezes their region operations temporarily. Tenants continue service."
        onSubmit={(e) => {
          e.preventDefault();
          const d = new FormData(e.target as HTMLFormElement);
          suspendMut.mutate({ agent_id: showSuspend!, reason: d.get("reason") as string });
        }}
        submitLabel="Suspend Agent"
        loading={suspendMut.isPending}
      >
        <div>
          <Label>Reason for Suspension</Label>
          <Textarea name="reason" required placeholder="Describe the reason for suspension..." />
        </div>
      </FormDialog>

      {/* ── Termination Dialog (Reversible / Permanent) ─────────────────── */}
      {showTerminate && (
        <FormDialog
          open={!!showTerminate}
          onClose={() => setShowTerminate(null)}
          title={showTerminate.mode === "permanent" ? "Permanent Termination" : "Reversible Termination"}
          description={
            showTerminate.mode === "permanent"
              ? "PERMANENT: The licence is revoked forever. This RLA can never be reinstated under any circumstances."
              : "REVERSIBLE: The RLA is terminated but can be reinstated to full terms once the issue is remedied."
          }
          onSubmit={(e) => {
            e.preventDefault();
            const d = new FormData(e.target as HTMLFormElement);
            if (showTerminate.mode === "permanent") {
              terminatePermanentMut.mutate({ agent_id: showTerminate.agent_id, reason: d.get("reason") as string });
            } else {
              terminateReversibleMut.mutate({ agent_id: showTerminate.agent_id, reason: d.get("reason") as string });
            }
          }}
          submitLabel={showTerminate.mode === "permanent" ? "Permanently Terminate" : "Reversibly Terminate"}
          loading={terminatePermanentMut.isPending || terminateReversibleMut.isPending}
        >
          <div className={`mb-3 flex items-start gap-2 rounded-lg p-3 text-sm ${
            showTerminate.mode === "permanent"
              ? "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200"
              : "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200"
          }`}>
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              {showTerminate.mode === "permanent" ? (
                <span><strong>Permanent:</strong> Licence permanently revoked. Cannot be reinstated. A new RLA must be appointed for this region.</span>
              ) : (
                <span><strong>Reversible:</strong> Licence suspended pending remedy. Can be reinstated to full terms or reinstated at a reduced commission rate.</span>
              )}
              <p className="mt-1 font-medium">
                In both cases: tenants continue service without billing until a new or reinstated RLA is assigned.
              </p>
            </div>
          </div>
          <div>
            <Label>Reason for Termination</Label>
            <Textarea name="reason" required placeholder="Document the specific violation or breach..." />
          </div>
        </FormDialog>
      )}

      {/* ── Reinstatement Dialog (Full / Reduced) ──────────────────────── */}
      {showReinstate && (
        <FormDialog
          open={!!showReinstate}
          onClose={() => setShowReinstate(null)}
          title={showReinstate.mode === "full" ? "Full Reinstatement" : "Reduced-Rate Reinstatement"}
          description={
            showReinstate.mode === "full"
              ? "Restore the RLA to full ACTIVE status under their original contract terms. Billing resumes immediately."
              : "Reinstate the RLA at a lower commission rate for a fixed term. After the term expires, full rates resume."
          }
          onSubmit={(e) => {
            e.preventDefault();
            const d = new FormData(e.target as HTMLFormElement);
            if (showReinstate.mode === "full") {
              reinstateFullMut.mutate({
                agent_id: showReinstate.agent_id,
                notes: d.get("notes") as string,
              });
            } else {
              reinstateReducedMut.mutate({
                agent_id: showReinstate.agent_id,
                reduced_commission_rate: parseFloat(d.get("reduced_rate") as string) / 100,
                reduced_commission_term_months: parseInt(d.get("term_months") as string),
                reason: d.get("reason") as string,
              });
            }
          }}
          submitLabel={showReinstate.mode === "full" ? "Reinstate at Full Terms" : "Reinstate at Reduced Rate"}
          loading={reinstateFullMut.isPending || reinstateReducedMut.isPending}
        >
          {showReinstate.mode === "reduced" ? (
            <>
              <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                <strong>Reduced Commission Reinstatement:</strong> RLA resumes operations at a lower commission rate for a fixed term. This cannot be reversed — after the term expires, rates return to original agreed levels (or a new contract is negotiated).
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Reduced Commission Rate (%)</Label>
                  <Input name="reduced_rate" type="number" min="1" max="40" defaultValue="20" required />
                  <p className="mt-0.5 text-xs text-bos-silver-dark">Must be lower than their original rate</p>
                </div>
                <div>
                  <Label>Term Duration (months)</Label>
                  <Input name="term_months" type="number" min="3" max="24" defaultValue="6" required />
                  <p className="mt-0.5 text-xs text-bos-silver-dark">After this period, full rates resume</p>
                </div>
              </div>
              <div>
                <Label>Justification</Label>
                <Textarea name="reason" required placeholder="Document why reduced-rate reinstatement was chosen over full reinstatement..." />
              </div>
            </>
          ) : (
            <div>
              <div className="mb-3 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
                <strong>Full Reinstatement:</strong> All original contract terms are restored. Region exits pending state immediately and billing resumes.
              </div>
              <Label>Reinstatement Notes</Label>
              <Textarea name="notes" placeholder="Document what remediation was completed..." />
            </div>
          )}
        </FormDialog>
      )}

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
