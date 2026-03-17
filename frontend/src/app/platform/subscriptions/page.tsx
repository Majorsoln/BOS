"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Toast,
} from "@/components/ui";
import {
  getSubscriptions, activateSubscription, cancelSubscription,
} from "@/lib/api/saas";
import { formatDate } from "@/lib/utils";
import { Search, Play, XCircle } from "lucide-react";

export default function SubscriptionsPage() {
  const [businessId, setBusinessId] = useState("");
  const [sub, setSub] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showActivate, setShowActivate] = useState(false);
  const [showCancel, setShowCancel] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  async function handleSearch(e?: React.FormEvent) {
    e?.preventDefault?.();
    if (!businessId.trim()) return;
    setLoading(true);
    setError("");
    setSub(null);
    try {
      const res = await getSubscriptions({ status: undefined });
      const found = (res.data ?? []).find((s: { business_id: string }) => s.business_id === businessId.trim());
      if (found) {
        setSub(found);
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

  const s = sub;

  return (
    <div>
      <PageHeader
        title="Subscriptions"
        description="Search and manage tenant subscriptions"
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
              <InfoRow label="Services" value={(s.services as string) ?? "—"} />
              <InfoRow label="Activated" value={s.activated_at ? formatDate(s.activated_at as string) : "—"} />
              <InfoRow label="Billing Starts" value={s.billing_starts_at ? formatDate(s.billing_starts_at as string) : "—"} />
              <InfoRow label="Renewals" value={String(s.renewal_count ?? 0)} />
              <InfoRow label="Monthly Amount" value={(s.monthly_amount as string) ?? "—"} />
            </div>

            {/* Actions */}
            <div className="mt-6 flex flex-wrap gap-3 border-t border-bos-silver/20 pt-4">
              {s.status === "TRIAL" && (
                <Button onClick={() => setShowActivate(true)} className="gap-2">
                  <Play className="h-4 w-4" />
                  Activate
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
        description="Trial will be converted to a paid subscription. Tenant will start paying."
        confirmLabel="Activate"
        loading={activateMut.isPending}
      />

      {/* Cancel Dialog */}
      <ConfirmDialog
        open={showCancel}
        onClose={() => setShowCancel(false)}
        onConfirm={() => cancelMut.mutate({ business_id: businessId })}
        title="Cancel Subscription"
        description="Subscription will be permanently cancelled."
        confirmLabel="Cancel Subscription"
        confirmVariant="destructive"
        loading={cancelMut.isPending}
      />

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
