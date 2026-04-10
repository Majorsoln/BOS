"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast,
} from "@/components/ui";
import { getMyCommissions, requestMyPayout } from "@/lib/api/agents";
import { PAYOUT_METHODS } from "@/lib/constants";
import { useRegions } from "@/hooks/use-regions";
import { DollarSign, Download } from "lucide-react";

export default function CommissionHistoryPage() {
  const [showPayout, setShowPayout] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);
  const commissions = useQuery({ queryKey: ["agent", "commissions"], queryFn: () => getMyCommissions() });
  const { regions } = useRegions();

  const payoutMut = useMutation({
    mutationFn: requestMyPayout,
    onSuccess: () => { setShowPayout(false); setToast({ message: "Payout requested", variant: "success" }); },
    onError: () => setToast({ message: "Failed to request payout", variant: "error" }),
  });

  function handlePayout(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    payoutMut.mutate({
      amount: Number(d.get("amount")),
      currency: d.get("currency") as string,
      method: d.get("method") as string,
    });
  }

  const data = commissions.data?.data;
  const history = data?.history ?? [];

  return (
    <div>
      <PageHeader
        title="Commission History"
        description="Your earnings and payout history"
        actions={
          <Button variant="outline" onClick={() => setShowPayout(true)} className="gap-2">
            <Download className="h-4 w-4" />
            Request Payout
          </Button>
        }
      />

      {/* Current Month Summary */}
      {data?.current && (
        <Card className="mb-6 border-bos-purple/20">
          <CardHeader>
            <CardTitle className="text-base">Current Month</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-xs text-bos-silver-dark">Tenant Payments</p>
                <p className="text-lg font-bold">{data.current.gross ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-bos-silver-dark">Commission Rate</p>
                <p className="text-lg font-bold text-bos-purple">{data.current.rate ?? "—"}%</p>
              </div>
              <div>
                <p className="text-xs text-bos-silver-dark">Earned</p>
                <p className="text-lg font-bold text-bos-purple">{data.current.earned ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-bos-silver-dark">Status</p>
                <StatusBadge status={data.current.status ?? "ACCRUING"} />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* History Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Monthly History</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Month</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Tenant Payments</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Rate</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Commission</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Override</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Payout Status</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-bos-silver-dark">No commission history yet</td></tr>
                )}
                {history.map((h: {
                  month: string; tenant_payments: string; rate: number;
                  commission: string; override: string; total: string; status: string;
                }, i: number) => (
                  <tr key={i} className="border-b border-bos-silver/10">
                    <td className="px-4 py-3 font-medium">{h.month}</td>
                    <td className="px-4 py-3 text-right font-mono">{h.tenant_payments}</td>
                    <td className="px-4 py-3 text-right">{h.rate}%</td>
                    <td className="px-4 py-3 text-right font-mono">{h.commission}</td>
                    <td className="px-4 py-3 text-right font-mono">{h.override ?? "—"}</td>
                    <td className="px-4 py-3 text-right font-mono font-bold text-bos-purple">{h.total}</td>
                    <td className="px-4 py-3"><StatusBadge status={h.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <FormDialog
        open={showPayout}
        onClose={() => setShowPayout(false)}
        title="Request Payout"
        description="Request payout of accrued commission. Platform must approve before processing."
        onSubmit={handlePayout}
        submitLabel="Request"
        loading={payoutMut.isPending}
      >
        <div>
          <Label htmlFor="pay_amount">Amount</Label>
          <Input id="pay_amount" name="amount" type="number" required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="pay_currency">Currency</Label>
          <Select id="pay_currency" name="currency" className="mt-1" required>
            {regions.map((r) => <option key={r.code} value={r.currency}>{r.currency} ({r.name})</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="pay_method">Payout Method</Label>
          <Select id="pay_method" name="method" className="mt-1" required>
            {PAYOUT_METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
          </Select>
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
