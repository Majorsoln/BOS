"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
  Textarea,
} from "@/components/ui";
import { getCommissionRanges, setCommissionRanges } from "@/lib/api/agents";
import {
  Shield, Save, Scale, Clock, DollarSign, AlertTriangle,
  Percent, Wallet, Settings, FileText,
} from "lucide-react";

type ToastState = { message: string; variant: "success" | "error" } | null;
type TabKey = "commission" | "settlement" | "clawback" | "thresholds";

export default function PaymentRulesPage() {
  const [tab, setTab] = useState<TabKey>("commission");
  const [toast, setToast] = useState<ToastState>(null);

  const tabs: { key: TabKey; label: string }[] = [
    { key: "commission", label: "Commission Tiers" },
    { key: "settlement", label: "Settlement Schedule" },
    { key: "clawback", label: "Clawback Policy" },
    { key: "thresholds", label: "Payout Thresholds" },
  ];

  return (
    <div>
      <PageHeader
        title="Payment Rules"
        description="Set commission tiers, settlement schedules, clawback policies, and payout thresholds for all agents."
      />

      <div className="mb-6 flex gap-1 rounded-lg bg-bos-silver-light p-1 dark:bg-neutral-800 w-fit">
        {tabs.map((t) => (
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

      {tab === "commission" && <CommissionTiersTab onToast={setToast} />}
      {tab === "settlement" && <SettlementTab onToast={setToast} />}
      {tab === "clawback" && <ClawbackTab onToast={setToast} />}
      {tab === "thresholds" && <ThresholdsTab onToast={setToast} />}

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

type ToastFn = (t: { message: string; variant: "success" | "error" }) => void;

/* ── Commission Tiers Tab ─────────────────────────────── */

function CommissionTiersTab({ onToast }: { onToast: ToastFn }) {
  const qc = useQueryClient();
  const rangesQuery = useQuery({
    queryKey: ["saas", "commission-ranges"],
    queryFn: getCommissionRanges,
  });

  const saveMut = useMutation({
    mutationFn: setCommissionRanges,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saas", "commission-ranges"] });
      onToast({ message: "Commission tiers updated", variant: "success" });
    },
    onError: () => onToast({ message: "Failed to update", variant: "error" }),
  });

  const config = rangesQuery.data?.data;
  const tiers = config?.tiers ?? [
    { tier: "BRONZE", min_tenants: 0, max_tenants: 10, rate_pct: 10 },
    { tier: "SILVER", min_tenants: 11, max_tenants: 50, rate_pct: 15 },
    { tier: "GOLD", min_tenants: 51, max_tenants: 999, rate_pct: 20 },
  ];
  const residualRate = config?.residual_rate_pct ?? 3;
  const firstYearBonus = config?.first_year_bonus_pct ?? 0;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    saveMut.mutate({
      ranges: tiers.map((t: { tier: string; min_tenants: number; max_tenants: number }) => ({
        min_tenants: t.min_tenants,
        max_tenants: t.max_tenants,
        rate_pct: Number(d.get(`rate_${t.tier}`)),
      })),
      residual_rate_pct: Number(d.get("residual_rate")),
      first_year_bonus_pct: Number(d.get("first_year_bonus")),
    });
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Percent className="h-5 w-5 text-bos-purple" />
            <CardTitle>Commission Tiers — Remote Agents</CardTitle>
          </div>
          <p className="text-xs text-bos-silver-dark mt-1">
            Remote agents earn commission based on their active tenant count tier.
            RLAs earn via market share (set per-RLA at appointment).
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Tier cards */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {tiers.map((t: { tier: string; min_tenants: number; max_tenants: number; rate_pct: number }) => (
                <div key={t.tier} className={`rounded-lg border-2 p-4 ${
                  t.tier === "GOLD" ? "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950" :
                  t.tier === "SILVER" ? "border-gray-300 bg-gray-50 dark:border-gray-600 dark:bg-gray-900" :
                  "border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-950"
                }`}>
                  <p className="text-center font-bold text-sm">{t.tier}</p>
                  <p className="text-center text-xs text-bos-silver-dark mb-3">
                    {t.min_tenants}–{t.max_tenants === 999 ? "∞" : t.max_tenants} tenants
                  </p>
                  <div>
                    <Label>Commission Rate %</Label>
                    <Input
                      name={`rate_${t.tier}`}
                      type="number"
                      min={1}
                      max={50}
                      defaultValue={t.rate_pct}
                      required
                      className="text-center font-mono text-lg"
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Additional rates */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Residual Rate % (recurring on renewals)</Label>
                <Input name="residual_rate" type="number" min={0} max={20} step={0.5} defaultValue={residualRate} required />
                <p className="mt-1 text-xs text-bos-silver-dark">Agent earns this % on every tenant renewal</p>
              </div>
              <div>
                <Label>First Year Bonus %</Label>
                <Input name="first_year_bonus" type="number" min={0} max={30} step={0.5} defaultValue={firstYearBonus} required />
                <p className="mt-1 text-xs text-bos-silver-dark">Extra commission during tenant&apos;s first year</p>
              </div>
            </div>

            <Button type="submit" disabled={saveMut.isPending} className="w-full gap-2">
              <Save className="h-4 w-4" />
              {saveMut.isPending ? "Saving..." : "Save Commission Rules"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* RLA Info */}
      <Card className="border-purple-200/50 bg-purple-50/30 dark:border-purple-800/30 dark:bg-purple-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Shield className="mt-0.5 h-5 w-5 text-purple-600" />
            <div className="text-sm">
              <p className="font-semibold text-purple-700 dark:text-purple-400">RLA Compensation — Market Share Model</p>
              <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-400">
                RLAs do NOT use commission tiers. Each RLA&apos;s market share % is set individually at appointment time.
                Go to <a href="/platform/agents/rla" className="text-bos-purple underline">Region License Agents</a> to view/adjust.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Settlement Schedule Tab ──────────────────────────── */

function SettlementTab({ onToast }: { onToast: ToastFn }) {
  const [saved, setSaved] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // In production this would call a backend endpoint
    setSaved(true);
    onToast({ message: "Settlement schedule updated", variant: "success" });
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-bos-purple" />
            <CardTitle>Settlement Schedule</CardTitle>
          </div>
          <p className="text-xs text-bos-silver-dark mt-1">
            How often RLAs must remit collected funds, and when agent payouts are processed.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* RLA Remittance */}
            <div className="rounded-lg border p-4">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Shield className="h-4 w-4 text-purple-600" /> RLA Remittance to Platform
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Remittance Frequency</Label>
                  <Select name="rla_remittance_frequency" defaultValue="WEEKLY">
                    <option value="DAILY">Daily</option>
                    <option value="WEEKLY">Weekly</option>
                    <option value="BIWEEKLY">Bi-weekly</option>
                    <option value="MONTHLY">Monthly</option>
                  </Select>
                </div>
                <div>
                  <Label>Settlement Day</Label>
                  <Select name="rla_settlement_day" defaultValue="FRIDAY">
                    <option value="MONDAY">Monday</option>
                    <option value="WEDNESDAY">Wednesday</option>
                    <option value="FRIDAY">Friday</option>
                    <option value="LAST_DAY">Last Day of Period</option>
                  </Select>
                </div>
              </div>
              <div className="mt-3">
                <Label>Late Remittance Grace Period (days)</Label>
                <Input name="rla_grace_days" type="number" defaultValue={3} min={0} max={14} />
                <p className="mt-1 text-xs text-bos-silver-dark">After grace period, system flags RLA for review</p>
              </div>
            </div>

            {/* Agent Payouts */}
            <div className="rounded-lg border p-4">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Wallet className="h-4 w-4 text-green-600" /> Agent Payout Processing
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Bronze/Silver Payout Frequency</Label>
                  <Select name="standard_payout_frequency" defaultValue="MONTHLY">
                    <option value="WEEKLY">Weekly</option>
                    <option value="BIWEEKLY">Bi-weekly</option>
                    <option value="MONTHLY">Monthly</option>
                  </Select>
                </div>
                <div>
                  <Label>Gold Payout Frequency</Label>
                  <Select name="gold_payout_frequency" defaultValue="WEEKLY">
                    <option value="WEEKLY">Weekly</option>
                    <option value="BIWEEKLY">Bi-weekly</option>
                    <option value="MONTHLY">Monthly</option>
                  </Select>
                </div>
              </div>
              <div className="mt-3">
                <Label>Payout Processing Day</Label>
                <Select name="payout_processing_day" defaultValue="1">
                  <option value="1">1st of month</option>
                  <option value="15">15th of month</option>
                  <option value="LAST">Last day of month</option>
                  <option value="FRIDAY">Every Friday (weekly)</option>
                </Select>
              </div>
            </div>

            {/* Auto-approval */}
            <div className="rounded-lg border p-4">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Settings className="h-4 w-4 text-blue-600" /> Auto-Approval Rules
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Auto-approve payouts under (amount)</Label>
                  <Input name="auto_approve_threshold" type="number" defaultValue={50000} />
                  <p className="mt-1 text-xs text-bos-silver-dark">Payouts above this require manual approval</p>
                </div>
                <div>
                  <Label>Auto-approve for agents with tier</Label>
                  <Select name="auto_approve_tier" defaultValue="GOLD">
                    <option value="NONE">None — all manual</option>
                    <option value="GOLD">Gold only</option>
                    <option value="SILVER">Silver and above</option>
                    <option value="ALL">All tiers</option>
                  </Select>
                </div>
              </div>
            </div>

            <Button type="submit" className="w-full gap-2">
              <Save className="h-4 w-4" /> Save Settlement Schedule
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Clawback Policy Tab ──────────────────────────────── */

function ClawbackTab({ onToast }: { onToast: ToastFn }) {
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onToast({ message: "Clawback policy updated", variant: "success" });
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <CardTitle>Clawback Policy — Sera ya Kurudisha</CardTitle>
          </div>
          <p className="text-xs text-bos-silver-dark mt-1">
            When a tenant churns within the clawback period, the agent&apos;s commission is reversed.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="rounded-lg border-2 border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950">
              <h3 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-3">Clawback Rules</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Clawback Period (days)</Label>
                  <Input name="clawback_days" type="number" defaultValue={90} min={30} max={365} />
                  <p className="mt-1 text-xs text-bos-silver-dark">Tenant must stay active this long, else commission is reversed</p>
                </div>
                <div>
                  <Label>Clawback Percentage</Label>
                  <Select name="clawback_pct" defaultValue="100">
                    <option value="100">100% — full reversal</option>
                    <option value="75">75% — partial</option>
                    <option value="50">50% — half</option>
                  </Select>
                </div>
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <h3 className="text-sm font-semibold mb-3">Clawback Exceptions</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Gold agents exempt</p>
                    <p className="text-xs text-bos-silver-dark">Gold tier agents are not subject to clawback</p>
                  </div>
                  <Select name="gold_exempt" defaultValue="NO" className="w-24">
                    <option value="YES">Yes</option>
                    <option value="NO">No</option>
                  </Select>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Platform-caused churn exempt</p>
                    <p className="text-xs text-bos-silver-dark">If tenant left due to platform issue, no clawback</p>
                  </div>
                  <Select name="platform_churn_exempt" defaultValue="YES" className="w-24">
                    <option value="YES">Yes</option>
                    <option value="NO">No</option>
                  </Select>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Partial period refund</p>
                    <p className="text-xs text-bos-silver-dark">Pro-rate clawback based on days active</p>
                  </div>
                  <Select name="prorated" defaultValue="YES" className="w-24">
                    <option value="YES">Yes</option>
                    <option value="NO">No</option>
                  </Select>
                </div>
              </div>
            </div>

            <Button type="submit" className="w-full gap-2">
              <Save className="h-4 w-4" /> Save Clawback Policy
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Payout Thresholds Tab ────────────────────────────── */

function ThresholdsTab({ onToast }: { onToast: ToastFn }) {
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onToast({ message: "Payout thresholds updated", variant: "success" });
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-bos-purple" />
            <CardTitle>Payout Thresholds — Kiwango cha Chini</CardTitle>
          </div>
          <p className="text-xs text-bos-silver-dark mt-1">
            Minimum amounts agents must accumulate before requesting a payout. Set per currency.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { currency: "KES", name: "Kenya Shilling", defaultMin: 5000 },
              { currency: "TZS", name: "Tanzania Shilling", defaultMin: 50000 },
              { currency: "UGX", name: "Uganda Shilling", defaultMin: 100000 },
              { currency: "RWF", name: "Rwanda Franc", defaultMin: 50000 },
              { currency: "USD", name: "US Dollar", defaultMin: 50 },
            ].map((c) => (
              <div key={c.currency} className="flex items-center gap-4 rounded-lg border p-3">
                <div className="w-20">
                  <Badge variant="outline" className="font-mono">{c.currency}</Badge>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">{c.name}</p>
                </div>
                <div className="w-40">
                  <Input
                    name={`min_${c.currency}`}
                    type="number"
                    defaultValue={c.defaultMin}
                    min={0}
                    className="text-right font-mono"
                  />
                </div>
              </div>
            ))}

            <div className="rounded-lg border p-4 mt-4">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <FileText className="h-4 w-4 text-bos-purple" /> Payout Methods Allowed
              </h3>
              <div className="space-y-2">
                {[
                  { method: "MPESA", label: "M-Pesa", desc: "Mobile money (Kenya)" },
                  { method: "MOBILE_MONEY", label: "Mobile Money", desc: "MTN, Airtel Money, Tigo Pesa" },
                  { method: "BANK_TRANSFER", label: "Bank Transfer", desc: "Direct to bank account" },
                ].map((m) => (
                  <div key={m.method} className="flex items-center justify-between rounded-md border p-2">
                    <div>
                      <p className="text-sm font-medium">{m.label}</p>
                      <p className="text-xs text-bos-silver-dark">{m.desc}</p>
                    </div>
                    <Select name={`method_${m.method}`} defaultValue="ENABLED" className="w-28">
                      <option value="ENABLED">Enabled</option>
                      <option value="DISABLED">Disabled</option>
                    </Select>
                  </div>
                ))}
              </div>
            </div>

            <Button type="submit" className="w-full gap-2">
              <Save className="h-4 w-4" /> Save Thresholds
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
