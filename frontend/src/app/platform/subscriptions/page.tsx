"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Toast, Badge,
} from "@/components/ui";
import {
  getTrialPolicy, setTrialPolicy, getTrials, extendTrial, convertTrial,
  getSubscriptions, activateSubscription, cancelSubscription,
} from "@/lib/api/saas";
import { formatDate, formatCurrency } from "@/lib/utils";
import {
  Search, Clock, CalendarDays, CreditCard, Plus, ArrowRightCircle, Play, XCircle,
  ClipboardList, Save,
} from "lucide-react";

type TabKey = "trials" | "subscriptions" | "policy";
type ToastState = { message: string; variant: "success" | "error" } | null;

export default function TrialsSubscriptionsPage() {
  const [tab, setTab] = useState<TabKey>("trials");
  const [toast, setToast] = useState<ToastState>(null);

  const tabs: { key: TabKey; label: string }[] = [
    { key: "trials", label: "Active Trials" },
    { key: "subscriptions", label: "Subscriptions" },
    { key: "policy", label: "Trial Policy" },
  ];

  return (
    <div>
      <PageHeader
        title="Trials & Subscriptions"
        description="Manage tenant trial agreements, subscriptions, and trial policy"
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

      {tab === "trials" && <TrialsTab onToast={setToast} />}
      {tab === "subscriptions" && <SubscriptionsTab onToast={setToast} />}
      {tab === "policy" && <PolicyTab onToast={setToast} />}

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

type ToastFn = (t: { message: string; variant: "success" | "error" }) => void;

/* ── Trials Tab ────────────────────────────────────────── */

function TrialsTab({ onToast }: { onToast: ToastFn }) {
  const [businessId, setBusinessId] = useState("");
  const [agreement, setAgreement] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showExtend, setShowExtend] = useState(false);
  const [showConvert, setShowConvert] = useState(false);

  async function handleSearch(e?: React.FormEvent) {
    e?.preventDefault?.();
    if (!businessId.trim()) return;
    setLoading(true);
    setError("");
    setAgreement(null);
    try {
      const res = await getTrials({ status: undefined });
      const found = (res.data ?? []).find((t: { business_id: string }) => t.business_id === businessId.trim());
      if (found) setAgreement(found);
      else setError("No trial agreement found for this business");
    } catch {
      setError("Failed to fetch trial agreement");
    } finally {
      setLoading(false);
    }
  }

  const extendMut = useMutation({
    mutationFn: extendTrial,
    onSuccess: () => { setShowExtend(false); onToast({ message: "Trial extended", variant: "success" }); handleSearch(); },
    onError: () => onToast({ message: "Failed to extend trial", variant: "error" }),
  });

  const convertMut = useMutation({
    mutationFn: convertTrial,
    onSuccess: () => { setShowConvert(false); onToast({ message: "Trial converted to paying", variant: "success" }); handleSearch(); },
    onError: () => onToast({ message: "Failed to convert trial", variant: "error" }),
  });

  const a = agreement;

  return (
    <>
      <Card className="mb-6">
        <CardContent className="p-4">
          <form onSubmit={handleSearch} className="flex gap-3">
            <Input placeholder="Enter Business ID..." value={businessId} onChange={(e) => setBusinessId(e.target.value)} className="flex-1" />
            <Button type="submit" disabled={loading} className="gap-2">
              <Search className="h-4 w-4" /> {loading ? "Searching..." : "Search"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <Card className="mb-6 border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <CardContent className="p-4 text-sm text-red-700 dark:text-red-300">{error}</CardContent>
        </Card>
      )}

      {a && (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>Trial Agreement</CardTitle>
                <p className="mt-1 font-mono text-xs text-bos-silver-dark">{a.agreement_id as string}</p>
              </div>
              <StatusBadge status={a.status as string} />
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              <InfoBlock icon={Clock} label="Trial Days" value={`${a.trial_days} days${(a.bonus_days as number) > 0 ? ` + ${a.bonus_days} bonus` : ""}`} />
              <InfoBlock icon={CalendarDays} label="Trial Starts" value={formatDate(a.trial_starts_at as string)} />
              <InfoBlock icon={CalendarDays} label="Trial Ends" value={formatDate(a.trial_ends_at as string)} />
              <InfoBlock icon={CalendarDays} label="Billing Starts" value={formatDate(a.billing_starts_at as string)} />
              <InfoBlock icon={CreditCard} label="Rate Snapshot" value={
                a.rate_snapshot
                  ? formatCurrency((a.rate_snapshot as Record<string, unknown>).monthly_amount as number * 100, (a.rate_snapshot as Record<string, unknown>).currency as string)
                  : "\u2014"
              } />
              <InfoBlock icon={Clock} label="Combo" value={(a.combo_id as string) || "\u2014"} />
            </div>
            {a.promo_code ? <div className="mt-4"><Badge variant="gold">Promo: {a.promo_code as string}</Badge></div> : null}
            {a.status === "ACTIVE" && (
              <div className="mt-6 flex gap-3 border-t border-bos-silver/20 pt-4">
                <Button variant="outline" onClick={() => setShowExtend(true)} className="gap-2"><Plus className="h-4 w-4" /> Extend</Button>
                <Button onClick={() => setShowConvert(true)} className="gap-2"><ArrowRightCircle className="h-4 w-4" /> Convert to Paying</Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <FormDialog open={showExtend} onClose={() => setShowExtend(false)} title="Extend Trial" onSubmit={(e) => { e.preventDefault(); const d = new FormData(e.target as HTMLFormElement); extendMut.mutate({ business_id: businessId, extra_days: Number(d.get("extra_days")), reason: d.get("reason") as string }); }} submitLabel="Extend" loading={extendMut.isPending}>
        <div><Label>Extra Days</Label><Input name="extra_days" type="number" required /></div>
        <div><Label>Reason</Label><Input name="reason" placeholder="Optional" /></div>
      </FormDialog>

      <ConfirmDialog open={showConvert} onClose={() => setShowConvert(false)} onConfirm={() => convertMut.mutate({ business_id: businessId })} title="Convert Trial" description="Tenant will start paying from the next billing day." confirmLabel="Convert" loading={convertMut.isPending} />
    </>
  );
}

/* ── Subscriptions Tab ─────────────────────────────────── */

function SubscriptionsTab({ onToast }: { onToast: ToastFn }) {
  const [businessId, setBusinessId] = useState("");
  const [sub, setSub] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showActivate, setShowActivate] = useState(false);
  const [showCancel, setShowCancel] = useState(false);

  async function handleSearch(e?: React.FormEvent) {
    e?.preventDefault?.();
    if (!businessId.trim()) return;
    setLoading(true);
    setError("");
    setSub(null);
    try {
      const res = await getSubscriptions({ status: undefined });
      const found = (res.data ?? []).find((s: { business_id: string }) => s.business_id === businessId.trim());
      if (found) setSub(found);
      else setError("No subscription found for this business");
    } catch {
      setError("No subscription found or failed to fetch");
    } finally {
      setLoading(false);
    }
  }

  const activateMut = useMutation({
    mutationFn: activateSubscription,
    onSuccess: () => { setShowActivate(false); onToast({ message: "Subscription activated", variant: "success" }); handleSearch(); },
    onError: () => onToast({ message: "Failed to activate", variant: "error" }),
  });

  const cancelMut = useMutation({
    mutationFn: cancelSubscription,
    onSuccess: () => { setShowCancel(false); onToast({ message: "Subscription cancelled", variant: "success" }); handleSearch(); },
    onError: () => onToast({ message: "Failed to cancel", variant: "error" }),
  });

  const s = sub;

  return (
    <>
      <Card className="mb-6">
        <CardContent className="p-4">
          <form onSubmit={handleSearch} className="flex gap-3">
            <Input placeholder="Enter Business ID..." value={businessId} onChange={(e) => setBusinessId(e.target.value)} className="flex-1" />
            <Button type="submit" disabled={loading} className="gap-2"><Search className="h-4 w-4" /> {loading ? "Searching..." : "Search"}</Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <Card className="mb-6 border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-950">
          <CardContent className="p-4 text-sm text-orange-700 dark:text-orange-300">{error}</CardContent>
        </Card>
      )}

      {s && (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>Subscription</CardTitle>
                <p className="mt-1 font-mono text-xs text-bos-silver-dark">{s.subscription_id as string}</p>
              </div>
              <StatusBadge status={s.status as string} />
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <InfoRow label="Business ID" value={(s.business_id as string) ?? "\u2014"} mono />
              <InfoRow label="Services" value={(s.services as string) ?? "\u2014"} />
              <InfoRow label="Activated" value={s.activated_at ? formatDate(s.activated_at as string) : "\u2014"} />
              <InfoRow label="Billing Starts" value={s.billing_starts_at ? formatDate(s.billing_starts_at as string) : "\u2014"} />
              <InfoRow label="Renewals" value={String(s.renewal_count ?? 0)} />
              <InfoRow label="Monthly Amount" value={(s.monthly_amount as string) ?? "\u2014"} />
            </div>
            <div className="mt-6 flex flex-wrap gap-3 border-t border-bos-silver/20 pt-4">
              {s.status === "TRIAL" && (
                <Button onClick={() => setShowActivate(true)} className="gap-2"><Play className="h-4 w-4" /> Activate</Button>
              )}
              {s.status !== "CANCELLED" && (
                <Button variant="destructive" onClick={() => setShowCancel(true)} className="gap-2"><XCircle className="h-4 w-4" /> Cancel</Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <ConfirmDialog open={showActivate} onClose={() => setShowActivate(false)} onConfirm={() => activateMut.mutate({ business_id: businessId })} title="Activate Subscription" description="Tenant will start paying." confirmLabel="Activate" loading={activateMut.isPending} />
      <ConfirmDialog open={showCancel} onClose={() => setShowCancel(false)} onConfirm={() => cancelMut.mutate({ business_id: businessId })} title="Cancel Subscription" description="Permanent cancellation." confirmLabel="Cancel" confirmVariant="destructive" loading={cancelMut.isPending} />
    </>
  );
}

/* ── Trial Policy Tab ──────────────────────────────────── */

function PolicyTab({ onToast }: { onToast: ToastFn }) {
  const qc = useQueryClient();
  const policy = useQuery({ queryKey: ["saas", "trial-policy"], queryFn: getTrialPolicy });
  const policyData = policy.data?.data;

  const saveMut = useMutation({
    mutationFn: setTrialPolicy,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "trial-policy"] }); onToast({ message: "Trial policy updated", variant: "success" }); },
    onError: () => onToast({ message: "Failed to update", variant: "error" }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    saveMut.mutate({
      default_trial_days: Number(d.get("default_trial_days")),
      max_trial_days: Number(d.get("max_trial_days")),
      grace_period_days: Number(d.get("grace_period_days")),
    });
  }

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-bos-purple" />
            <CardTitle>Trial Policy</CardTitle>
          </div>
          <p className="text-xs text-bos-silver-dark mt-1">
            Guidelines for agents when onboarding tenants. Changes apply to NEW trials only.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label>Default Trial Days</Label>
              <Input name="default_trial_days" type="number" defaultValue={policyData?.default_trial_days ?? 180} required />
            </div>
            <div>
              <Label>Max Trial Days (incl. bonuses)</Label>
              <Input name="max_trial_days" type="number" defaultValue={policyData?.max_trial_days ?? 365} required />
            </div>
            <div>
              <Label>Grace Period Days (after trial expires)</Label>
              <Input name="grace_period_days" type="number" defaultValue={policyData?.grace_period_days ?? 30} required />
            </div>
            <Button type="submit" disabled={saveMut.isPending} className="w-full gap-2">
              <Save className="h-4 w-4" />
              {saveMut.isPending ? "Saving..." : "Save Policy"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Shared Components ─────────────────────────────────── */

function InfoBlock({ icon: Icon, label, value }: { icon: typeof Clock; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-bos-purple-light">
        <Icon className="h-4 w-4 text-bos-purple" />
      </div>
      <div>
        <p className="text-xs text-bos-silver-dark">{label}</p>
        <p className="text-sm font-medium">{value}</p>
      </div>
    </div>
  );
}

function InfoRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-xs text-bos-silver-dark">{label}</p>
      <p className={`text-sm font-medium ${mono ? "font-mono" : ""}`}>{value}</p>
    </div>
  );
}
