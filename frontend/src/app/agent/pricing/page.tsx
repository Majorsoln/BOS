"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Toast, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getPricingGovernance, getMyPricing, setMyPrice } from "@/lib/api/agents";
import { BOS_SERVICES } from "@/lib/constants";
import {
  DollarSign, Shield, ArrowUpDown, CheckCircle, AlertTriangle, Package,
} from "lucide-react";

type PriceRange = { min_amount: number; max_amount: number; currency: string };
type MyPrice = { amount: number; currency: string; updated_at?: string };

export default function AgentPricingPage() {
  const qc = useQueryClient();
  const [showSetPrice, setShowSetPrice] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const governance = useQuery({ queryKey: ["saas", "pricing-governance"], queryFn: getPricingGovernance });
  const myPricing = useQuery({ queryKey: ["agent", "pricing"], queryFn: getMyPricing });

  const ranges: Record<string, Record<string, PriceRange>> = governance.data?.data?.ranges ?? {};
  const myPrices: Record<string, MyPrice> = myPricing.data?.data?.prices ?? {};
  const regionCode: string = myPricing.data?.data?.region_code ?? "";
  const regionCurrency: string = myPricing.data?.data?.currency ?? "KES";

  const setPriceMut = useMutation({
    mutationFn: setMyPrice,
    onSuccess: () => {
      setShowSetPrice(null);
      qc.invalidateQueries({ queryKey: ["agent", "pricing"] });
      setToast({ message: "Price updated", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to update price", variant: "error" }),
  });

  function handleSetPrice(e: React.FormEvent) {
    e.preventDefault();
    if (!showSetPrice) return;
    const d = new FormData(e.target as HTMLFormElement);
    setPriceMut.mutate({
      service_key: showSetPrice,
      amount: Number(d.get("amount")),
    });
  }

  const currentRange = (svcKey: string): PriceRange | null => {
    return ranges[svcKey]?.[regionCode] ?? null;
  };

  const totalConfigured = BOS_SERVICES.filter((s) => myPrices[s.key]).length;
  const totalServices = BOS_SERVICES.length;

  return (
    <div>
      <PageHeader
        title="Service Pricing"
        description="Set your prices for each service within the platform-defined ranges"
      />

      {/* Governance Info */}
      <Card className="mb-6 border-blue-200/50 bg-blue-50/30 dark:border-blue-800/30 dark:bg-blue-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Shield className="mt-0.5 h-5 w-5 text-blue-600" />
            <div className="text-sm">
              <p className="font-semibold text-blue-700 dark:text-blue-400">Pricing Rules</p>
              <ul className="mt-1 list-disc pl-4 text-neutral-600 dark:text-neutral-400 space-y-0.5">
                <li>Main Administration sets allowable price ranges (minimum and maximum) per service</li>
                <li>You set the actual price your tenants pay — within the allowed range</li>
                <li>Prices below the minimum or above the maximum will be rejected</li>
                <li>Your region: <strong>{regionCode || "Not assigned"}</strong> | Currency: <strong>{regionCurrency}</strong></li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Progress */}
      <div className="mb-6 flex items-center gap-3">
        <div className="flex items-center gap-2 text-sm">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <span>
            <strong>{totalConfigured}</strong> of <strong>{totalServices}</strong> services priced
          </span>
        </div>
        {totalConfigured < totalServices && (
          <span className="text-xs text-amber-600 flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" /> Set all prices to start accepting tenants
          </span>
        )}
      </div>

      {/* Services */}
      <div className="space-y-4">
        {BOS_SERVICES.map((svc) => {
          const range = currentRange(svc.key);
          const price = myPrices[svc.key];
          const isWithinRange = price && range
            ? price.amount >= range.min_amount && price.amount <= range.max_amount
            : true;

          return (
            <Card key={svc.key}>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-bos-purple/10">
                      <Package className="h-5 w-5 text-bos-purple" />
                    </div>
                    <div>
                      <p className="font-semibold text-sm">{svc.name}</p>
                      <p className="text-xs text-bos-silver-dark">{svc.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {/* Range */}
                    {range ? (
                      <div className="text-right">
                        <p className="text-[11px] text-bos-silver-dark">Allowed Range</p>
                        <p className="font-mono text-xs">
                          <span className="text-green-700">{regionCurrency} {range.min_amount.toLocaleString()}</span>
                          {" — "}
                          <span className="text-red-700">{regionCurrency} {range.max_amount.toLocaleString()}</span>
                        </p>
                      </div>
                    ) : (
                      <div className="text-right">
                        <p className="text-[11px] text-bos-silver-dark">Range</p>
                        <p className="text-xs text-neutral-400">Not set by platform</p>
                      </div>
                    )}

                    {/* Your Price */}
                    <div className="text-right min-w-[120px]">
                      <p className="text-[11px] text-bos-silver-dark">Your Price</p>
                      {price ? (
                        <div className="flex items-center gap-1.5 justify-end">
                          <span className="font-mono text-sm font-bold text-bos-purple">
                            {regionCurrency} {price.amount.toLocaleString()}
                          </span>
                          {!isWithinRange && (
                            <AlertTriangle className="h-3.5 w-3.5 text-red-500" title="Out of allowed range" />
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-amber-600">Not set</span>
                      )}
                    </div>

                    <Button size="sm" onClick={() => setShowSetPrice(svc.key)} className="gap-1">
                      <DollarSign className="h-3 w-3" />
                      {price ? "Update" : "Set Price"}
                    </Button>
                  </div>
                </div>

                {/* Visual range indicator */}
                {range && price && (
                  <div className="mt-3 px-14">
                    <div className="relative h-2 rounded-full bg-neutral-100 dark:bg-neutral-800">
                      <div
                        className="absolute h-2 rounded-full bg-green-200 dark:bg-green-900"
                        style={{
                          left: "0%",
                          width: "100%",
                        }}
                      />
                      {/* Price marker */}
                      <div
                        className={`absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 ${
                          isWithinRange ? "border-bos-purple bg-white" : "border-red-500 bg-red-50"
                        }`}
                        style={{
                          left: `${Math.min(100, Math.max(0, ((price.amount - range.min_amount) / (range.max_amount - range.min_amount)) * 100))}%`,
                        }}
                      />
                    </div>
                    <div className="mt-1 flex justify-between text-[10px] text-bos-silver-dark font-mono">
                      <span>{regionCurrency} {range.min_amount.toLocaleString()}</span>
                      <span>{regionCurrency} {range.max_amount.toLocaleString()}</span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Set Price Dialog */}
      <FormDialog
        open={!!showSetPrice}
        onClose={() => setShowSetPrice(null)}
        title={`Set Price — ${BOS_SERVICES.find((s) => s.key === showSetPrice)?.name ?? ""}`}
        description={(() => {
          const range = showSetPrice ? currentRange(showSetPrice) : null;
          return range
            ? `Allowed range: ${regionCurrency} ${range.min_amount.toLocaleString()} — ${regionCurrency} ${range.max_amount.toLocaleString()} per month`
            : "No price range set by platform yet. You may set any price.";
        })()}
        onSubmit={handleSetPrice}
        submitLabel="Save Price"
        loading={setPriceMut.isPending}
      >
        <div>
          <Label>Monthly Amount ({regionCurrency})</Label>
          <Input
            name="amount"
            type="number"
            min={showSetPrice ? (currentRange(showSetPrice)?.min_amount ?? 0) : 0}
            max={showSetPrice ? (currentRange(showSetPrice)?.max_amount ?? undefined) : undefined}
            defaultValue={showSetPrice ? (myPrices[showSetPrice]?.amount ?? "") : ""}
            required
          />
          {showSetPrice && currentRange(showSetPrice) && (
            <p className="text-xs text-bos-silver-dark mt-1">
              Min: {regionCurrency} {currentRange(showSetPrice)!.min_amount.toLocaleString()} | Max: {regionCurrency} {currentRange(showSetPrice)!.max_amount.toLocaleString()}
            </p>
          )}
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
