"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, Input, Label, Select, Textarea, Toast,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Badge,
} from "@/components/ui";
import { getResellers, registerReseller, linkTenant, accrueCommission, requestPayout } from "@/lib/api/saas";
import { REGIONS, PAYOUT_METHODS } from "@/lib/constants";
import { formatCurrency } from "@/lib/utils";
import { Handshake, UserPlus, Link2, DollarSign, Wallet, Plus } from "lucide-react";

const TIER_COLORS: Record<string, string> = {
  BRONZE: "bg-orange-100 text-orange-800",
  SILVER: "bg-neutral-200 text-neutral-700",
  GOLD: "bg-bos-gold-light text-bos-gold-dark",
};

export default function ResellersPage() {
  const queryClient = useQueryClient();
  const [showRegister, setShowRegister] = useState(false);
  const [showLink, setShowLink] = useState<string | null>(null);
  const [showAccrue, setShowAccrue] = useState<string | null>(null);
  const [showPayout, setShowPayout] = useState<string | null>(null);
  const [payoutMethod, setPayoutMethod] = useState("MPESA");
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const resellers = useQuery({ queryKey: ["saas", "resellers"], queryFn: getResellers });

  const registerMut = useMutation({
    mutationFn: registerReseller,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["saas", "resellers"] }); setShowRegister(false); setToast({ message: "Reseller registered", variant: "success" }); },
    onError: () => setToast({ message: "Failed to register reseller", variant: "error" }),
  });

  const linkMut = useMutation({
    mutationFn: linkTenant,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["saas", "resellers"] }); setShowLink(null); setToast({ message: "Tenant linked", variant: "success" }); },
    onError: () => setToast({ message: "Failed to link tenant", variant: "error" }),
  });

  const accrueMut = useMutation({
    mutationFn: accrueCommission,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["saas", "resellers"] }); setShowAccrue(null); setToast({ message: "Commission accrued", variant: "success" }); },
    onError: () => setToast({ message: "Failed to accrue commission", variant: "error" }),
  });

  const payoutMut = useMutation({
    mutationFn: requestPayout,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["saas", "resellers"] }); setShowPayout(null); setToast({ message: "Payout requested", variant: "success" }); },
    onError: () => setToast({ message: "Failed to request payout", variant: "error" }),
  });

  const resellerList = resellers.data?.data ?? [];
  const totalTenants = resellerList.reduce((sum: number, r: { active_tenant_count?: number }) => sum + (r.active_tenant_count ?? 0), 0);
  const totalPending = resellerList.reduce((sum: number, r: { pending_commission?: number }) => sum + (r.pending_commission ?? 0), 0);

  function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    registerMut.mutate({
      company_name: d.get("company_name") as string,
      contact_person: d.get("contact_person") as string,
      phone: d.get("phone") as string,
      email: d.get("email") as string,
      payout_method: payoutMethod as "MPESA" | "MOBILE_MONEY" | "BANK_TRANSFER",
      payout_phone: d.get("payout_phone") as string || undefined,
      bank_name: d.get("bank_name") as string || undefined,
      account_number: d.get("account_number") as string || undefined,
      account_name: d.get("account_name") as string || undefined,
    });
  }

  function handleLink(e: React.FormEvent) {
    e.preventDefault();
    if (!showLink) return;
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    linkMut.mutate({ reseller_id: showLink, business_id: d.get("business_id") as string });
  }

  function handleAccrue(e: React.FormEvent) {
    e.preventDefault();
    if (!showAccrue) return;
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    accrueMut.mutate({
      reseller_id: showAccrue,
      business_id: d.get("business_id") as string,
      tenant_monthly_amount: Number(d.get("tenant_monthly_amount")),
      currency: d.get("currency") as string,
      period: d.get("period") as string,
    });
  }

  function handlePayout(e: React.FormEvent) {
    e.preventDefault();
    if (!showPayout) return;
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    payoutMut.mutate({
      reseller_id: showPayout,
      amount: Number(d.get("amount")),
      currency: d.get("currency") as string,
    });
  }

  return (
    <div>
      <PageHeader
        title="Resellers"
        description="Manage reseller agents and their commissions"
        actions={
          <Button onClick={() => setShowRegister(true)} className="gap-2">
            <UserPlus className="h-4 w-4" />
            Register Reseller
          </Button>
        }
      />

      {/* Summary Stats */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Total Resellers" value={resellerList.length} icon={Handshake} />
        <StatCard title="Total Tenants Linked" value={totalTenants} icon={Link2} />
        <StatCard title="Pending Commissions" value={totalPending > 0 ? formatCurrency(totalPending, "KES") : "0"} icon={Wallet} />
      </div>

      {/* Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Company</TableHead>
              <TableHead>Contact</TableHead>
              <TableHead>Tier</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Tenants</TableHead>
              <TableHead>Rate</TableHead>
              <TableHead>Earned</TableHead>
              <TableHead>Pending</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {resellerList.map((r: {
              reseller_id: string; company_name: string; contact_person?: string;
              tier: string; status: string; active_tenant_count: number;
              commission_rate: number; total_commission_earned: number;
              pending_commission: number;
            }) => (
              <TableRow key={r.reseller_id}>
                <TableCell className="font-medium">{r.company_name}</TableCell>
                <TableCell className="text-sm text-bos-silver-dark">{r.contact_person || "—"}</TableCell>
                <TableCell>
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${TIER_COLORS[r.tier] ?? ""}`}>
                    {r.tier}
                  </span>
                </TableCell>
                <TableCell><StatusBadge status={r.status} /></TableCell>
                <TableCell className="font-medium">{r.active_tenant_count}</TableCell>
                <TableCell className="text-sm">{Math.round(r.commission_rate * 100)}%</TableCell>
                <TableCell className="text-sm">{formatCurrency(r.total_commission_earned, "KES")}</TableCell>
                <TableCell className={r.pending_commission > 0 ? "font-medium text-bos-gold-dark" : "text-sm"}>
                  {formatCurrency(r.pending_commission, "KES")}
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" onClick={() => setShowLink(r.reseller_id)} title="Link Tenant">
                      <Link2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setShowAccrue(r.reseller_id)} title="Accrue Commission">
                      <DollarSign className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setShowPayout(r.reseller_id)} title="Request Payout">
                      <Wallet className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {resellerList.length === 0 && !resellers.isLoading && (
              <TableRow>
                <TableCell colSpan={9} className="py-8 text-center text-bos-silver-dark">
                  No resellers registered yet
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Register Dialog */}
      <FormDialog
        open={showRegister}
        onClose={() => setShowRegister(false)}
        title="Register Reseller"
        description="Register a new BOS reseller agent"
        onSubmit={handleRegister}
        submitLabel="Register"
        loading={registerMut.isPending}
        wide
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="company_name">Company Name</Label>
            <Input id="company_name" name="company_name" required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="contact_person">Contact Person</Label>
            <Input id="contact_person" name="contact_person" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="phone">Phone</Label>
            <Input id="phone" name="phone" placeholder="+254..." className="mt-1" />
          </div>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" name="email" type="email" className="mt-1" />
          </div>
        </div>
        <div>
          <Label>Payout Method</Label>
          <Select value={payoutMethod} onChange={(e) => setPayoutMethod(e.target.value)} className="mt-1">
            {PAYOUT_METHODS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </Select>
        </div>
        {(payoutMethod === "MPESA" || payoutMethod === "MOBILE_MONEY") && (
          <div>
            <Label htmlFor="payout_phone">Payout Phone</Label>
            <Input id="payout_phone" name="payout_phone" placeholder="+254..." className="mt-1" />
          </div>
        )}
        {payoutMethod === "BANK_TRANSFER" && (
          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label htmlFor="bank_name">Bank Name</Label>
              <Input id="bank_name" name="bank_name" className="mt-1" />
            </div>
            <div>
              <Label htmlFor="account_number">Account Number</Label>
              <Input id="account_number" name="account_number" className="mt-1" />
            </div>
            <div>
              <Label htmlFor="account_name">Account Name</Label>
              <Input id="account_name" name="account_name" className="mt-1" />
            </div>
          </div>
        )}
      </FormDialog>

      {/* Link Tenant Dialog */}
      <FormDialog open={!!showLink} onClose={() => setShowLink(null)} title="Link Tenant" onSubmit={handleLink} submitLabel="Link" loading={linkMut.isPending}>
        <div>
          <Label htmlFor="link_biz">Business ID</Label>
          <Input id="link_biz" name="business_id" required className="mt-1" />
        </div>
      </FormDialog>

      {/* Accrue Commission Dialog */}
      <FormDialog open={!!showAccrue} onClose={() => setShowAccrue(null)} title="Accrue Commission" onSubmit={handleAccrue} submitLabel="Accrue" loading={accrueMut.isPending}>
        <div>
          <Label htmlFor="acc_biz">Tenant Business ID</Label>
          <Input id="acc_biz" name="business_id" required className="mt-1" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="acc_amount">Monthly Amount</Label>
            <Input id="acc_amount" name="tenant_monthly_amount" type="number" required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="acc_currency">Currency</Label>
            <Select id="acc_currency" name="currency" className="mt-1">
              {REGIONS.map((r) => (
                <option key={r.currency} value={r.currency}>{r.currency}</option>
              ))}
            </Select>
          </div>
        </div>
        <div>
          <Label htmlFor="acc_period">Period</Label>
          <Input id="acc_period" name="period" placeholder="e.g. 2026-03" required className="mt-1" />
        </div>
      </FormDialog>

      {/* Request Payout Dialog */}
      <FormDialog open={!!showPayout} onClose={() => setShowPayout(null)} title="Request Payout" onSubmit={handlePayout} submitLabel="Request" loading={payoutMut.isPending}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="pay_amount">Amount</Label>
            <Input id="pay_amount" name="amount" type="number" required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="pay_currency">Currency</Label>
            <Select id="pay_currency" name="currency" className="mt-1">
              {REGIONS.map((r) => (
                <option key={r.currency} value={r.currency}>{r.currency}</option>
              ))}
            </Select>
          </div>
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
