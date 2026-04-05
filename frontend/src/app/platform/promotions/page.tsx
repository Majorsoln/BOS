"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Card, CardContent, CardHeader, CardTitle, Toast, Badge, Button, Input, Label,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Select,
} from "@/components/ui";
import { getPromos } from "@/lib/api/saas";
import { getDiscountGovernance, setDiscountGovernance } from "@/lib/api/agents";
import { formatDate } from "@/lib/utils";
import {
  Tag, Eye, Shield, TrendingUp, AlertTriangle, Ban, CheckCircle, Settings, Percent, DollarSign, Calendar,
} from "lucide-react";

const PROMO_TYPE_BADGE: Record<string, "purple" | "gold" | "outline"> = {
  DISCOUNT: "purple",
  CREDIT: "gold",
  EXTENDED_TRIAL: "outline",
  ENGINE_BONUS: "outline",
  BUNDLE_DISCOUNT: "purple",
  PERCENTAGE: "purple",
  FIXED_AMOUNT: "gold",
  BUY_ONE_GET_ONE: "purple",
  SEASONAL: "outline",
  REFERRAL_BONUS: "outline",
};

export default function PromotionsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [showDeactivate, setShowDeactivate] = useState<string | null>(null);
  const [showEditLimits, setShowEditLimits] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const promos = useQuery({ queryKey: ["saas", "promos"], queryFn: getPromos });
  const governance = useQuery({ queryKey: ["saas", "discount-governance"], queryFn: getDiscountGovernance });

  const promoList: Array<{
    promo_id: string; promo_code: string; promo_type: string;
    valid_from: string; valid_until: string;
    current_redemptions: number; max_redemptions?: number;
    status: string; description?: string;
    created_by?: string; region_codes?: string[];
    discount_value?: number; strategy?: string;
  }> = promos.data?.data ?? [];

  const limits = governance.data?.data ?? {};
  const maxPlatformDiscount = limits.max_platform_discount_pct ?? 0;
  const maxRlaFundedDiscount = limits.max_rla_funded_discount_pct ?? 0;
  const maxTrialDays = limits.max_trial_days ?? 0;
  const maxBudgetPerPeriod = limits.max_budget_per_period ?? 0;
  const maxFixedAmount = limits.max_fixed_amount ?? 0;
  const maxBundleDiscount = limits.max_bundle_discount_pct ?? 0;

  const filtered = statusFilter
    ? promoList.filter((p) => p.status === statusFilter)
    : promoList;

  const activeCount = promoList.filter((p) => p.status === "ACTIVE").length;
  const totalRedemptions = promoList.reduce((s, p) => s + p.current_redemptions, 0);
  const exhaustedCount = promoList.filter((p) => p.status === "EXHAUSTED").length;

  const deactivateMut = useMutation({
    mutationFn: async (promoId: string) => {
      const res = await fetch("/api/saas/promos/deactivate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ promo_id: promoId }),
      });
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saas", "promos"] });
      setShowDeactivate(null);
      setToast({ message: "Promotion deactivated", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to deactivate", variant: "error" }),
  });

  const limitsMut = useMutation({
    mutationFn: setDiscountGovernance,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saas", "discount-governance"] });
      setShowEditLimits(false);
      setToast({ message: "Promotion limits updated", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to update limits", variant: "error" }),
  });

  function handleSaveLimits(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    limitsMut.mutate({
      max_platform_discount_pct: Number(d.get("max_platform_discount_pct")),
      max_rla_funded_discount_pct: Number(d.get("max_rla_funded_discount_pct")),
      max_trial_days: Number(d.get("max_trial_days")),
      max_budget_per_period: Number(d.get("max_budget_per_period")),
      max_fixed_amount: Number(d.get("max_fixed_amount")),
      max_bundle_discount_pct: Number(d.get("max_bundle_discount_pct")),
    });
  }

  return (
    <div>
      <PageHeader
        title="Promotion Governance"
        description="Set promotion limits that all Region License Agents must operate within. Monitor and enforce compliance."
        actions={
          <Button onClick={() => setShowEditLimits(true)} className="gap-2">
            <Settings className="h-4 w-4" />
            Edit Limits
          </Button>
        }
      />

      {/* Doctrine Banner */}
      <Card className="mb-6 border-amber-200/50 bg-amber-50/30 dark:border-amber-800/30 dark:bg-amber-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Eye className="mt-0.5 h-5 w-5 text-amber-600" />
            <div className="text-sm">
              <p className="font-semibold text-amber-700 dark:text-amber-400">Promotion Governance Doctrine</p>
              <ul className="mt-1 list-disc pl-4 text-neutral-600 dark:text-neutral-400 space-y-0.5">
                <li><strong>Main Administration sets limits</strong> — maximum discount caps, budget ceilings, and trial extensions</li>
                <li><strong>RLAs create promotions</strong> — using any strategy, as long as they stay within the limits</li>
                <li><strong>Excess liability falls on the RLA</strong> — any discount beyond platform-funded caps is the RLA&apos;s cost</li>
                <li><strong>Platform can deactivate</strong> — any promotion that violates policy</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Current Limits */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Active Promotion Limits</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <LimitCard
              icon={Percent}
              label="Max Platform Discount"
              value={`${maxPlatformDiscount}%`}
              sublabel="Platform-funded ceiling"
            />
            <LimitCard
              icon={Percent}
              label="Max RLA-Funded Discount"
              value={`${maxRlaFundedDiscount}%`}
              sublabel="RLA pays the difference"
            />
            <LimitCard
              icon={Calendar}
              label="Max Trial Extension"
              value={`${maxTrialDays} days`}
              sublabel="Beyond default trial"
            />
            <LimitCard
              icon={DollarSign}
              label="Max Budget / Period"
              value={maxBudgetPerPeriod > 0 ? maxBudgetPerPeriod.toLocaleString() : "No limit"}
              sublabel="Total promo spend cap"
            />
            <LimitCard
              icon={DollarSign}
              label="Max Fixed Amount"
              value={maxFixedAmount > 0 ? maxFixedAmount.toLocaleString() : "No limit"}
              sublabel="Per-redemption credit cap"
            />
            <LimitCard
              icon={Percent}
              label="Max Bundle Discount"
              value={`${maxBundleDiscount}%`}
              sublabel="Multi-service bundle cap"
            />
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active Promotions" value={activeCount} icon={Tag} />
        <StatCard title="Total Redemptions" value={totalRedemptions} icon={TrendingUp} />
        <StatCard title="Exhausted" value={exhaustedCount} icon={CheckCircle} />
        <StatCard title="Total Promos" value={promoList.length} icon={Shield} />
      </div>

      {/* Filter */}
      <div className="mb-4 flex gap-3">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="DEACTIVATED">Deactivated</option>
          <option value="EXHAUSTED">Exhausted</option>
        </Select>
      </div>

      {/* Promotions Table */}
      <Card>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <EmptyState title="No promotions found" description="Promotions will appear here when RLAs create them" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Created By</TableHead>
                  <TableHead>Regions</TableHead>
                  <TableHead>Valid Period</TableHead>
                  <TableHead className="text-center">Redemptions</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-center">Compliance</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((p) => {
                  const discountExceedsLimit = (p.discount_value ?? 0) > maxPlatformDiscount && maxPlatformDiscount > 0;
                  return (
                    <TableRow key={p.promo_id}>
                      <TableCell>
                        <code className="rounded bg-bos-purple-light px-2 py-0.5 font-mono text-sm font-bold text-bos-purple">
                          {p.promo_code}
                        </code>
                        {p.description && <p className="mt-0.5 text-xs text-bos-silver-dark">{p.description}</p>}
                      </TableCell>
                      <TableCell>
                        <Badge variant={PROMO_TYPE_BADGE[p.strategy ?? p.promo_type] ?? "outline"}>
                          {(p.strategy ?? p.promo_type).replace(/_/g, " ")}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">
                        {p.created_by || "Platform"}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {(p.region_codes ?? []).length > 0
                            ? p.region_codes!.map((r) => <Badge key={r} variant="outline" className="text-xs">{r}</Badge>)
                            : <span className="text-xs text-bos-silver-dark">All</span>
                          }
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-bos-silver-dark">
                        {formatDate(p.valid_from)} — {formatDate(p.valid_until)}
                      </TableCell>
                      <TableCell className="text-center">
                        <span className="text-sm font-medium">
                          {p.current_redemptions}/{p.max_redemptions ?? "\u221e"}
                        </span>
                      </TableCell>
                      <TableCell className="text-center"><StatusBadge status={p.status} /></TableCell>
                      <TableCell className="text-center">
                        {discountExceedsLimit ? (
                          <span className="inline-flex items-center gap-1 text-xs text-amber-600" title="Discount exceeds platform-funded limit. Excess is RLA liability.">
                            <AlertTriangle className="h-3.5 w-3.5" /> RLA Liability
                          </span>
                        ) : (
                          <span className="text-xs text-green-600">Within Limits</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {p.status === "ACTIVE" && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowDeactivate(p.promo_id)}
                            title="Deactivate promotion"
                            className="text-red-600 hover:text-red-700"
                          >
                            <Ban className="h-3.5 w-3.5" />
                          </Button>
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

      {/* Edit Limits Dialog */}
      <FormDialog
        open={showEditLimits}
        onClose={() => setShowEditLimits(false)}
        title="Set Promotion Limits"
        description="These limits apply to all RLAs. Any discount beyond the platform-funded cap becomes the RLA's liability."
        onSubmit={handleSaveLimits}
        submitLabel="Save Limits"
        loading={limitsMut.isPending}
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="max_platform_discount_pct">Max Platform Discount %</Label>
            <Input id="max_platform_discount_pct" name="max_platform_discount_pct" type="number" min={0} max={100}
              defaultValue={maxPlatformDiscount} className="mt-1" />
            <p className="text-xs text-bos-silver-dark mt-1">Platform absorbs up to this %</p>
          </div>
          <div>
            <Label htmlFor="max_rla_funded_discount_pct">Max RLA-Funded Discount %</Label>
            <Input id="max_rla_funded_discount_pct" name="max_rla_funded_discount_pct" type="number" min={0} max={100}
              defaultValue={maxRlaFundedDiscount} className="mt-1" />
            <p className="text-xs text-bos-silver-dark mt-1">RLA can add up to this % on top</p>
          </div>
          <div>
            <Label htmlFor="max_trial_days">Max Trial Extension (days)</Label>
            <Input id="max_trial_days" name="max_trial_days" type="number" min={0} max={365}
              defaultValue={maxTrialDays} className="mt-1" />
            <p className="text-xs text-bos-silver-dark mt-1">Extra days beyond default trial</p>
          </div>
          <div>
            <Label htmlFor="max_budget_per_period">Max Budget / Period</Label>
            <Input id="max_budget_per_period" name="max_budget_per_period" type="number" min={0}
              defaultValue={maxBudgetPerPeriod} className="mt-1" />
            <p className="text-xs text-bos-silver-dark mt-1">0 = no limit</p>
          </div>
          <div>
            <Label htmlFor="max_fixed_amount">Max Fixed Amount (per use)</Label>
            <Input id="max_fixed_amount" name="max_fixed_amount" type="number" min={0}
              defaultValue={maxFixedAmount} className="mt-1" />
            <p className="text-xs text-bos-silver-dark mt-1">Credit/voucher cap per redemption</p>
          </div>
          <div>
            <Label htmlFor="max_bundle_discount_pct">Max Bundle Discount %</Label>
            <Input id="max_bundle_discount_pct" name="max_bundle_discount_pct" type="number" min={0} max={100}
              defaultValue={maxBundleDiscount} className="mt-1" />
            <p className="text-xs text-bos-silver-dark mt-1">Multi-service bundle ceiling</p>
          </div>
        </div>
      </FormDialog>

      {/* Deactivate Confirm */}
      <ConfirmDialog
        open={!!showDeactivate}
        onClose={() => setShowDeactivate(null)}
        onConfirm={() => showDeactivate && deactivateMut.mutate(showDeactivate)}
        title="Deactivate Promotion"
        description="This will immediately stop this promo code from being redeemed. Existing redemptions are not affected. This action is logged."
        confirmLabel="Deactivate"
        confirmVariant="destructive"
        loading={deactivateMut.isPending}
      />

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

function LimitCard({ icon: Icon, label, value, sublabel }: { icon: React.ElementType; label: string; value: string; sublabel: string }) {
  return (
    <div className="rounded-lg border border-bos-silver/20 p-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="h-4 w-4 text-bos-purple" />
        <span className="text-xs font-medium text-bos-silver-dark">{label}</span>
      </div>
      <p className="text-lg font-bold">{value}</p>
      <p className="text-[11px] text-bos-silver-dark">{sublabel}</p>
    </div>
  );
}
