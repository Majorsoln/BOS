"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Toast, Badge,
} from "@/components/ui";
import { getTrialAgreement, extendTrial, convertTrial } from "@/lib/api/saas";
import { formatDate, formatCurrency } from "@/lib/utils";
import { Search, Clock, CalendarDays, CreditCard, Plus, ArrowRightCircle } from "lucide-react";

export default function TrialsPage() {
  const queryClient = useQueryClient();
  const [businessId, setBusinessId] = useState("");
  const [agreement, setAgreement] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showExtend, setShowExtend] = useState(false);
  const [showConvert, setShowConvert] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!businessId.trim()) return;
    setLoading(true);
    setError("");
    setAgreement(null);
    try {
      const res = await getTrialAgreement(businessId.trim());
      if (res.data) {
        setAgreement(res.data);
      } else {
        setError("No trial agreement found for this business");
      }
    } catch {
      setError("Failed to fetch trial agreement");
    } finally {
      setLoading(false);
    }
  }

  const extendMut = useMutation({
    mutationFn: extendTrial,
    onSuccess: () => {
      setShowExtend(false);
      setToast({ message: "Trial extended", variant: "success" });
      // Re-fetch
      handleSearch({ preventDefault: () => {} } as React.FormEvent);
    },
    onError: () => setToast({ message: "Failed to extend trial", variant: "error" }),
  });

  const convertMut = useMutation({
    mutationFn: convertTrial,
    onSuccess: () => {
      setShowConvert(false);
      setToast({ message: "Trial converted to paying", variant: "success" });
      handleSearch({ preventDefault: () => {} } as React.FormEvent);
    },
    onError: () => setToast({ message: "Failed to convert trial", variant: "error" }),
  });

  function handleExtend(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const data = new FormData(form);
    extendMut.mutate({
      business_id: businessId,
      extra_days: Number(data.get("extra_days")),
      reason: data.get("reason") as string,
    });
  }

  const a = agreement as Record<string, unknown> | null;

  return (
    <div>
      <PageHeader
        title="Active Trials"
        description="Search and manage tenant trial agreements"
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
                  : "—"
              } />
              <InfoBlock icon={Clock} label="Combo" value={(a.combo_id as string) || "—"} />
            </div>

            {a.promo_code ? (
              <div className="mt-4">
                <Badge variant="gold">Promo: {a.promo_code as string}</Badge>
              </div>
            ) : null}

            {/* Actions */}
            {a.status === "ACTIVE" && (
              <div className="mt-6 flex gap-3 border-t border-bos-silver/20 pt-4">
                <Button variant="outline" onClick={() => setShowExtend(true)} className="gap-2">
                  <Plus className="h-4 w-4" />
                  Extend Trial
                </Button>
                <Button onClick={() => setShowConvert(true)} className="gap-2">
                  <ArrowRightCircle className="h-4 w-4" />
                  Convert to Paying
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Extend Dialog */}
      <FormDialog
        open={showExtend}
        onClose={() => setShowExtend(false)}
        title="Extend Trial"
        description="Add extra trial days for this tenant"
        onSubmit={handleExtend}
        submitLabel="Extend"
        loading={extendMut.isPending}
      >
        <div>
          <Label htmlFor="extra_days">Extra Days</Label>
          <Input id="extra_days" name="extra_days" type="number" placeholder="e.g. 30" required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="reason">Reason</Label>
          <Input id="reason" name="reason" placeholder="e.g. Customer support request" className="mt-1" />
        </div>
      </FormDialog>

      {/* Convert Dialog */}
      <ConfirmDialog
        open={showConvert}
        onClose={() => setShowConvert(false)}
        onConfirm={() => convertMut.mutate({ business_id: businessId })}
        title="Convert Trial to Paying"
        description="Tenant will start paying from the next billing day. This action cannot be undone."
        confirmLabel="Convert"
        loading={convertMut.isPending}
      />

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

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
