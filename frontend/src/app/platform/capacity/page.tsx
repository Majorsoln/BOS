"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast,
} from "@/components/ui";
import { getCapacityPricing, setCapacityTierRate } from "@/lib/api/saas";
import { CAPACITY_DIMENSIONS, REGIONS } from "@/lib/constants";
import { Layers, DollarSign, Building2, FileText, Users, Cpu } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const DIMENSION_ICONS: Record<string, LucideIcon> = {
  BRANCHES: Building2,
  DOCUMENTS: FileText,
  USERS: Users,
  AI_TOKENS: Cpu,
};

type TierRateMap = Record<string, Record<string, Record<string, { monthly_amount: number; currency: string }>>>;

export default function CapacityPage() {
  const qc = useQueryClient();
  const [rateTarget, setRateTarget] = useState<{ dimension: string; tier_key: string } | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const pricing = useQuery({ queryKey: ["saas", "capacity"], queryFn: getCapacityPricing });

  const rateMut = useMutation({
    mutationFn: setCapacityTierRate,
    onSuccess: () => { setRateTarget(null); qc.invalidateQueries({ queryKey: ["saas", "capacity"] }); setToast({ message: "Tier rate updated", variant: "success" }); },
    onError: () => setToast({ message: "Failed to update rate", variant: "error" }),
  });

  function handleSetRate(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    const region = REGIONS.find((r) => r.code === d.get("region_code"));
    rateMut.mutate({
      dimension: rateTarget!.dimension,
      tier_key: rateTarget!.tier_key,
      region_code: d.get("region_code") as string,
      currency: region?.currency ?? "USD",
      monthly_amount: Number(d.get("monthly_amount")),
    });
  }

  // { BRANCHES: { BRANCH_1: { KE: { monthly_amount, currency } } } }
  const tierRates: TierRateMap = pricing.data?.data ?? {};

  return (
    <div>
      <PageHeader
        title="Capacity & Consumption Tiers"
        description="Define capacity tier pricing per region. Tiers are global — only prices differ by region."
      />

      <div className="mb-6 rounded-lg border border-bos-purple/20 bg-bos-purple/5 p-4">
        <h3 className="mb-1 text-sm font-semibold text-bos-purple">How Capacity Pricing Works</h3>
        <p className="text-xs text-bos-silver-dark">
          Capacity charges are <strong>added on top</strong> of the service total. Each dimension has tiers
          with increasing limits. Set the monthly price per tier per region. The first tier can be set to 0
          to include a base allocation with the service.
        </p>
      </div>

      <div className="space-y-6">
        {CAPACITY_DIMENSIONS.map((dim) => {
          const Icon = DIMENSION_ICONS[dim.key] ?? Layers;
          const dimRates = tierRates[dim.key] ?? {};

          return (
            <Card key={dim.key}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-bos-purple/10">
                    <Icon className="h-5 w-5 text-bos-purple" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{dim.label}</CardTitle>
                    <p className="text-xs text-bos-silver-dark">{dim.description}</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-bos-silver/20">
                        <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-bos-silver-dark">Tier</th>
                        <th className="px-3 py-2 text-right text-xs font-semibold uppercase text-bos-silver-dark">Limit</th>
                        {REGIONS.slice(0, 5).map((r) => (
                          <th key={r.code} className="px-3 py-2 text-right text-xs font-semibold uppercase text-bos-silver-dark">
                            {r.code}
                          </th>
                        ))}
                        <th className="px-3 py-2 text-right text-xs font-semibold uppercase text-bos-silver-dark">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dim.tiers.map((tier) => {
                        const tRates = dimRates[tier.key] ?? {};
                        return (
                          <tr key={tier.key} className="border-b border-bos-silver/10">
                            <td className="px-3 py-2 font-medium">{tier.label}</td>
                            <td className="px-3 py-2 text-right font-mono text-xs">
                              {tier.limit === -1 ? "∞" : tier.limit.toLocaleString()}
                            </td>
                            {REGIONS.slice(0, 5).map((r) => {
                              const rate = tRates[r.code];
                              return (
                                <td key={r.code} className="px-3 py-2 text-right text-xs">
                                  {rate
                                    ? <span className="font-mono">{r.currency} {rate.monthly_amount.toLocaleString()}</span>
                                    : <span className="text-bos-silver">—</span>
                                  }
                                </td>
                              );
                            })}
                            <td className="px-3 py-2 text-right">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setRateTarget({ dimension: dim.key, tier_key: tier.key })}
                                className="gap-1"
                              >
                                <DollarSign className="h-3 w-3" />
                                Set
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Set Tier Rate Dialog */}
      <FormDialog
        open={!!rateTarget}
        onClose={() => setRateTarget(null)}
        title={`Set Tier Rate`}
        description={rateTarget ? `${CAPACITY_DIMENSIONS.find((d) => d.key === rateTarget.dimension)?.label} — ${
          CAPACITY_DIMENSIONS.find((d) => d.key === rateTarget.dimension)?.tiers.find((t) => t.key === rateTarget.tier_key)?.label
        }` : ""}
        onSubmit={handleSetRate}
        submitLabel="Save Rate"
        loading={rateMut.isPending}
      >
        <div>
          <Label htmlFor="ct_region">Region</Label>
          <Select id="ct_region" name="region_code" required className="mt-1">
            <option value="">Select region...</option>
            {REGIONS.map((r) => <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="ct_amount">Monthly Amount (local currency, 0 = included free)</Label>
          <Input id="ct_amount" name="monthly_amount" type="number" min={0} required className="mt-1" />
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
