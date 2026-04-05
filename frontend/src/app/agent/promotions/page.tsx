"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
} from "@/components/ui";
import { getMyPromotions, createMyPromotion, requestCostShare, getDiscountGovernance } from "@/lib/api/agents";
import {
  Megaphone, Plus, HandCoins, Percent, DollarSign, Gift, Calendar, Users, Tag, ShoppingCart, Zap, AlertTriangle, Shield, Info,
} from "lucide-react";

type Strategy = "PERCENTAGE" | "FIXED_AMOUNT" | "BUY_ONE_GET_ONE" | "EXTENDED_TRIAL" | "BUNDLE_DISCOUNT" | "SEASONAL" | "REFERRAL_BONUS" | "FIRST_MONTH_FREE";

const STRATEGIES: { key: Strategy; label: string; description: string; icon: React.ElementType }[] = [
  { key: "PERCENTAGE", label: "Percentage Discount", description: "Flat % off the monthly subscription price", icon: Percent },
  { key: "FIXED_AMOUNT", label: "Fixed Amount Credit", description: "Fixed credit applied to the first invoice", icon: DollarSign },
  { key: "BUY_ONE_GET_ONE", label: "Buy One Get One", description: "Subscribe to one service, get another free for a period", icon: Gift },
  { key: "EXTENDED_TRIAL", label: "Extended Trial", description: "Extra trial days beyond the default trial period", icon: Calendar },
  { key: "BUNDLE_DISCOUNT", label: "Bundle Discount", description: "Discount when subscribing to multiple services together", icon: ShoppingCart },
  { key: "SEASONAL", label: "Seasonal Promotion", description: "Time-limited discount for a specific season or event", icon: Tag },
  { key: "REFERRAL_BONUS", label: "Referral Bonus", description: "Reward for referring new tenants who subscribe", icon: Users },
  { key: "FIRST_MONTH_FREE", label: "First Month Free", description: "Waive the first month subscription completely", icon: Zap },
];

const STRATEGY_BADGE: Record<string, "purple" | "gold" | "outline"> = {
  PERCENTAGE: "purple",
  FIXED_AMOUNT: "gold",
  BUY_ONE_GET_ONE: "purple",
  EXTENDED_TRIAL: "outline",
  BUNDLE_DISCOUNT: "purple",
  SEASONAL: "gold",
  REFERRAL_BONUS: "outline",
  FIRST_MONTH_FREE: "gold",
};

export default function AgentPromotionsPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [showCostShare, setShowCostShare] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const promos = useQuery({ queryKey: ["agent", "promotions"], queryFn: getMyPromotions });
  const governance = useQuery({ queryKey: ["saas", "discount-governance"], queryFn: getDiscountGovernance });

  const limits = governance.data?.data ?? {};
  const maxPlatformDiscount = limits.max_platform_discount_pct ?? 25;
  const maxRlaFundedDiscount = limits.max_rla_funded_discount_pct ?? 15;
  const maxTrialDays = limits.max_trial_days ?? 90;
  const maxBudgetPerPeriod = limits.max_budget_per_period ?? 0;
  const maxFixedAmount = limits.max_fixed_amount ?? 0;
  const maxBundleDiscount = limits.max_bundle_discount_pct ?? 30;
  const totalMaxDiscount = maxPlatformDiscount + maxRlaFundedDiscount;

  const createMut = useMutation({
    mutationFn: createMyPromotion,
    onSuccess: () => {
      setShowCreate(false);
      setSelectedStrategy(null);
      qc.invalidateQueries({ queryKey: ["agent", "promotions"] });
      setToast({ message: "Promotion created", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to create promotion", variant: "error" }),
  });

  const costShareMut = useMutation({
    mutationFn: requestCostShare,
    onSuccess: () => { setShowCostShare(false); setToast({ message: "Cost-share request submitted", variant: "success" }); },
    onError: () => setToast({ message: "Failed to submit request", variant: "error" }),
  });

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedStrategy) return;
    const d = new FormData(e.target as HTMLFormElement);
    createMut.mutate({
      promo_code: d.get("promo_code") as string,
      strategy: selectedStrategy,
      discount_pct: Number(d.get("discount_pct") ?? 0),
      fixed_amount: Number(d.get("fixed_amount") ?? 0),
      extra_trial_days: Number(d.get("extra_trial_days") ?? 0),
      bundle_discount_pct: Number(d.get("bundle_discount_pct") ?? 0),
      free_months: Number(d.get("free_months") ?? 0),
      max_uses: Number(d.get("max_uses") ?? 0),
      valid_until: d.get("valid_until") as string,
      description: d.get("description") as string || undefined,
    });
  }

  function handleCostShare(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    costShareMut.mutate({
      promotion_description: d.get("promotion_description") as string,
      total_cost: Number(d.get("total_cost")),
      requested_platform_share_pct: Number(d.get("requested_platform_share_pct")),
      justification: d.get("justification") as string,
    });
  }

  const promoList = promos.data?.data ?? [];

  return (
    <div>
      <PageHeader
        title="Promotions"
        description="Create and manage promotions for your region within platform-set limits"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setShowCostShare(true)} className="gap-2">
              <HandCoins className="h-4 w-4" />
              Request Cost-Share
            </Button>
            <Button onClick={() => setShowCreate(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Create Promotion
            </Button>
          </div>
        }
      />

      {/* Limits Banner */}
      <Card className="mb-6 border-blue-200/50 bg-blue-50/30 dark:border-blue-800/30 dark:bg-blue-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Shield className="mt-0.5 h-5 w-5 text-blue-600" />
            <div className="w-full">
              <p className="font-semibold text-blue-700 dark:text-blue-400 mb-3">Platform Promotion Limits</p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <LimitPill label="Platform-Funded" value={`${maxPlatformDiscount}%`} />
                <LimitPill label="RLA-Funded Cap" value={`${maxRlaFundedDiscount}%`} />
                <LimitPill label="Total Max Discount" value={`${totalMaxDiscount}%`} />
                <LimitPill label="Trial Extension" value={`${maxTrialDays} days`} />
                <LimitPill label="Fixed Credit Cap" value={maxFixedAmount > 0 ? maxFixedAmount.toLocaleString() : "None"} />
                <LimitPill label="Bundle Cap" value={`${maxBundleDiscount}%`} />
              </div>
              <p className="mt-3 text-xs text-blue-600 dark:text-blue-400">
                <AlertTriangle className="inline h-3 w-3 mr-1" />
                Discounts up to {maxPlatformDiscount}% are platform-funded. Anything between {maxPlatformDiscount}% and {totalMaxDiscount}% is deducted from your share. Exceeding {totalMaxDiscount}% is not allowed.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Active Promotions */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Megaphone className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">My Promotions</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Strategy</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Value</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Uses</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Valid Until</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Liability</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Status</th>
                </tr>
              </thead>
              <tbody>
                {promoList.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-bos-silver-dark">
                    <Megaphone className="mx-auto mb-2 h-5 w-5" />
                    No promotions yet. Choose a strategy below to create one.
                  </td></tr>
                )}
                {promoList.map((p: {
                  id: string; promo_code: string; strategy?: string; discount_pct?: number;
                  fixed_amount?: number; extra_trial_days?: number; bundle_discount_pct?: number;
                  used_count: number; max_uses: number; valid_until: string;
                  description?: string; status: string;
                }) => {
                  const pct = p.discount_pct ?? p.bundle_discount_pct ?? 0;
                  const exceedsPlatform = pct > maxPlatformDiscount;
                  const valueDisplay = p.strategy === "FIXED_AMOUNT" ? p.fixed_amount?.toLocaleString() ?? "—"
                    : p.strategy === "EXTENDED_TRIAL" ? `${p.extra_trial_days ?? 0} days`
                    : p.strategy === "FIRST_MONTH_FREE" ? "1 month"
                    : `${pct}%`;

                  return (
                    <tr key={p.id} className="border-b border-bos-silver/10 hover:bg-bos-silver-light/50 dark:hover:bg-neutral-900/50">
                      <td className="px-4 py-3 font-mono font-bold">{p.promo_code}</td>
                      <td className="px-4 py-3">
                        <Badge variant={STRATEGY_BADGE[p.strategy ?? "PERCENTAGE"] ?? "outline"}>
                          {(p.strategy ?? "PERCENTAGE").replace(/_/g, " ")}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-bos-purple">{valueDisplay}</td>
                      <td className="px-4 py-3 text-right">
                        <Badge variant="outline">{p.used_count ?? 0}/{p.max_uses}</Badge>
                      </td>
                      <td className="px-4 py-3 text-bos-silver-dark">{p.valid_until}</td>
                      <td className="px-4 py-3">
                        {exceedsPlatform ? (
                          <span className="inline-flex items-center gap-1 text-xs text-amber-600">
                            <AlertTriangle className="h-3 w-3" /> Your cost ({pct - maxPlatformDiscount}%)
                          </span>
                        ) : (
                          <span className="text-xs text-green-600">Platform-funded</span>
                        )}
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Strategy Picker + Create Dialog */}
      {showCreate && !selectedStrategy && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/50" onClick={() => setShowCreate(false)} />
          <div className="relative z-50 w-full max-w-2xl rounded-xl bg-white p-6 shadow-lg dark:bg-neutral-900 max-h-[85vh] overflow-y-auto">
            <h2 className="text-lg font-bold mb-1">Choose Promotion Strategy</h2>
            <p className="text-sm text-bos-silver-dark mb-4">Select how you want to attract and retain tenants</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {STRATEGIES.map((s) => {
                const Icon = s.icon;
                return (
                  <button
                    key={s.key}
                    onClick={() => setSelectedStrategy(s.key)}
                    className="flex items-start gap-3 rounded-lg border border-bos-silver/20 p-4 text-left transition-colors hover:border-bos-purple hover:bg-bos-purple/5"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-bos-purple/10">
                      <Icon className="h-5 w-5 text-bos-purple" />
                    </div>
                    <div>
                      <p className="font-semibold text-sm">{s.label}</p>
                      <p className="text-xs text-bos-silver-dark mt-0.5">{s.description}</p>
                    </div>
                  </button>
                );
              })}
            </div>
            <div className="mt-4 flex justify-end">
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </div>
        </div>
      )}

      {/* Strategy-Specific Form */}
      <FormDialog
        open={!!selectedStrategy}
        onClose={() => { setSelectedStrategy(null); setShowCreate(false); }}
        title={`Create ${STRATEGIES.find((s) => s.key === selectedStrategy)?.label ?? "Promotion"}`}
        description={STRATEGIES.find((s) => s.key === selectedStrategy)?.description}
        onSubmit={handleCreate}
        submitLabel="Create Promotion"
        loading={createMut.isPending}
      >
        {/* Limit warning */}
        <div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-950/30">
          <div className="flex items-start gap-2">
            <Info className="mt-0.5 h-4 w-4 text-blue-600 shrink-0" />
            <p className="text-xs text-blue-700 dark:text-blue-400">
              {selectedStrategy === "PERCENTAGE" && `Max discount: ${totalMaxDiscount}%. Up to ${maxPlatformDiscount}% is platform-funded, the rest is your liability.`}
              {selectedStrategy === "FIXED_AMOUNT" && `Max credit per redemption: ${maxFixedAmount > 0 ? maxFixedAmount.toLocaleString() : "No limit set"}.`}
              {selectedStrategy === "EXTENDED_TRIAL" && `Max extra trial days: ${maxTrialDays}.`}
              {selectedStrategy === "BUNDLE_DISCOUNT" && `Max bundle discount: ${maxBundleDiscount}%.`}
              {selectedStrategy === "SEASONAL" && `Max seasonal discount: ${totalMaxDiscount}%. Platform-funded up to ${maxPlatformDiscount}%.`}
              {selectedStrategy === "REFERRAL_BONUS" && `Referral bonuses are platform-funded up to ${maxPlatformDiscount}% discount equivalent.`}
              {selectedStrategy === "BUY_ONE_GET_ONE" && `BOGO cost is split: platform funds up to ${maxPlatformDiscount}% of the free service value.`}
              {selectedStrategy === "FIRST_MONTH_FREE" && `First month waiver is equivalent to 100% discount for 1 month. Excess beyond ${maxPlatformDiscount}% is your cost.`}
            </p>
          </div>
        </div>

        <div>
          <Label htmlFor="promo_code">Promo Code</Label>
          <Input id="promo_code" name="promo_code" required className="mt-1" placeholder="e.g. DUKA2026" />
        </div>

        {/* Strategy-specific fields */}
        {(selectedStrategy === "PERCENTAGE" || selectedStrategy === "SEASONAL") && (
          <div>
            <Label htmlFor="discount_pct">Discount %</Label>
            <Input id="discount_pct" name="discount_pct" type="number" min={1} max={totalMaxDiscount} required className="mt-1" />
            {totalMaxDiscount > 0 && (
              <p className="text-xs text-bos-silver-dark mt-1">
                1–{maxPlatformDiscount}% = platform-funded | {maxPlatformDiscount + 1}–{totalMaxDiscount}% = your liability
              </p>
            )}
          </div>
        )}

        {selectedStrategy === "FIXED_AMOUNT" && (
          <div>
            <Label htmlFor="fixed_amount">Credit Amount</Label>
            <Input id="fixed_amount" name="fixed_amount" type="number" min={1}
              max={maxFixedAmount > 0 ? maxFixedAmount : undefined} required className="mt-1" />
            {maxFixedAmount > 0 && <p className="text-xs text-bos-silver-dark mt-1">Max: {maxFixedAmount.toLocaleString()}</p>}
          </div>
        )}

        {selectedStrategy === "EXTENDED_TRIAL" && (
          <div>
            <Label htmlFor="extra_trial_days">Extra Trial Days</Label>
            <Input id="extra_trial_days" name="extra_trial_days" type="number" min={1} max={maxTrialDays} required className="mt-1" />
            <p className="text-xs text-bos-silver-dark mt-1">Max: {maxTrialDays} days</p>
          </div>
        )}

        {selectedStrategy === "BUNDLE_DISCOUNT" && (
          <div>
            <Label htmlFor="bundle_discount_pct">Bundle Discount %</Label>
            <Input id="bundle_discount_pct" name="bundle_discount_pct" type="number" min={1} max={maxBundleDiscount} required className="mt-1" />
            <p className="text-xs text-bos-silver-dark mt-1">Max: {maxBundleDiscount}%</p>
          </div>
        )}

        {selectedStrategy === "BUY_ONE_GET_ONE" && (
          <div>
            <Label htmlFor="free_months">Free Months for Second Service</Label>
            <Input id="free_months" name="free_months" type="number" min={1} max={3} required className="mt-1" />
            <p className="text-xs text-bos-silver-dark mt-1">Typically 1–3 months</p>
          </div>
        )}

        {selectedStrategy === "FIRST_MONTH_FREE" && (
          <div className="rounded-lg bg-amber-50 p-3 dark:bg-amber-950/30">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-600 shrink-0" />
              <p className="text-xs text-amber-700 dark:text-amber-400">
                First month free = 100% discount for month 1. The platform funds {maxPlatformDiscount}% of the monthly rate. The remaining {100 - maxPlatformDiscount}% is deducted from your share.
              </p>
            </div>
          </div>
        )}

        {selectedStrategy === "REFERRAL_BONUS" && (
          <div>
            <Label htmlFor="discount_pct">Referral Discount %</Label>
            <Input id="discount_pct" name="discount_pct" type="number" min={1} max={totalMaxDiscount} required className="mt-1" />
            <p className="text-xs text-bos-silver-dark mt-1">Applied to the referee&apos;s first billing cycle</p>
          </div>
        )}

        <div>
          <Label htmlFor="max_uses">Max Redemptions</Label>
          <Input id="max_uses" name="max_uses" type="number" min={1} required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="valid_until">Valid Until</Label>
          <Input id="valid_until" name="valid_until" type="date" required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="promo_desc">Description (optional)</Label>
          <Input id="promo_desc" name="description" className="mt-1" placeholder="What is this promotion for?" />
        </div>
      </FormDialog>

      {/* Cost-Share Request Dialog */}
      <FormDialog
        open={showCostShare}
        onClose={() => setShowCostShare(false)}
        title="Request Cost-Share"
        description="Request platform co-funding for a marketing or promotional activity. Submit your proposal for review."
        onSubmit={handleCostShare}
        submitLabel="Submit Request"
        loading={costShareMut.isPending}
      >
        <div>
          <Label htmlFor="cs_desc">Promotion Description</Label>
          <Input id="cs_desc" name="promotion_description" required className="mt-1" placeholder="e.g. Radio campaign in Nairobi" />
        </div>
        <div>
          <Label htmlFor="cs_cost">Total Cost</Label>
          <Input id="cs_cost" name="total_cost" type="number" min={1} required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="cs_share">Requested Platform Share %</Label>
          <Input id="cs_share" name="requested_platform_share_pct" type="number" min={10} max={80} required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="cs_justification">Justification</Label>
          <Input id="cs_justification" name="justification" required className="mt-1" placeholder="Why should the platform co-fund this?" />
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

function LimitPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/60 dark:bg-neutral-800/60 px-3 py-2 text-center">
      <p className="text-[11px] text-blue-600 dark:text-blue-400">{label}</p>
      <p className="text-sm font-bold">{value}</p>
    </div>
  );
}
