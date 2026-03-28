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
import { REGIONS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import {
  Shield, MapPin, Plus, XCircle, Play, AlertTriangle, Users, FileText, Percent,
} from "lucide-react";
import Link from "next/link";

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
    onSuccess: () => { setShowSuspend(null); qc.invalidateQueries({ queryKey: ["saas", "agents"] }); setToast({ message: "Agent suspended", variant: "success" }); },
  });

  const reinstateMut = useMutation({
    mutationFn: reinstateAgent,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "agents"] }); setToast({ message: "Agent reinstated", variant: "success" }); },
  });

  const terminateMut = useMutation({
    mutationFn: terminateAgent,
    onSuccess: () => { setShowTerminate(null); qc.invalidateQueries({ queryKey: ["saas", "agents"] }); setToast({ message: "Agent terminated", variant: "success" }); },
  });

  const agentList: Array<{
    agent_id: string; agent_name: string; agent_type: string;
    territory?: string; status: string; active_tenant_count?: number;
    contact_email: string; contact_phone?: string; created_at?: string;
    market_share_pct?: number; license_number?: string;
    max_platform_discount_pct?: number; max_trial_days?: number;
    commission_rate?: string;
  }> = agents.data?.data ?? [];

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
      agent_type: "REGION_LICENSE_AGENT",
      territory: d.get("territory") as string,
      contact_person: d.get("contact_person") as string,
      market_share_pct: parseInt(d.get("market_share_pct") as string || "30"),
      max_platform_discount_pct: parseInt(d.get("max_platform_discount_pct") as string || "15"),
      max_trial_days: parseInt(d.get("max_trial_days") as string || "180"),
    } as Parameters<typeof registerAgent>[0] & { market_share_pct: number; max_platform_discount_pct: number; max_trial_days: number });
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
        <StatCard title="Total Tenants (RLA)" value={agentList.reduce((s, a) => s + (a.active_tenant_count ?? 0), 0)} icon={Users} />
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
                <li><strong>Market share</strong> — Platform Admin sets % of regional revenue the RLA retains</li>
                <li><strong>Auto-license</strong> — system generates license number on appointment (BOS-RLA-XX-YYYY-HASH)</li>
                <li><strong>Revenue collector</strong> — collects all subscription payments from tenants in their region</li>
                <li><strong>Discount authority</strong> — RLA sets discounts within platform limits. Can add extra discount from own market share</li>
                <li><strong>Trial days</strong> — RLA sets trial period within platform maximum</li>
                <li><strong>Compliance owner</strong> — responsible for local tax filings, e-invoicing, privacy compliance</li>
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
                  <TableHead>License</TableHead>
                  <TableHead className="text-center">Market Share</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Tenants</TableHead>
                  <TableHead className="text-center">Discount Limit</TableHead>
                  <TableHead className="text-center">Max Trial</TableHead>
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
                      <TableCell className="text-center"><StatusBadge status={a.status} /></TableCell>
                      <TableCell className="text-right font-mono">{a.active_tenant_count ?? 0}</TableCell>
                      <TableCell className="text-center">
                        <span className="font-mono text-sm">{a.max_platform_discount_pct ?? 15}%</span>
                      </TableCell>
                      <TableCell className="text-center">
                        <span className="font-mono text-sm">{a.max_trial_days ?? 180}d</span>
                      </TableCell>
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
        description="Assign an RLA with market share, license, and discount limits. The system will auto-generate a license number."
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
            <p className="mt-0.5 text-xs text-bos-silver-dark">% of regional revenue RLA retains. Platform keeps the rest.</p>
          </div>
        </div>

        <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <h4 className="text-sm font-semibold text-amber-900 flex items-center gap-1.5"><Percent className="h-4 w-4" /> Platform Limits for this RLA</h4>
          <p className="mt-1 text-xs text-amber-700">These are the maximum values this RLA can set. RLA sets actual values within these limits.</p>
          <div className="mt-3 grid grid-cols-2 gap-4">
            <div>
              <Label className="text-amber-900">Max Platform-Funded Discount (%)</Label>
              <Input name="max_platform_discount_pct" type="number" min="0" max="50" defaultValue="15" />
              <p className="mt-0.5 text-xs text-amber-700">Platform pays for this discount</p>
            </div>
            <div>
              <Label className="text-amber-900">Max Trial Days</Label>
              <Input name="max_trial_days" type="number" min="0" max="365" defaultValue="180" />
              <p className="mt-0.5 text-xs text-amber-700">Maximum trial period RLA can offer</p>
            </div>
          </div>
        </div>

        <div className="mt-2 rounded-lg border border-blue-200 bg-blue-50 p-3">
          <h4 className="text-sm font-semibold text-blue-900">RLA-Funded Discount (From Market Share)</h4>
          <p className="mt-1 text-xs text-blue-700">
            In addition to platform-funded discounts, the RLA can offer extra discounts from their own market share.
            These reduce the RLA&apos;s revenue — not the platform&apos;s. No platform limit applies.
          </p>
        </div>
      </FormDialog>

      {/* Suspend Dialog */}
      <FormDialog
        open={!!showSuspend}
        onClose={() => setShowSuspend(null)}
        title="Suspend Region License Agent"
        description="Suspending an RLA will freeze their region operations. Tenants can still use the system but no new sales can be processed."
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
          <span>Terminating an RLA removes them permanently. The license will be revoked and the region becomes uncovered.</span>
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
