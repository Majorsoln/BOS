"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast,
} from "@/components/ui";
import {
  getSubscription, activateSubscription, cancelSubscription, changeCombo, startTrial, getCombos,
} from "@/lib/api/saas";
import { formatDate } from "@/lib/utils";
import { Search, Play, XCircle, RefreshCw, Plus } from "lucide-react";

export default function SubscriptionsPage() {
  const [businessId, setBusinessId] = useState("");
  const [sub, setSub] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showActivate, setShowActivate] = useState(false);
  const [showCancel, setShowCancel] = useState(false);
  const [showChangeCombo, setShowChangeCombo] = useState(false);
  const [showStartTrial, setShowStartTrial] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const combos = useQuery({ queryKey: ["saas", "combos"], queryFn: getCombos });
  const comboList = (combos.data?.data ?? []).filter((c: { status: string }) => c.status === "ACTIVE");

  async function handleSearch(e?: React.FormEvent) {
    e?.preventDefault?.();
    if (!businessId.trim()) return;
    setLoading(true);
    setError("");
    setSub(null);
    try {
      const res = await getSubscription(businessId.trim());
      if (res.data) {
        setSub(res.data);
      } else {
        setError("No subscription found for this business");
      }
    } catch {
      setError("No subscription found or failed to fetch");
    } finally {
      setLoading(false);
    }
  }

  const activateMut = useMutation({
    mutationFn: activateSubscription,
    onSuccess: () => { setShowActivate(false); setToast({ message: "Subscription activated", variant: "success" }); handleSearch(); },
    onError: () => setToast({ message: "Failed to activate", variant: "error" }),
  });

  const cancelMut = useMutation({
    mutationFn: cancelSubscription,
    onSuccess: () => { setShowCancel(false); setToast({ message: "Subscription cancelled", variant: "success" }); handleSearch(); },
    onError: () => setToast({ message: "Failed to cancel", variant: "error" }),
  });

  const changeMut = useMutation({
    mutationFn: changeCombo,
    onSuccess: () => { setShowChangeCombo(false); setToast({ message: "Combo changed", variant: "success" }); handleSearch(); },
    onError: () => setToast({ message: "Failed to change combo", variant: "error" }),
  });

  const trialMut = useMutation({
    mutationFn: startTrial,
    onSuccess: () => { setShowStartTrial(false); setToast({ message: "Trial started", variant: "success" }); handleSearch(); },
    onError: () => setToast({ message: "Failed to start trial", variant: "error" }),
  });

  function handleChangeCombo(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    changeMut.mutate({ business_id: businessId, new_combo_id: d.get("new_combo_id") as string });
  }

  function handleStartTrial(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    trialMut.mutate({
      business_id: d.get("business_id") as string,
      combo_id: d.get("combo_id") as string,
    });
  }

  const s = sub;

  return (
    <div>
      <PageHeader
        title="Subscriptions"
        description="Tafuta na simamia subscriptions za tenants"
        actions={
          <Button variant="outline" onClick={() => setShowStartTrial(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Start Trial
          </Button>
        }
      />

      {/* Search */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <form onSubmit={handleSearch} className="flex gap-3">
            <Input
              placeholder="Enter Business ID..."
              value={businessId}
              onChange={(e) => setBusinessId(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={loading} className="gap-2">
              <Search className="h-4 w-4" />
              {loading ? "Searching..." : "Search"}
            </Button>
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
              <InfoRow label="Business ID" value={(s.business_id as string) ?? "—"} mono />
              <InfoRow label="Combo" value={(s.combo_id as string) ?? "—"} />
              <InfoRow label="Plan" value={(s.plan_id as string) ?? "—"} />
              <InfoRow label="Activated" value={s.activated_at ? formatDate(s.activated_at as string) : "—"} />
              <InfoRow label="Billing Starts" value={s.billing_starts_at ? formatDate(s.billing_starts_at as string) : "—"} />
              <InfoRow label="Renewals" value={String(s.renewal_count ?? 0)} />
            </div>

            {/* Actions */}
            <div className="mt-6 flex flex-wrap gap-3 border-t border-bos-silver/20 pt-4">
              {s.status === "TRIAL" && (
                <Button onClick={() => setShowActivate(true)} className="gap-2">
                  <Play className="h-4 w-4" />
                  Activate
                </Button>
              )}
              {(s.status === "TRIAL" || s.status === "ACTIVE") && (
                <Button variant="outline" onClick={() => setShowChangeCombo(true)} className="gap-2">
                  <RefreshCw className="h-4 w-4" />
                  Change Combo
                </Button>
              )}
              {s.status !== "CANCELLED" && (
                <Button variant="destructive" onClick={() => setShowCancel(true)} className="gap-2">
                  <XCircle className="h-4 w-4" />
                  Cancel
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Activate Dialog */}
      <ConfirmDialog
        open={showActivate}
        onClose={() => setShowActivate(false)}
        onConfirm={() => activateMut.mutate({ business_id: businessId })}
        title="Activate Subscription"
        description="Trial itabadilishwa kuwa subscription ya kulipa. Tenant itaanza kulipa."
        confirmLabel="Activate"
        loading={activateMut.isPending}
      />

      {/* Cancel Dialog */}
      <ConfirmDialog
        open={showCancel}
        onClose={() => setShowCancel(false)}
        onConfirm={() => cancelMut.mutate({ business_id: businessId })}
        title="Cancel Subscription"
        description="Subscription itasimamishwa kabisa. Hii ni hali ya mwisho — haiwezi kurudishwa."
        confirmLabel="Cancel Subscription"
        confirmVariant="destructive"
        loading={cancelMut.isPending}
      />

      {/* Change Combo Dialog */}
      <FormDialog
        open={showChangeCombo}
        onClose={() => setShowChangeCombo(false)}
        title="Change Combo"
        description="Badilisha engine combo kwa tenant hii"
        onSubmit={handleChangeCombo}
        submitLabel="Change"
        loading={changeMut.isPending}
      >
        <div>
          <Label htmlFor="new_combo_id">New Combo</Label>
          <Select id="new_combo_id" name="new_combo_id" className="mt-1" required>
            <option value="">Select combo...</option>
            {comboList.map((c: { combo_id: string; name: string }) => (
              <option key={c.combo_id} value={c.combo_id}>{c.name}</option>
            ))}
          </Select>
        </div>
      </FormDialog>

      {/* Start Trial Dialog */}
      <FormDialog
        open={showStartTrial}
        onClose={() => setShowStartTrial(false)}
        title="Start Trial Subscription"
        description="Anza trial subscription kwa tenant mpya"
        onSubmit={handleStartTrial}
        submitLabel="Start Trial"
        loading={trialMut.isPending}
      >
        <div>
          <Label htmlFor="trial_biz_id">Business ID</Label>
          <Input id="trial_biz_id" name="business_id" required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="trial_combo">Combo</Label>
          <Select id="trial_combo" name="combo_id" className="mt-1" required>
            <option value="">Select combo...</option>
            {comboList.map((c: { combo_id: string; name: string }) => (
              <option key={c.combo_id} value={c.combo_id}>{c.name}</option>
            ))}
          </Select>
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
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
