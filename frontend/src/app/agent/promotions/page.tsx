"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Toast, Badge,
} from "@/components/ui";
import { getMyPromotions, createMyPromotion, requestCostShare } from "@/lib/api/agents";
import { Megaphone, Plus, HandCoins } from "lucide-react";

export default function AgentPromotionsPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [showCostShare, setShowCostShare] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const promos = useQuery({ queryKey: ["agent", "promotions"], queryFn: getMyPromotions });

  const createMut = useMutation({
    mutationFn: createMyPromotion,
    onSuccess: () => { setShowCreate(false); qc.invalidateQueries({ queryKey: ["agent", "promotions"] }); setToast({ message: "Promotion created", variant: "success" }); },
    onError: () => setToast({ message: "Failed to create promotion", variant: "error" }),
  });

  const costShareMut = useMutation({
    mutationFn: requestCostShare,
    onSuccess: () => { setShowCostShare(false); setToast({ message: "Cost-share request submitted", variant: "success" }); },
    onError: () => setToast({ message: "Failed to submit request", variant: "error" }),
  });

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    createMut.mutate({
      promo_code: d.get("promo_code") as string,
      discount_pct: Number(d.get("discount_pct")),
      max_uses: Number(d.get("max_uses")),
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
        title="My Promotions"
        description="Create promotions for your tenants and request cost-sharing"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setShowCostShare(true)} className="gap-2">
              <HandCoins className="h-4 w-4" />
              Request Cost-Share
            </Button>
            <Button onClick={() => setShowCreate(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              New Promotion
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Megaphone className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Active Promotions</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Code</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Discount</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Uses</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Valid Until</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Status</th>
                </tr>
              </thead>
              <tbody>
                {promoList.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-bos-silver-dark">
                    <Megaphone className="mx-auto mb-2 h-5 w-5" />
                    No promotions yet. Create one to attract new tenants.
                  </td></tr>
                )}
                {promoList.map((p: {
                  id: string; promo_code: string; discount_pct: number;
                  used_count: number; max_uses: number; valid_until: string;
                  description?: string; status: string;
                }) => (
                  <tr key={p.id} className="border-b border-bos-silver/10 hover:bg-bos-silver-light/50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-3 font-mono font-bold">{p.promo_code}</td>
                    <td className="px-4 py-3 text-right font-mono text-bos-purple">{p.discount_pct}%</td>
                    <td className="px-4 py-3 text-right">
                      <Badge variant="outline">{p.used_count ?? 0}/{p.max_uses}</Badge>
                    </td>
                    <td className="px-4 py-3 text-bos-silver-dark">{p.valid_until}</td>
                    <td className="px-4 py-3 text-bos-silver-dark">{p.description ?? "—"}</td>
                    <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Create Promotion Dialog */}
      <FormDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Create Promotion"
        description="Create a promo code to offer discounts to tenants during onboarding."
        onSubmit={handleCreate}
        submitLabel="Create"
        loading={createMut.isPending}
      >
        <div>
          <Label htmlFor="promo_code">Promo Code</Label>
          <Input id="promo_code" name="promo_code" required className="mt-1" placeholder="e.g. DUKA2026" />
        </div>
        <div>
          <Label htmlFor="discount_pct">Discount %</Label>
          <Input id="discount_pct" name="discount_pct" type="number" min={1} max={50} required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="max_uses">Max Uses</Label>
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
        description="Request platform co-funding for a marketing or promotional activity."
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
