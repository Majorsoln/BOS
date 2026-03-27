"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { FormDialog } from "@/components/shared/form-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import {
  getAgentPayouts, approvePayout, rejectPayout,
  getCommissionRanges, setCommissionRanges,
} from "@/lib/api/agents";
import { DEFAULT_COMMISSION_RANGES } from "@/lib/constants";
import { DollarSign, Check, X, Percent, Clock, CheckCircle2, XCircle } from "lucide-react";

type TabKey = "payouts" | "commissions";
type ToastState = { message: string; variant: "success" | "error" } | null;

export default function CommissionsPayoutsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<TabKey>("payouts");
  const [toast, setToast] = useState<ToastState>(null);
  const [showReject, setShowReject] = useState<string | null>(null);

  const payouts = useQuery({ queryKey: ["saas", "payouts"], queryFn: () => getAgentPayouts() });

  const approveMut = useMutation({
    mutationFn: approvePayout,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "payouts"] }); setToast({ message: "Payout approved", variant: "success" }); },
    onError: () => setToast({ message: "Failed to approve", variant: "error" }),
  });

  const rejectMut = useMutation({
    mutationFn: rejectPayout,
    onSuccess: () => { setShowReject(null); qc.invalidateQueries({ queryKey: ["saas", "payouts"] }); setToast({ message: "Payout rejected", variant: "success" }); },
    onError: () => setToast({ message: "Failed to reject", variant: "error" }),
  });

  const saveMut = useMutation({
    mutationFn: setCommissionRanges,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "commission-ranges"] }); setToast({ message: "Commission settings saved", variant: "success" }); },
    onError: () => setToast({ message: "Failed to save", variant: "error" }),
  });

  const payoutList: Array<{
    payout_id: string; agent_name: string; agent_type?: string; period: string;
    amount: number; currency: string; method: string; status: string;
  }> = payouts.data?.data ?? [];

  const pendingCount = payoutList.filter((p) => p.status === "PENDING").length;
  const totalPending = payoutList.filter((p) => p.status === "PENDING").reduce((s, p) => s + (p.amount ?? 0), 0);

  function handleSaveCommissions(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
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
    <div>
      <PageHeader
        title="Commissions & Payouts"
        description="Commission settings and payout approvals for all agent types"
      />

      {/* Stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Pending Payouts" value={pendingCount} icon={Clock} />
        <StatCard title="Pending Amount" value={`${totalPending.toLocaleString()}`} icon={DollarSign} />
        <StatCard title="Total Payouts" value={payoutList.length} icon={CheckCircle2} />
        <StatCard title="Commission Tiers" value={DEFAULT_COMMISSION_RANGES.length} icon={Percent} />
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-bos-silver-light p-1 dark:bg-neutral-800 w-fit">
        {([
          { key: "payouts" as const, label: "Pending Payouts" },
          { key: "commissions" as const, label: "Commission Settings" },
        ]).map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-white text-bos-purple shadow-sm dark:bg-neutral-900"
                : "text-bos-silver-dark hover:text-neutral-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Payouts Tab */}
      {tab === "payouts" && (
        <Card>
          <CardContent className="p-0">
            {payoutList.length === 0 ? (
              <EmptyState title="No payouts" description="No pending commission payouts" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Agent</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Method</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payoutList.map((p) => (
                    <TableRow key={p.payout_id}>
                      <TableCell className="font-medium">{p.agent_name}</TableCell>
                      <TableCell>
                        <Badge variant={p.agent_type === "REGION_LICENSE_AGENT" ? "purple" : "outline"}>
                          {p.agent_type === "REGION_LICENSE_AGENT" ? "RLA" : "Remote"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-bos-silver-dark">{p.period}</TableCell>
                      <TableCell className="text-right font-mono">{p.currency} {p.amount?.toLocaleString()}</TableCell>
                      <TableCell>{p.method}</TableCell>
                      <TableCell className="text-center"><StatusBadge status={p.status} /></TableCell>
                      <TableCell className="text-right">
                        {p.status === "PENDING" && (
                          <div className="flex justify-end gap-1">
                            <Button size="sm" onClick={() => approveMut.mutate({ payout_id: p.payout_id })} disabled={approveMut.isPending}>
                              <Check className="mr-1 h-3.5 w-3.5" /> Approve
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => setShowReject(p.payout_id)}>
                              <X className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* Commission Settings Tab */}
      {tab === "commissions" && (
        <div className="mx-auto max-w-lg">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Percent className="h-5 w-5 text-bos-purple" />
                <CardTitle>Commission Ranges</CardTitle>
              </div>
              <p className="text-xs text-bos-silver-dark mt-1">
                Volume-based commission rates. Applies to both RLAs and Remote Agents. RLA additionally collects regional revenue.
              </p>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSaveCommissions} className="space-y-4">
                {DEFAULT_COMMISSION_RANGES.map((r, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-sm w-32 text-bos-silver-dark">{r.min_tenants}–{r.max_tenants > 999 ? "\u221e" : r.max_tenants} tenants</span>
                    <Input name={`rate_${i}`} type="number" min={1} max={50} defaultValue={r.rate_pct} className="w-20" />
                    <span className="text-sm text-bos-silver-dark">%</span>
                  </div>
                ))}
                <div className="border-t border-bos-silver/20 pt-4 space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm w-32 text-bos-silver-dark">Residual rate</span>
                    <Input name="residual_rate_pct" type="number" min={0} max={10} defaultValue={3} className="w-20" />
                    <span className="text-sm text-bos-silver-dark">%</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm w-32 text-bos-silver-dark">First year bonus</span>
                    <Input name="first_year_bonus_pct" type="number" min={0} max={10} defaultValue={0} className="w-20" />
                    <span className="text-sm text-bos-silver-dark">%</span>
                  </div>
                </div>
                <Button type="submit" disabled={saveMut.isPending} className="w-full">
                  {saveMut.isPending ? "Saving..." : "Save Commission Settings"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Reject Dialog */}
      <FormDialog
        open={!!showReject}
        onClose={() => setShowReject(null)}
        title="Reject Payout"
        onSubmit={(e) => { e.preventDefault(); const d = new FormData(e.target as HTMLFormElement); rejectMut.mutate({ payout_id: showReject!, reason: d.get("reason") as string }); }}
        submitLabel="Reject"
        loading={rejectMut.isPending}
      >
        <div><Label>Reason</Label><Input name="reason" required placeholder="Reason for rejection" /></div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
