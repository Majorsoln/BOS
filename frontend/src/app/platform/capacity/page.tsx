"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
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

const DIMENSION_COLORS: Record<string, string> = {
  BRANCHES: "bg-blue-100 text-blue-600 dark:bg-blue-900/30",
  DOCUMENTS: "bg-amber-100 text-amber-600 dark:bg-amber-900/30",
  USERS: "bg-green-100 text-green-600 dark:bg-green-900/30",
  AI_TOKENS: "bg-purple-100 text-purple-600 dark:bg-purple-900/30",
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

  const tierRates: TierRateMap = pricing.data?.data ?? {};

  // Count configured rates
  const totalTiers = CAPACITY_DIMENSIONS.reduce((s, d) => s + d.tiers.length, 0);
  const configuredRates = Object.values(tierRates).reduce(
    (s, dim) => s + Object.values(dim).reduce((s2, tier) => s2 + Object.keys(tier).length, 0),
    0,
  );

  return (
    <div>
      <PageHeader
        title="Capacity & Consumption Tiers"
        description="Define capacity tier pricing per region. Tiers are global — only prices differ by region."
      />

      {/* Summary Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bos-purple/10">
              <Layers className="h-5 w-5 text-bos-purple" />
            </div>
            <div>
              <p className="text-2xl font-bold">{CAPACITY_DIMENSIONS.length}</p>
              <p className="text-xs text-bos-silver-dark">Dimensions</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-green-100 dark:bg-green-900/30">
              <Building2 className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{totalTiers}</p>
              <p className="text-xs text-bos-silver-dark">Total Tiers</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bos-gold-light">
              <DollarSign className="h-5 w-5 text-bos-gold-dark" />
            </div>
            <div>
              <p className="text-2xl font-bold">{configuredRates}</p>
              <p className="text-xs text-bos-silver-dark">Rates Configured</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Info Banner */}
      <div className="mb-6 rounded-lg border border-bos-purple/20 bg-bos-purple/5 p-4">
        <h3 className="mb-1 text-sm font-semibold text-bos-purple">How Capacity Pricing Works</h3>
        <p className="text-xs text-bos-silver-dark">
          Capacity charges are <strong>added on top</strong> of the service total. Each dimension has tiers
          with increasing limits. Set the monthly price per tier per region. The first tier can be set to 0
          to include a base allocation with the service.
        </p>
      </div>

      {/* Dimension Cards */}
      <div className="space-y-6">
        {CAPACITY_DIMENSIONS.map((dim) => {
          const Icon = DIMENSION_ICONS[dim.key] ?? Layers;
          const colorClass = DIMENSION_COLORS[dim.key] ?? "bg-neutral-100 text-neutral-600";
          const dimRates = tierRates[dim.key] ?? {};

          return (
            <Card key={dim.key}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${colorClass}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{dim.label}</CardTitle>
                    <p className="text-xs text-bos-silver-dark">{dim.description}</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-bos-silver-light/50 dark:bg-neutral-900 hover:bg-bos-silver-light/50">
                      <TableHead className="text-xs h-9">Tier</TableHead>
                      <TableHead className="text-right text-xs h-9 w-20">Limit</TableHead>
                      {REGIONS.map((r) => (
                        <TableHead key={r.code} className="text-right text-xs h-9 px-2 w-24">
                          {r.code} ({r.currency})
                        </TableHead>
                      ))}
                      <TableHead className="text-right text-xs h-9 w-16">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dim.tiers.map((tier) => {
                      const tRates = dimRates[tier.key] ?? {};
                      return (
                        <TableRow key={tier.key}>
                          <TableCell className="font-medium py-2">{tier.label}</TableCell>
                          <TableCell className="text-right py-2">
                            <Badge variant="outline" className="font-mono">
                              {tier.limit === -1 ? "\u221E" : tier.limit.toLocaleString()}
                            </Badge>
                          </TableCell>
                          {REGIONS.map((r) => {
                            const rate = tRates[r.code];
                            return (
                              <TableCell key={r.code} className="text-right py-2 px-2">
                                {rate ? (
                                  <span className="font-mono text-xs font-semibold">
                                    {rate.monthly_amount.toLocaleString()}
                                  </span>
                                ) : (
                                  <span className="text-xs text-neutral-300 dark:text-neutral-600">—</span>
                                )}
                              </TableCell>
                            );
                          })}
                          <TableCell className="text-right py-2">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setRateTarget({ dimension: dim.key, tier_key: tier.key })}
                              className="gap-1 h-7 px-2"
                            >
                              <DollarSign className="h-3 w-3" />
                              Set
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Set Tier Rate Dialog */}
      <FormDialog
        open={!!rateTarget}
        onClose={() => setRateTarget(null)}
        title="Set Tier Rate"
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
