"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Select, Toast, Badge, Textarea, Label,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getAgentPayouts, approvePayout, rejectPayout } from "@/lib/api/agents";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import {
  CheckCircle, XCircle, Clock, DollarSign, AlertTriangle,
  Shield, UserCheck, Eye,
} from "lucide-react";

type ToastState = { message: string; variant: "success" | "error" } | null;

export default function PayoutApprovalsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("PENDING");
  const [toast, setToast] = useState<ToastState>(null);
  const [showApprove, setShowApprove] = useState<string | null>(null);
  const [showReject, setShowReject] = useState<string | null>(null);

  const payoutsQuery = useQuery({
    queryKey: ["saas", "agents", "payouts", statusFilter],
    queryFn: () => getAgentPayouts({ status: statusFilter || undefined }),
  });

  const approveMut = useMutation({
    mutationFn: approvePayout,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saas", "agents", "payouts"] });
      setShowApprove(null);
      setToast({ message: "Payout approved — processing", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to approve", variant: "error" }),
  });

  const rejectMut = useMutation({
    mutationFn: rejectPayout,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saas", "agents", "payouts"] });
      setShowReject(null);
      setToast({ message: "Payout rejected — agent notified", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to reject", variant: "error" }),
  });

  const payouts: Array<Record<string, unknown>> = payoutsQuery.data?.data ?? [];

  const pendingCount = payouts.filter((p) => p.status === "PENDING").length;
  const pendingAmount = payouts.filter((p) => p.status === "PENDING").reduce((s, p) => s + parseFloat((p.amount as string) || "0"), 0);
  const completedCount = payouts.filter((p) => p.status === "COMPLETED").length;
  const rejectedCount = payouts.filter((p) => p.status === "REJECTED" || p.status === "FAILED").length;

  const filtered = statusFilter
    ? payouts.filter((p) => p.status === statusFilter)
    : payouts;

  return (
    <div>
      <PageHeader
        title="Payout Approvals — Idhini ya Malipo"
        description="Review and approve agent commission payouts. Every approval is logged for audit."
      />

      {/* Stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          title="Pending Approval"
          value={pendingCount}
          icon={Clock}
          description={pendingAmount > 0 ? `${pendingAmount.toLocaleString()} total` : "None"}
        />
        <StatCard title="Approved" value={completedCount} icon={CheckCircle} description="Processed" />
        <StatCard title="Rejected" value={rejectedCount} icon={XCircle} />
        <StatCard title="Total Requests" value={payouts.length} icon={DollarSign} />
      </div>

      {/* Pending alert */}
      {pendingCount > 0 && (
        <Card className="mb-4 border-amber-200 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/30">
          <CardContent className="flex items-center gap-3 p-4">
            <AlertTriangle className="h-5 w-5 text-amber-600" />
            <div className="text-sm">
              <span className="font-semibold text-amber-700 dark:text-amber-400">
                {pendingCount} payout{pendingCount > 1 ? "s" : ""} awaiting approval
              </span>
              <span className="ml-2 text-bos-silver-dark">
                Total: {pendingAmount.toLocaleString()}
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filter */}
      <div className="mb-4 flex gap-3">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="COMPLETED">Approved</option>
          <option value="REJECTED">Rejected</option>
          <option value="FAILED">Failed</option>
        </Select>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <EmptyState
              title="No payouts"
              description={statusFilter === "PENDING" ? "No pending payouts — all clear" : "No payouts match this filter"}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>Requested</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((p, i) => (
                  <TableRow key={i} className={p.status === "PENDING" ? "bg-amber-50/30 dark:bg-amber-950/10" : ""}>
                    <TableCell>
                      <Link
                        href={`/platform/agents/${p.agent_id as string}`}
                        className="font-medium text-bos-purple hover:underline"
                      >
                        {(p.agent_name as string) || "—"}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant={(p.agent_type as string) === "REGION_LICENSE_AGENT" ? "purple" : "success"}>
                        {(p.agent_type as string) === "REGION_LICENSE_AGENT" ? "RLA" : "Remote"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{(p.period as string) || "—"}</TableCell>
                    <TableCell className="text-right font-mono font-bold">
                      {parseFloat((p.amount as string) || "0").toLocaleString()}
                    </TableCell>
                    <TableCell className="text-xs">{(p.currency as string) || "—"}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">{(p.method as string) || "—"}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">
                      {p.requested_at ? formatDate(p.requested_at as string) : "—"}
                    </TableCell>
                    <TableCell className="text-center"><StatusBadge status={p.status as string} /></TableCell>
                    <TableCell className="text-right">
                      {p.status === "PENDING" && (
                        <div className="flex justify-end gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowApprove(p.payout_id as string)}
                            className="text-green-600 hover:text-green-700"
                            title="Approve"
                          >
                            <CheckCircle className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowReject(p.payout_id as string)}
                            className="text-red-600 hover:text-red-700"
                            title="Reject"
                          >
                            <XCircle className="h-3.5 w-3.5" />
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

      {/* Approve Confirm */}
      <ConfirmDialog
        open={!!showApprove}
        onClose={() => setShowApprove(null)}
        onConfirm={() => showApprove && approveMut.mutate({ payout_id: showApprove })}
        title="Approve Payout"
        description="This will process the payout to the agent. This action is logged and irreversible."
        confirmLabel="Approve & Process"
        loading={approveMut.isPending}
      />

      {/* Reject Dialog */}
      <FormDialog
        open={!!showReject}
        onClose={() => setShowReject(null)}
        title="Reject Payout"
        description="The agent will be notified with the reason. Funds remain as pending commission."
        onSubmit={(e) => {
          e.preventDefault();
          const d = new FormData(e.target as HTMLFormElement);
          rejectMut.mutate({
            payout_id: showReject!,
            reason: d.get("reason") as string,
          });
        }}
        submitLabel="Reject"
        loading={rejectMut.isPending}
      >
        <div>
          <Label>Reason (Required — agent will see this)</Label>
          <Textarea name="reason" required placeholder="e.g. Pending remittance reconciliation, compliance review needed..." />
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
