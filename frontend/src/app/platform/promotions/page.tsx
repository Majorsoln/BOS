"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, Input, Label, Select, Textarea, Toast,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Badge,
} from "@/components/ui";
import { getPromos, createPromo, redeemPromo } from "@/lib/api/saas";
import { PROMO_TYPES, REGIONS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import { Plus, Tag, Ticket } from "lucide-react";

const PROMO_TYPE_BADGE: Record<string, "purple" | "gold" | "outline"> = {
  DISCOUNT: "purple",
  CREDIT: "gold",
  EXTENDED_TRIAL: "outline",
};

export default function PromotionsPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [showRedeem, setShowRedeem] = useState(false);
  const [promoType, setPromoType] = useState("DISCOUNT");
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const promos = useQuery({ queryKey: ["saas", "promos"], queryFn: getPromos });


  const createMut = useMutation({
    mutationFn: createPromo,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["saas", "promos"] }); setShowCreate(false); setToast({ message: "Promotion created", variant: "success" }); },
    onError: () => setToast({ message: "Failed to create promotion", variant: "error" }),
  });

  const redeemMut = useMutation({
    mutationFn: redeemPromo,
    onSuccess: () => { setShowRedeem(false); setToast({ message: "Promo redeemed", variant: "success" }); },
    onError: () => setToast({ message: "Failed to redeem promo", variant: "error" }),
  });

  const promoList = promos.data?.data ?? [];
  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    createMut.mutate({
      promo_code: d.get("promo_code") as string,
      promo_type: promoType,
      description: d.get("description") as string,
      valid_from: d.get("valid_from") as string,
      valid_until: d.get("valid_until") as string,
      max_redemptions: Number(d.get("max_redemptions")) || undefined,
      discount_pct: promoType === "DISCOUNT" ? Number(d.get("discount_pct")) : undefined,
      discount_months: promoType === "DISCOUNT" ? Number(d.get("discount_months")) : undefined,
      credit_amount: promoType === "CREDIT" ? Number(d.get("credit_amount")) : undefined,
      credit_currency: promoType === "CREDIT" ? d.get("credit_currency") as string : undefined,
      extra_trial_days: promoType === "EXTENDED_TRIAL" ? Number(d.get("extra_trial_days")) : undefined,
    });
  }

  function handleRedeem(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    redeemMut.mutate({
      promo_code: d.get("promo_code") as string,
      business_id: d.get("business_id") as string,
    });
  }

  return (
    <div>
      <PageHeader
        title="Promotions"
        description="Create and manage promotional codes"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setShowRedeem(true)} className="gap-2">
              <Ticket className="h-4 w-4" />
              Redeem Code
            </Button>
            <Button onClick={() => setShowCreate(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Create Promotion
            </Button>
          </div>
        }
      />

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Valid Period</TableHead>
              <TableHead>Redemptions</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {promoList.map((p: {
              promo_id: string; promo_code: string; promo_type: string;
              valid_from: string; valid_until: string;
              current_redemptions: number; max_redemptions?: number;
              status: string; description?: string;
            }) => (
              <TableRow key={p.promo_id}>
                <TableCell>
                  <code className="rounded bg-bos-purple-light px-2 py-0.5 font-mono text-sm font-bold text-bos-purple">
                    {p.promo_code}
                  </code>
                  {p.description && <p className="mt-0.5 text-xs text-bos-silver-dark">{p.description}</p>}
                </TableCell>
                <TableCell>
                  <Badge variant={PROMO_TYPE_BADGE[p.promo_type] ?? "outline"}>{p.promo_type}</Badge>
                </TableCell>
                <TableCell className="text-xs text-bos-silver-dark">
                  {formatDate(p.valid_from)} — {formatDate(p.valid_until)}
                </TableCell>
                <TableCell>
                  <span className="text-sm font-medium">
                    {p.current_redemptions}/{p.max_redemptions ?? "∞"}
                  </span>
                </TableCell>
                <TableCell><StatusBadge status={p.status} /></TableCell>
              </TableRow>
            ))}
            {promoList.length === 0 && !promos.isLoading && (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-bos-silver-dark">
                  No promotions created yet
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Create Promotion Dialog */}
      <FormDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Create Promotion"
        onSubmit={handleCreate}
        submitLabel="Create"
        loading={createMut.isPending}
        wide
      >
        {/* Type Selection */}
        <div>
          <Label>Promotion Type</Label>
          <div className="mt-1 grid grid-cols-2 gap-2 lg:grid-cols-3">
            {PROMO_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setPromoType(t.value)}
                className={`rounded-lg border p-3 text-left text-sm transition-colors ${
                  promoType === t.value
                    ? "border-bos-purple bg-bos-purple-light text-bos-purple"
                    : "border-bos-silver/30 hover:border-bos-purple/50"
                }`}
              >
                <p className="font-medium">{t.label}</p>
                <p className="text-xs text-bos-silver-dark">{t.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Common Fields */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="promo_code">Promo Code</Label>
            <Input id="promo_code" name="promo_code" placeholder="e.g. WELCOME50" required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="max_redemptions">Max Redemptions</Label>
            <Input id="max_redemptions" name="max_redemptions" type="number" placeholder="e.g. 100" className="mt-1" />
          </div>
        </div>
        <div>
          <Label htmlFor="description">Description</Label>
          <Textarea id="description" name="description" placeholder="Short description..." className="mt-1" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="valid_from">Valid From</Label>
            <Input id="valid_from" name="valid_from" type="date" required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="valid_until">Valid Until</Label>
            <Input id="valid_until" name="valid_until" type="date" required className="mt-1" />
          </div>
        </div>

        {/* Type-specific Fields */}
        {promoType === "DISCOUNT" && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="discount_pct">Discount %</Label>
              <Input id="discount_pct" name="discount_pct" type="number" min="1" max="100" placeholder="e.g. 20" required className="mt-1" />
            </div>
            <div>
              <Label htmlFor="discount_months">For How Many Months</Label>
              <Input id="discount_months" name="discount_months" type="number" placeholder="e.g. 3" required className="mt-1" />
            </div>
          </div>
        )}

        {promoType === "CREDIT" && (
          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label htmlFor="credit_amount">Credit Amount</Label>
              <Input id="credit_amount" name="credit_amount" type="number" placeholder="e.g. 5000" required className="mt-1" />
            </div>
            <div>
              <Label htmlFor="credit_currency">Currency</Label>
              <Select id="credit_currency" name="credit_currency" className="mt-1">
                {REGIONS.map((r) => (
                  <option key={r.currency} value={r.currency}>{r.currency}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="credit_expires_months">Expires (months)</Label>
              <Input id="credit_expires_months" name="credit_expires_months" type="number" placeholder="e.g. 6" className="mt-1" />
            </div>
          </div>
        )}

        {promoType === "EXTENDED_TRIAL" && (
          <div>
            <Label htmlFor="extra_trial_days">Extra Trial Days</Label>
            <Input id="extra_trial_days" name="extra_trial_days" type="number" placeholder="e.g. 30" required className="mt-1" />
          </div>
        )}

      </FormDialog>

      {/* Redeem Dialog */}
      <FormDialog
        open={showRedeem}
        onClose={() => setShowRedeem(false)}
        title="Redeem Promo Code"
        description="Apply a promo code to a business"
        onSubmit={handleRedeem}
        submitLabel="Redeem"
        loading={redeemMut.isPending}
      >
        <div>
          <Label htmlFor="redeem_code">Promo Code</Label>
          <Input id="redeem_code" name="promo_code" placeholder="e.g. WELCOME50" required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="redeem_biz">Business ID</Label>
          <Input id="redeem_biz" name="business_id" required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="redeem_region">Region (optional)</Label>
          <Select id="redeem_region" name="region_code" className="mt-1">
            <option value="">Any region</option>
            {REGIONS.map((r) => (
              <option key={r.code} value={r.code}>{r.name}</option>
            ))}
          </Select>
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
