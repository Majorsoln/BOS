"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Card, CardContent, CardHeader, CardTitle, Toast, Badge, Button,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Select,
} from "@/components/ui";
import { getPromos } from "@/lib/api/saas";
import { formatDate } from "@/lib/utils";
import {
  Tag, Eye, Shield, TrendingUp, AlertTriangle, Ban, CheckCircle,
} from "lucide-react";

const PROMO_TYPE_BADGE: Record<string, "purple" | "gold" | "outline"> = {
  DISCOUNT: "purple",
  CREDIT: "gold",
  EXTENDED_TRIAL: "outline",
  ENGINE_BONUS: "outline",
  BUNDLE_DISCOUNT: "purple",
};

export default function PromotionsOversightPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [showDeactivate, setShowDeactivate] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const promos = useQuery({ queryKey: ["saas", "promos"], queryFn: getPromos });
  const promoList: Array<{
    promo_id: string; promo_code: string; promo_type: string;
    valid_from: string; valid_until: string;
    current_redemptions: number; max_redemptions?: number;
    status: string; description?: string;
    created_by?: string; region_codes?: string[];
  }> = promos.data?.data ?? [];

  const filtered = statusFilter
    ? promoList.filter((p) => p.status === statusFilter)
    : promoList;

  const activeCount = promoList.filter((p) => p.status === "ACTIVE").length;
  const totalRedemptions = promoList.reduce((s, p) => s + p.current_redemptions, 0);
  const exhaustedCount = promoList.filter((p) => p.status === "EXHAUSTED").length;

  // Deactivate promo — calls backend
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

  return (
    <div>
      <PageHeader
        title="Promotions — Oversight"
        description="Monitor all promotions created by agents. Platform can deactivate but does not create promotions."
      />

      {/* Doctrine banner */}
      <Card className="mb-6 border-amber-200/50 bg-amber-50/30 dark:border-amber-800/30 dark:bg-amber-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Eye className="mt-0.5 h-5 w-5 text-amber-600" />
            <div className="text-sm">
              <p className="font-semibold text-amber-700 dark:text-amber-400">Oversight Doctrine</p>
              <ul className="mt-1 list-disc pl-4 text-neutral-600 dark:text-neutral-400 space-y-0.5">
                <li><strong>Agents create promotions</strong> within platform-set discount limits</li>
                <li><strong>Platform monitors</strong> all promo activity and redemption rates</li>
                <li><strong>Platform can deactivate</strong> any promotion that violates policy</li>
                <li><strong>Platform does NOT create promotions</strong> — agents own their sales strategy</li>
              </ul>
            </div>
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

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <EmptyState title="No promotions found" description="Promotions will appear here when agents create them" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Created By</TableHead>
                  <TableHead>Regions</TableHead>
                  <TableHead>Valid Period</TableHead>
                  <TableHead className="text-center">Redemptions</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((p) => (
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
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

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
