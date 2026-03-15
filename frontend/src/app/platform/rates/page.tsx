"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast,
} from "@/components/ui";
import { getEffectiveRate, publishRateChange, getCombos } from "@/lib/api/saas";
import { REGIONS } from "@/lib/constants";
import { formatCurrency, formatDate } from "@/lib/utils";
import { Search, TrendingUp, AlertTriangle } from "lucide-react";

export default function RatesPage() {
  const [activeTab, setActiveTab] = useState<"check" | "publish">("check");
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  return (
    <div>
      <PageHeader
        title="Rate Governance"
        description="Simamia mabadiliko ya bei na kulinda tenants"
      />

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-bos-silver-light p-1 dark:bg-neutral-800 w-fit">
        <button
          onClick={() => setActiveTab("check")}
          className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${activeTab === "check" ? "bg-white text-bos-purple shadow-sm dark:bg-neutral-900" : "text-bos-silver-dark hover:text-neutral-900"}`}
        >
          Check Effective Rate
        </button>
        <button
          onClick={() => setActiveTab("publish")}
          className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${activeTab === "publish" ? "bg-white text-bos-purple shadow-sm dark:bg-neutral-900" : "text-bos-silver-dark hover:text-neutral-900"}`}
        >
          Publish Rate Change
        </button>
      </div>

      {activeTab === "check" ? (
        <EffectiveRateChecker />
      ) : (
        <RateChangePublisher onSuccess={() => setToast({ message: "Rate change published", variant: "success" })} onError={() => setToast({ message: "Failed to publish", variant: "error" })} />
      )}

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

function EffectiveRateChecker() {
  const [businessId, setBusinessId] = useState("");
  const [rate, setRate] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCheck(e: React.FormEvent) {
    e.preventDefault();
    if (!businessId.trim()) return;
    setLoading(true);
    setError("");
    setRate(null);
    try {
      const res = await getEffectiveRate(businessId.trim());
      setRate(res.data ?? res);
    } catch {
      setError("Failed to fetch effective rate");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Search className="h-5 w-5 text-bos-purple" />
            <CardTitle>Check Effective Rate</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCheck} className="flex gap-3">
            <Input
              placeholder="Business ID..."
              value={businessId}
              onChange={(e) => setBusinessId(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={loading}>
              {loading ? "Checking..." : "Check"}
            </Button>
          </form>

          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

          {rate && (
            <div className="mt-4 space-y-3 rounded-lg bg-bos-silver-light p-4 dark:bg-neutral-800">
              <div className="flex justify-between">
                <span className="text-sm text-bos-silver-dark">Effective Rate</span>
                <span className="text-lg font-bold text-bos-gold-dark">
                  {rate.monthly_amount != null
                    ? formatCurrency((rate.monthly_amount as number) * 100, (rate.currency as string) ?? "KES")
                    : "Free (Trial)"}
                </span>
              </div>
              {rate.rate_guaranteed_until ? (
                <div className="flex justify-between">
                  <span className="text-sm text-bos-silver-dark">Rate Guaranteed Until</span>
                  <span className="text-sm font-medium">{formatDate(rate.rate_guaranteed_until as string)}</span>
                </div>
              ) : null}
              {rate.is_trial != null ? (
                <div className="flex justify-between">
                  <span className="text-sm text-bos-silver-dark">Status</span>
                  <StatusBadge status={rate.is_trial ? "TRIAL" : "ACTIVE"} />
                </div>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function RateChangePublisher({ onSuccess, onError }: { onSuccess: () => void; onError: () => void }) {
  const combos = useQuery({ queryKey: ["saas", "combos"], queryFn: getCombos });
  const comboList = (combos.data?.data ?? []).filter((c: { status: string }) => c.status === "ACTIVE");

  const publishMut = useMutation({
    mutationFn: publishRateChange,
    onSuccess,
    onError,
  });

  function handlePublish(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const data = new FormData(form);
    const regionCode = data.get("region_code") as string;
    const region = REGIONS.find((r) => r.code === regionCode);
    publishMut.mutate({
      combo_id: data.get("combo_id") as string,
      region_code: regionCode,
      old_amount: Number(data.get("old_amount")),
      new_amount: Number(data.get("new_amount")),
      currency: region?.currency ?? "KES",
      effective_from: data.get("effective_from") as string,
    });
  }

  // Min date = 90 days from now
  const minDate = new Date();
  minDate.setDate(minDate.getDate() + 90);
  const minDateStr = minDate.toISOString().split("T")[0];

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-bos-purple" />
            <CardTitle>Publish Rate Change</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-orange-50 p-3 text-sm text-orange-800 dark:bg-orange-950 dark:text-orange-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>Rate changes require minimum 90 days advance notice. Increases &gt;25% trigger elevated notifications.</span>
          </div>

          <form onSubmit={handlePublish} className="space-y-4">
            <div>
              <Label htmlFor="combo_id">Combo</Label>
              <Select id="combo_id" name="combo_id" className="mt-1" required>
                <option value="">Select combo...</option>
                {comboList.map((c: { combo_id: string; name: string }) => (
                  <option key={c.combo_id} value={c.combo_id}>{c.name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="region_code">Region</Label>
              <Select id="region_code" name="region_code" className="mt-1" required>
                {REGIONS.map((r) => (
                  <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>
                ))}
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="old_amount">Old Amount</Label>
                <Input id="old_amount" name="old_amount" type="number" required className="mt-1" />
              </div>
              <div>
                <Label htmlFor="new_amount">New Amount</Label>
                <Input id="new_amount" name="new_amount" type="number" required className="mt-1" />
              </div>
            </div>
            <div>
              <Label htmlFor="effective_from">Effective From</Label>
              <Input id="effective_from" name="effective_from" type="date" min={minDateStr} required className="mt-1" />
            </div>
            <Button type="submit" disabled={publishMut.isPending} className="w-full">
              {publishMut.isPending ? "Publishing..." : "Publish Rate Change"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
