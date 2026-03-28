"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { FormDialog } from "@/components/shared/form-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Textarea, Toast, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Select,
} from "@/components/ui";
import {
  getTrialPolicy, setTrialPolicy, getTrials,
  getSubscriptions, extendTrial,
} from "@/lib/api/saas";
import { formatDate, formatCurrency } from "@/lib/utils";
import {
  Search, Clock, CalendarDays, CreditCard, Eye, Shield,
  ClipboardList, Save, Users, TrendingUp, AlertTriangle, Plus,
  FileEdit,
} from "lucide-react";

type TabKey = "overview" | "trials" | "subscriptions" | "policy";
type ToastState = { message: string; variant: "success" | "error" } | null;

export default function SubscriptionsOversightPage() {
  const [tab, setTab] = useState<TabKey>("overview");
  const [toast, setToast] = useState<ToastState>(null);

  const tabs: { key: TabKey; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "trials", label: "All Trials" },
    { key: "subscriptions", label: "All Subscriptions" },
    { key: "policy", label: "Trial Policy (Limits)" },
  ];

  return (
    <div>
      <PageHeader
        title="Trials & Subscriptions — Oversight"
        description="Monitor all tenant trials and subscriptions. Agents create trials; Platform sets limits and intervenes when needed."
      />

      {/* Doctrine banner */}
      <Card className="mb-6 border-amber-200/50 bg-amber-50/30 dark:border-amber-800/30 dark:bg-amber-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Eye className="mt-0.5 h-5 w-5 text-amber-600" />
            <div className="text-sm">
              <p className="font-semibold text-amber-700 dark:text-amber-400">Oversight Doctrine</p>
              <ul className="mt-1 list-disc pl-4 text-neutral-600 dark:text-neutral-400 space-y-0.5">
                <li><strong>Agents create trials</strong> when onboarding tenants — Platform does not create trials</li>
                <li><strong>Platform sets limits</strong> — max trial days, grace period, rate notice period</li>
                <li><strong>Platform can intervene</strong> — extend trials, adjust agreements for support cases</li>
                <li><strong>All changes logged</strong> — every adjustment requires a reason and is auditable</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

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

      {tab === "overview" && <OverviewTab />}
      {tab === "trials" && <TrialsOversightTab onToast={setToast} />}
      {tab === "subscriptions" && <SubscriptionsOversightTab />}
      {tab === "policy" && <PolicyTab onToast={setToast} />}

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

type ToastFn = (t: { message: string; variant: "success" | "error" }) => void;

/* ── Overview Tab ─────────────────────────────────────── */

function OverviewTab() {
  const trials = useQuery({ queryKey: ["saas", "trials"], queryFn: () => getTrials({ status: undefined }) });
  const subs = useQuery({ queryKey: ["saas", "subscriptions"], queryFn: () => getSubscriptions({ status: undefined }) });
  const policy = useQuery({ queryKey: ["saas", "trial-policy"], queryFn: getTrialPolicy });

  const trialList: Array<{ status: string; trial_days: number; bonus_days: number }> = trials.data?.data ?? [];
  const subList: Array<{ status: string }> = subs.data?.data ?? [];
  const policyData = policy.data?.data;

  const activeTrials = trialList.filter((t) => t.status === "ACTIVE").length;
  const convertedTrials = trialList.filter((t) => t.status === "CONVERTED").length;
  const expiredTrials = trialList.filter((t) => t.status === "EXPIRED").length;
  const activeSubs = subList.filter((s) => s.status === "ACTIVE").length;
  const trialSubs = subList.filter((s) => s.status === "TRIAL").length;
  const conversionRate = trialList.length > 0
    ? Math.round((convertedTrials / trialList.length) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active Trials" value={activeTrials} icon={Clock} description="Currently in trial" />
        <StatCard title="Converted" value={convertedTrials} icon={TrendingUp} description={`${conversionRate}% conversion rate`} />
        <StatCard title="Expired" value={expiredTrials} icon={AlertTriangle} description="Not converted" />
        <StatCard title="Paying Subscribers" value={activeSubs} icon={Users} description={`${trialSubs} still on trial`} />
      </div>

      {/* Current Policy */}
      {policyData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Shield className="h-4 w-4 text-bos-purple" /> Current Trial Policy (Limits for Agents)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="rounded-lg bg-bos-purple-light p-3">
                <p className="text-xs text-bos-silver-dark">Default Trial Days</p>
                <p className="text-xl font-bold text-bos-purple">{policyData.default_trial_days ?? 180}</p>
                <p className="text-xs text-bos-silver-dark">Agents use this as default</p>
              </div>
              <div className="rounded-lg bg-bos-purple-light p-3">
                <p className="text-xs text-bos-silver-dark">Max Trial Days</p>
                <p className="text-xl font-bold text-bos-purple">{policyData.max_trial_days ?? 365}</p>
                <p className="text-xs text-bos-silver-dark">Including all bonuses</p>
              </div>
              <div className="rounded-lg bg-bos-purple-light p-3">
                <p className="text-xs text-bos-silver-dark">Grace Period</p>
                <p className="text-xl font-bold text-bos-purple">{policyData.grace_period_days ?? 30}</p>
                <p className="text-xs text-bos-silver-dark">Days after trial ends</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Trials */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Recent Trial Activity</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {trialList.length === 0 ? (
            <EmptyState title="No trials yet" description="Trials will appear here when agents onboard tenants" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Business</TableHead>
                  <TableHead>Trial Days</TableHead>
                  <TableHead>Bonus</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trialList.slice(0, 10).map((t: Record<string, unknown>, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-mono text-xs">{(t.business_id as string)?.slice(0, 12) ?? "—"}...</TableCell>
                    <TableCell className="font-mono">{t.trial_days as number}</TableCell>
                    <TableCell>
                      {(t.bonus_days as number) > 0 ? (
                        <Badge variant="gold">+{t.bonus_days as number} days</Badge>
                      ) : "—"}
                    </TableCell>
                    <TableCell className="text-center"><StatusBadge status={t.status as string} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Trials Oversight Tab ─────────────────────────────── */

function TrialsOversightTab({ onToast }: { onToast: ToastFn }) {
  const [businessId, setBusinessId] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showExtend, setShowExtend] = useState<string | null>(null);
  const [showAdjust, setShowAdjust] = useState<Record<string, unknown> | null>(null);

  const trials = useQuery({
    queryKey: ["saas", "trials", statusFilter],
    queryFn: () => getTrials({ status: statusFilter || undefined }),
  });

  const extendMut = useMutation({
    mutationFn: extendTrial,
    onSuccess: () => {
      setShowExtend(null);
      onToast({ message: "Trial extended (logged)", variant: "success" });
    },
    onError: () => onToast({ message: "Failed to extend trial", variant: "error" }),
  });

  const trialList: Array<Record<string, unknown>> = trials.data?.data ?? [];

  // Filter by business ID search
  const filtered = businessId.trim()
    ? trialList.filter((t) => (t.business_id as string)?.includes(businessId.trim()))
    : trialList;

  return (
    <>
      {/* Search + Filter */}
      <Card className="mb-4">
        <CardContent className="flex gap-3 p-4">
          <Input
            placeholder="Search by Business ID..."
            value={businessId}
            onChange={(e) => setBusinessId(e.target.value)}
            className="flex-1"
          />
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
            <option value="">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="CONVERTED">Converted</option>
            <option value="EXPIRED">Expired</option>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <EmptyState title="No trials found" description="Adjust filters or wait for agents to onboard tenants" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Business ID</TableHead>
                  <TableHead>Trial Days</TableHead>
                  <TableHead>Bonus</TableHead>
                  <TableHead>Starts</TableHead>
                  <TableHead>Ends</TableHead>
                  <TableHead>Billing Starts</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead>Rate</TableHead>
                  <TableHead className="text-right">Intervene</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((t, i) => {
                  const rate = t.rate_snapshot as Record<string, unknown> | undefined;
                  return (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-xs">{(t.business_id as string)?.slice(0, 12)}...</TableCell>
                      <TableCell className="font-mono">{t.trial_days as number}</TableCell>
                      <TableCell>
                        {(t.bonus_days as number) > 0 ? (
                          <Badge variant="gold">+{t.bonus_days as number}</Badge>
                        ) : "—"}
                      </TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">{formatDate(t.trial_starts_at as string)}</TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">{formatDate(t.trial_ends_at as string)}</TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">{formatDate(t.billing_starts_at as string)}</TableCell>
                      <TableCell className="text-center"><StatusBadge status={t.status as string} /></TableCell>
                      <TableCell className="text-xs font-mono">
                        {rate ? `${rate.currency} ${Number(rate.monthly_amount).toLocaleString()}` : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        {t.status === "ACTIVE" && (
                          <div className="flex justify-end gap-1">
                            <Button size="sm" variant="outline" onClick={() => setShowExtend(t.business_id as string)} title="Extend trial">
                              <Plus className="h-3.5 w-3.5" />
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => setShowAdjust(t)} title="View / Adjust">
                              <FileEdit className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Extend Dialog */}
      <FormDialog
        open={!!showExtend}
        onClose={() => setShowExtend(null)}
        title="Extend Trial — Platform Intervention"
        description="This is a platform override. A reason is required for audit trail."
        onSubmit={(e) => {
          e.preventDefault();
          const d = new FormData(e.target as HTMLFormElement);
          extendMut.mutate({
            business_id: showExtend!,
            extra_days: Number(d.get("extra_days")),
            reason: d.get("reason") as string,
          });
        }}
        submitLabel="Extend (Logged)"
        loading={extendMut.isPending}
      >
        <div>
          <Label>Extra Days</Label>
          <Input name="extra_days" type="number" required min={1} max={90} />
          <p className="mt-1 text-xs text-bos-silver-dark">Max 90 days per intervention</p>
        </div>
        <div>
          <Label>Reason (Required — audit logged)</Label>
          <Textarea name="reason" required placeholder="e.g. Customer support case #1234, agent request, technical issue..." />
        </div>
      </FormDialog>

      {/* Adjust/View Dialog */}
      {showAdjust && (
        <FormDialog
          open={!!showAdjust}
          onClose={() => setShowAdjust(null)}
          title="Trial Agreement Detail"
          description="Review agreement terms. Adjustments are logged."
          onSubmit={(e) => { e.preventDefault(); setShowAdjust(null); }}
          submitLabel="Close"
        >
          <div className="space-y-3 text-sm">
            <div className="flex justify-between"><span className="text-bos-silver-dark">Agreement ID</span><span className="font-mono text-xs">{showAdjust.agreement_id as string}</span></div>
            <div className="flex justify-between"><span className="text-bos-silver-dark">Business ID</span><span className="font-mono text-xs">{showAdjust.business_id as string}</span></div>
            <div className="flex justify-between"><span className="text-bos-silver-dark">Trial Days</span><span className="font-mono">{showAdjust.trial_days as number}{(showAdjust.bonus_days as number) > 0 ? ` + ${showAdjust.bonus_days} bonus` : ""}</span></div>
            <div className="flex justify-between"><span className="text-bos-silver-dark">Trial Period</span><span>{formatDate(showAdjust.trial_starts_at as string)} — {formatDate(showAdjust.trial_ends_at as string)}</span></div>
            <div className="flex justify-between"><span className="text-bos-silver-dark">Billing Starts</span><span>{formatDate(showAdjust.billing_starts_at as string)}</span></div>
            {showAdjust.promo_code && <div className="flex justify-between"><span className="text-bos-silver-dark">Promo Code</span><Badge variant="gold">{showAdjust.promo_code as string}</Badge></div>}
            <div className="flex justify-between"><span className="text-bos-silver-dark">Status</span><StatusBadge status={showAdjust.status as string} /></div>
          </div>
          <div className="rounded-lg bg-amber-50 p-3 text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-300">
            Trial agreements are immutable contracts. To modify terms, use Extend or contact Engineering for exceptional cases.
          </div>
        </FormDialog>
      )}
    </>
  );
}

/* ── Subscriptions Oversight Tab ──────────────────────── */

function SubscriptionsOversightTab() {
  const [businessId, setBusinessId] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const subs = useQuery({
    queryKey: ["saas", "subscriptions", statusFilter],
    queryFn: () => getSubscriptions({ status: statusFilter || undefined }),
  });

  const subList: Array<Record<string, unknown>> = subs.data?.data ?? [];
  const filtered = businessId.trim()
    ? subList.filter((s) => (s.business_id as string)?.includes(businessId.trim()))
    : subList;

  return (
    <>
      <Card className="mb-4">
        <CardContent className="flex gap-3 p-4">
          <Input
            placeholder="Search by Business ID..."
            value={businessId}
            onChange={(e) => setBusinessId(e.target.value)}
            className="flex-1"
          />
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
            <option value="">All Statuses</option>
            <option value="TRIAL">Trial</option>
            <option value="ACTIVE">Active (Paying)</option>
            <option value="CANCELLED">Cancelled</option>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <EmptyState title="No subscriptions found" description="Subscriptions are created when agents onboard tenants" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Business ID</TableHead>
                  <TableHead>Services</TableHead>
                  <TableHead>Activated</TableHead>
                  <TableHead>Billing Starts</TableHead>
                  <TableHead className="text-center">Renewals</TableHead>
                  <TableHead>Monthly Amount</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((s, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-mono text-xs">{(s.business_id as string)?.slice(0, 12)}...</TableCell>
                    <TableCell className="text-sm">{(s.services as string) || "—"}</TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{s.activated_at ? formatDate(s.activated_at as string) : "—"}</TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{s.billing_starts_at ? formatDate(s.billing_starts_at as string) : "—"}</TableCell>
                    <TableCell className="text-center font-mono">{(s.renewal_count as number) ?? 0}</TableCell>
                    <TableCell className="font-mono text-sm">{(s.monthly_amount as string) ?? "—"}</TableCell>
                    <TableCell className="text-center"><StatusBadge status={s.status as string} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}

/* ── Trial Policy Tab (Platform sets limits) ──────────── */

function PolicyTab({ onToast }: { onToast: ToastFn }) {
  const qc = useQueryClient();
  const policy = useQuery({ queryKey: ["saas", "trial-policy"], queryFn: getTrialPolicy });
  const policyData = policy.data?.data;

  const saveMut = useMutation({
    mutationFn: setTrialPolicy,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saas", "trial-policy"] });
      onToast({ message: "Trial policy limits updated", variant: "success" });
    },
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
            <CardTitle>Trial Policy — Platform Limits</CardTitle>
          </div>
          <p className="text-xs text-bos-silver-dark mt-1">
            These limits govern what agents can offer. Agents set actual trial days within these bounds. Changes apply to NEW trials only.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label>Default Trial Days</Label>
              <Input name="default_trial_days" type="number" defaultValue={policyData?.default_trial_days ?? 180} required />
              <p className="mt-1 text-xs text-bos-silver-dark">Agents use this as starting value when onboarding</p>
            </div>
            <div>
              <Label>Max Trial Days (hard ceiling, incl. bonuses)</Label>
              <Input name="max_trial_days" type="number" defaultValue={policyData?.max_trial_days ?? 365} required />
              <p className="mt-1 text-xs text-bos-silver-dark">Agents cannot exceed this limit even with referral bonuses</p>
            </div>
            <div>
              <Label>Grace Period Days (after trial expires)</Label>
              <Input name="grace_period_days" type="number" defaultValue={policyData?.grace_period_days ?? 30} required />
              <p className="mt-1 text-xs text-bos-silver-dark">Tenant access after trial ends before suspension</p>
            </div>
            <Button type="submit" disabled={saveMut.isPending} className="w-full gap-2">
              <Save className="h-4 w-4" />
              {saveMut.isPending ? "Saving..." : "Update Limits"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
