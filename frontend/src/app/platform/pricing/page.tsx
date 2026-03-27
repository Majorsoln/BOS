"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import {
  getServices, setServiceRate, toggleService,
  getCapacityPricing, setCapacityTierRate,
  getReductionRates, setReductionRate,
} from "@/lib/api/saas";
import { getAgents } from "@/lib/api/agents";
import { BOS_SERVICES, CAPACITY_DIMENSIONS, REGIONS } from "@/lib/constants";
import {
  Package, DollarSign, Power, PowerOff, CheckCircle2, Layers, Percent, Building2, FileText, Users, Cpu,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

type TabKey = "services" | "capacity" | "reductions";
type RateMap = Record<string, Record<string, { monthly_amount: number; currency: string }>>;
type TierRateMap = Record<string, Record<string, Record<string, { monthly_amount: number; currency: string }>>>;
type ReductionMap = Record<string, Record<number, number>>;

const DIMENSION_ICONS: Record<string, LucideIcon> = {
  BRANCHES: Building2, DOCUMENTS: FileText, USERS: Users, AI_TOKENS: Cpu,
};

const SERVICE_COUNTS = [
  { count: 2, label: "2 Services" },
  { count: 3, label: "3 Services" },
  { count: 4, label: "4 Services" },
  { count: 5, label: "5 Services (All)" },
];

export default function PricingPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<TabKey>("services");
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  // Fetch RLAs to know which regions are open for pricing
  const rlaQuery = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });

  const rlaList: Array<{ territory?: string; status: string }> = rlaQuery.data?.data ?? [];
  const activeRLARegions = new Set(rlaList.filter((a) => a.status === "ACTIVE").map((a) => a.territory).filter(Boolean));
  const pricingRegions = REGIONS.filter((r) => activeRLARegions.has(r.code));
  const hasNoRLAs = pricingRegions.length === 0;

  const tabs: { key: TabKey; label: string }[] = [
    { key: "services", label: "Services" },
    { key: "capacity", label: "Capacity Tiers" },
    { key: "reductions", label: "Volume Discounts" },
  ];

  return (
    <div>
      <PageHeader
        title="Services & Pricing"
        description="Configure service rates, capacity tiers, and volume discounts per region"
      />

      {/* RLA Gating Notice */}
      {hasNoRLAs && (
        <Card className="mb-6 border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-950">
          <CardContent className="flex items-start gap-3 pt-6">
            <Package className="mt-0.5 h-5 w-5 text-orange-600" />
            <div className="text-sm">
              <p className="font-semibold text-orange-700 dark:text-orange-400">No regions available for pricing</p>
              <p className="text-orange-600 dark:text-orange-300">
                Pricing can only be set for regions with an active Region License Agent.
                Go to <strong>Agents &rarr; Region License Agents</strong> to appoint an RLA first.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {!hasNoRLAs && (
        <div className="mb-4 flex flex-wrap gap-1 text-sm">
          <span className="text-bos-silver-dark">Pricing available for:</span>
          {pricingRegions.map((r) => (
            <Badge key={r.code} variant="outline">{r.code}</Badge>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-bos-silver-light p-1 dark:bg-neutral-800 w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-white text-bos-purple shadow-sm dark:bg-neutral-900"
                : "text-bos-silver-dark hover:text-neutral-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "services" && <ServicesTab pricingRegions={pricingRegions} onToast={setToast} />}
      {tab === "capacity" && <CapacityTab pricingRegions={pricingRegions} onToast={setToast} />}
      {tab === "reductions" && <ReductionsTab pricingRegions={pricingRegions} onToast={setToast} />}

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

type ToastFn = (t: { message: string; variant: "success" | "error" }) => void;
type RegionType = { code: string; name: string; currency: string };

/* ── Services Tab ──────────────────────────────────────── */

function ServicesTab({ pricingRegions, onToast }: { pricingRegions: RegionType[]; onToast: ToastFn }) {
  const qc = useQueryClient();
  const [showRate, setShowRate] = useState<string | null>(null);

  const services = useQuery({ queryKey: ["saas", "services"], queryFn: getServices });

  const rateMut = useMutation({
    mutationFn: setServiceRate,
    onSuccess: () => { setShowRate(null); qc.invalidateQueries({ queryKey: ["saas", "services"] }); onToast({ message: "Rate updated", variant: "success" }); },
    onError: () => onToast({ message: "Failed to update rate", variant: "error" }),
  });

  const toggleMut = useMutation({
    mutationFn: toggleService,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "services"] }); onToast({ message: "Service toggled", variant: "success" }); },
    onError: () => onToast({ message: "Failed to toggle", variant: "error" }),
  });

  const srvData = services.data?.data ?? {};
  const rates: RateMap = srvData.rates ?? {};
  const activeMap: Record<string, boolean> = srvData.active ?? {};

  function handleSetRate(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    const region = pricingRegions.find((r) => r.code === d.get("region_code"));
    rateMut.mutate({
      service_key: showRate!,
      region_code: d.get("region_code") as string,
      currency: region?.currency ?? "USD",
      monthly_amount: Number(d.get("monthly_amount")),
    });
  }

  return (
    <>
      <div className="space-y-4">
        {BOS_SERVICES.map((svc) => {
          const isActive = activeMap[svc.key] !== false;
          const svcRates = rates[svc.key] ?? {};

          return (
            <Card key={svc.key} className={!isActive ? "opacity-60" : ""}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-bos-purple/10">
                      <Package className="h-5 w-5 text-bos-purple" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{svc.name}</CardTitle>
                      <p className="text-xs text-bos-silver-dark">{svc.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={isActive ? "success" : "outline"}>{isActive ? "Active" : "Inactive"}</Badge>
                    <Button size="sm" variant="ghost" onClick={() => toggleMut.mutate({ service_key: svc.key, active: !isActive })} className="gap-1">
                      {isActive ? <PowerOff className="h-3 w-3" /> : <Power className="h-3 w-3" />}
                      {isActive ? "Disable" : "Enable"}
                    </Button>
                    <Button size="sm" onClick={() => setShowRate(svc.key)} className="gap-1" disabled={pricingRegions.length === 0}>
                      <DollarSign className="h-3 w-3" /> Set Rate
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="mb-3 flex flex-wrap gap-1.5">
                  {svc.engines.map((eng) => (
                    <span key={eng} className="inline-flex items-center rounded-md bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
                      {eng}
                    </span>
                  ))}
                </div>
                {pricingRegions.length > 0 && (
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        {pricingRegions.map((r) => (
                          <TableHead key={r.code} className="text-center text-xs h-8 px-2">{r.code}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow className="hover:bg-transparent">
                        {pricingRegions.map((r) => {
                          const rate = svcRates[r.code];
                          return (
                            <TableCell key={r.code} className="text-center px-2 py-2">
                              {rate ? (
                                <span className="font-mono text-xs font-semibold">{r.currency} {rate.monthly_amount.toLocaleString()}</span>
                              ) : (
                                <span className="text-xs text-neutral-300">—</span>
                              )}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <FormDialog
        open={!!showRate}
        onClose={() => setShowRate(null)}
        title={`Set Rate — ${BOS_SERVICES.find((s) => s.key === showRate)?.name ?? ""}`}
        description="Set monthly rate for a region with an active RLA."
        onSubmit={handleSetRate}
        submitLabel="Save Rate"
        loading={rateMut.isPending}
      >
        <div>
          <Label>Region</Label>
          <Select name="region_code" required>
            <option value="">Select region...</option>
            {pricingRegions.map((r) => <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>)}
          </Select>
        </div>
        <div>
          <Label>Monthly Amount (local currency)</Label>
          <Input name="monthly_amount" type="number" min={0} required />
        </div>
      </FormDialog>
    </>
  );
}

/* ── Capacity Tab ──────────────────────────────────────── */

function CapacityTab({ pricingRegions, onToast }: { pricingRegions: RegionType[]; onToast: ToastFn }) {
  const qc = useQueryClient();
  const [rateTarget, setRateTarget] = useState<{ dimension: string; tier_key: string } | null>(null);

  const pricing = useQuery({ queryKey: ["saas", "capacity"], queryFn: getCapacityPricing });

  const rateMut = useMutation({
    mutationFn: setCapacityTierRate,
    onSuccess: () => { setRateTarget(null); qc.invalidateQueries({ queryKey: ["saas", "capacity"] }); onToast({ message: "Tier rate updated", variant: "success" }); },
    onError: () => onToast({ message: "Failed to update tier rate", variant: "error" }),
  });

  const pricingData = pricing.data?.data ?? {};
  const tiers = pricingData.tiers ?? {};
  const tierRates: TierRateMap = pricingData.rates ?? {};

  function handleSetRate(e: React.FormEvent) {
    e.preventDefault();
    if (!rateTarget) return;
    const d = new FormData(e.target as HTMLFormElement);
    const region = pricingRegions.find((r) => r.code === d.get("region_code"));
    rateMut.mutate({
      dimension: rateTarget.dimension,
      tier_key: rateTarget.tier_key,
      region_code: d.get("region_code") as string,
      currency: region?.currency ?? "USD",
      monthly_amount: Number(d.get("monthly_amount")),
    });
  }

  return (
    <>
      <div className="space-y-6">
        {(CAPACITY_DIMENSIONS || []).map((dim: { key: string; name: string; tiers: Array<{ key: string; label: string; limit: string }> }) => {
          const Icon = DIMENSION_ICONS[dim.key] || Layers;
          return (
            <Card key={dim.key}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Icon className="h-5 w-5 text-bos-purple" />
                  <CardTitle className="text-base">{dim.name}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tier</TableHead>
                      <TableHead>Limit</TableHead>
                      {pricingRegions.map((r) => (
                        <TableHead key={r.code} className="text-center">{r.code}</TableHead>
                      ))}
                      <TableHead className="text-right">Set</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dim.tiers.map((tier) => {
                      const dimRates = tierRates[dim.key]?.[tier.key] ?? {};
                      return (
                        <TableRow key={tier.key}>
                          <TableCell className="font-medium">{tier.label}</TableCell>
                          <TableCell className="text-bos-silver-dark text-sm">{tier.limit}</TableCell>
                          {pricingRegions.map((r) => {
                            const rate = dimRates[r.code];
                            return (
                              <TableCell key={r.code} className="text-center font-mono text-sm">
                                {rate ? `${r.currency} ${rate.monthly_amount.toLocaleString()}` : "—"}
                              </TableCell>
                            );
                          })}
                          <TableCell className="text-right">
                            <Button size="sm" variant="ghost" onClick={() => setRateTarget({ dimension: dim.key, tier_key: tier.key })} disabled={pricingRegions.length === 0}>
                              <DollarSign className="h-3 w-3" />
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

      <FormDialog
        open={!!rateTarget}
        onClose={() => setRateTarget(null)}
        title={`Set Tier Rate — ${rateTarget?.dimension} / ${rateTarget?.tier_key}`}
        onSubmit={handleSetRate}
        submitLabel="Save"
        loading={rateMut.isPending}
      >
        <div>
          <Label>Region</Label>
          <Select name="region_code" required>
            <option value="">Select...</option>
            {pricingRegions.map((r) => <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>)}
          </Select>
        </div>
        <div>
          <Label>Monthly Amount</Label>
          <Input name="monthly_amount" type="number" min={0} required />
        </div>
      </FormDialog>
    </>
  );
}

/* ── Reductions Tab ────────────────────────────────────── */

function ReductionsTab({ pricingRegions, onToast }: { pricingRegions: RegionType[]; onToast: ToastFn }) {
  const qc = useQueryClient();
  const [showSet, setShowSet] = useState(false);

  const reductions = useQuery({ queryKey: ["saas", "reductions"], queryFn: getReductionRates });

  const setMut = useMutation({
    mutationFn: setReductionRate,
    onSuccess: () => { setShowSet(false); qc.invalidateQueries({ queryKey: ["saas", "reductions"] }); onToast({ message: "Reduction saved", variant: "success" }); },
    onError: () => onToast({ message: "Failed to save", variant: "error" }),
  });

  const data: ReductionMap = reductions.data?.data?.rates ?? {};

  function handleSet(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    setMut.mutate({
      region_code: d.get("region_code") as string,
      service_count: Number(d.get("service_count")),
      reduction_pct: Number(d.get("reduction_pct")),
    });
  }

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-bos-silver-dark">Discount percentage when a tenant subscribes to multiple services.</p>
        <Button size="sm" onClick={() => setShowSet(true)} disabled={pricingRegions.length === 0}>Set Reduction</Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Region</TableHead>
                {SERVICE_COUNTS.map((sc) => (
                  <TableHead key={sc.count} className="text-center">{sc.label}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {pricingRegions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-bos-silver-dark">
                    No regions with active RLA
                  </TableCell>
                </TableRow>
              ) : (
                pricingRegions.map((r) => (
                  <TableRow key={r.code}>
                    <TableCell>
                      <Badge variant="outline">{r.code} — {r.name}</Badge>
                    </TableCell>
                    {SERVICE_COUNTS.map((sc) => {
                      const pct = data[r.code]?.[sc.count];
                      return (
                        <TableCell key={sc.count} className="text-center font-mono">
                          {pct != null ? `${pct}%` : "—"}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <FormDialog
        open={showSet}
        onClose={() => setShowSet(false)}
        title="Set Volume Discount"
        onSubmit={handleSet}
        submitLabel="Save"
        loading={setMut.isPending}
      >
        <div>
          <Label>Region</Label>
          <Select name="region_code" required>
            <option value="">Select...</option>
            {pricingRegions.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
          </Select>
        </div>
        <div>
          <Label>Service Count</Label>
          <Select name="service_count" required>
            {SERVICE_COUNTS.map((sc) => <option key={sc.count} value={sc.count}>{sc.label}</option>)}
          </Select>
        </div>
        <div>
          <Label>Reduction %</Label>
          <Input name="reduction_pct" type="number" min={0} max={50} required placeholder="e.g. 10" />
        </div>
      </FormDialog>
    </>
  );
}
