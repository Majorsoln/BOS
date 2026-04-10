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
  getServices, toggleService,
  getCapacityPricing,
  getReductionRates, setReductionRate,
} from "@/lib/api/saas";
import { getAgents, getPricingGovernance, setPricingGovernance } from "@/lib/api/agents";
import { BOS_SERVICES, CAPACITY_DIMENSIONS } from "@/lib/constants";
import { useRegions } from "@/hooks/use-regions";
import {
  Package, DollarSign, Power, PowerOff, Layers, Percent, Building2, FileText, Users, Cpu, Shield, Eye, ArrowUpDown,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

type TabKey = "governance" | "services" | "capacity" | "reductions";

const DIMENSION_ICONS: Record<string, LucideIcon> = {
  BRANCHES: Building2, DOCUMENTS: FileText, USERS: Users, AI_TOKENS: Cpu,
};

const SERVICE_COUNTS = [
  { count: 2, label: "2 Services" },
  { count: 3, label: "3 Services" },
  { count: 4, label: "4 Services" },
  { count: 5, label: "5 Services (All)" },
];

type RateMap = Record<string, Record<string, { monthly_amount: number; currency: string }>>;
type TierRateMap = Record<string, Record<string, Record<string, { monthly_amount: number; currency: string }>>>;
type ReductionMap = Record<string, Record<number, number>>;

export default function PricingPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<TabKey>("governance");
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const rlaQuery = useQuery({
    queryKey: ["saas", "agents", "REGION_LICENSE_AGENT"],
    queryFn: () => getAgents({ type: "REGION_LICENSE_AGENT" }),
  });

  const { regions: allRegions } = useRegions();
  const rlaList: Array<{ territory?: string; status: string }> = rlaQuery.data?.data ?? [];
  const activeRLARegions = new Set(rlaList.filter((a) => a.status === "ACTIVE").map((a) => a.territory).filter(Boolean));
  const pricingRegions = allRegions.filter((r) => activeRLARegions.has(r.code));
  const hasNoRLAs = pricingRegions.length === 0;

  const tabs: { key: TabKey; label: string }[] = [
    { key: "governance", label: "Price Ranges" },
    { key: "services", label: "Service Controls" },
    { key: "capacity", label: "Capacity Tiers" },
    { key: "reductions", label: "Volume Discounts" },
  ];

  return (
    <div>
      <PageHeader
        title="Pricing Governance"
        description="Set allowable price ranges that RLAs must operate within. RLAs set their own prices."
      />

      {/* Doctrine Banner */}
      <Card className="mb-6 border-amber-200/50 bg-amber-50/30 dark:border-amber-800/30 dark:bg-amber-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Eye className="mt-0.5 h-5 w-5 text-amber-600" />
            <div className="text-sm">
              <p className="font-semibold text-amber-700 dark:text-amber-400">Pricing Governance Doctrine</p>
              <ul className="mt-1 list-disc pl-4 text-neutral-600 dark:text-neutral-400 space-y-0.5">
                <li><strong>Main Administration sets price ranges</strong> — minimum and maximum per service per region</li>
                <li><strong>RLAs set actual prices</strong> — they choose their price within the allowed range</li>
                <li><strong>RLAs cannot price below minimum</strong> — protects platform revenue and brand value</li>
                <li><strong>RLAs cannot price above maximum</strong> — protects market competitiveness</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* RLA Gating */}
      {hasNoRLAs && (
        <Card className="mb-6 border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-950">
          <CardContent className="flex items-start gap-3 pt-6">
            <Package className="mt-0.5 h-5 w-5 text-orange-600" />
            <div className="text-sm">
              <p className="font-semibold text-orange-700 dark:text-orange-400">No regions available</p>
              <p className="text-orange-600 dark:text-orange-300">
                Pricing ranges can only be set for regions with an active Region License Agent.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {!hasNoRLAs && (
        <div className="mb-4 flex flex-wrap gap-1 text-sm">
          <span className="text-bos-silver-dark">Active regions:</span>
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

      {tab === "governance" && <GovernanceTab pricingRegions={pricingRegions} onToast={setToast} />}
      {tab === "services" && <ServicesTab pricingRegions={pricingRegions} onToast={setToast} />}
      {tab === "capacity" && <CapacityTab pricingRegions={pricingRegions} onToast={setToast} />}
      {tab === "reductions" && <ReductionsTab pricingRegions={pricingRegions} onToast={setToast} />}

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

type ToastFn = (t: { message: string; variant: "success" | "error" }) => void;
type RegionType = { code: string; name: string; currency: string };

/* ── Price Ranges (Governance) Tab ─────────────────────── */

function GovernanceTab({ pricingRegions, onToast }: { pricingRegions: RegionType[]; onToast: ToastFn }) {
  const qc = useQueryClient();
  const [showSetRange, setShowSetRange] = useState<string | null>(null);

  const governance = useQuery({ queryKey: ["saas", "pricing-governance"], queryFn: getPricingGovernance });

  const setRangeMut = useMutation({
    mutationFn: setPricingGovernance,
    onSuccess: () => {
      setShowSetRange(null);
      qc.invalidateQueries({ queryKey: ["saas", "pricing-governance"] });
      onToast({ message: "Price range updated", variant: "success" });
    },
    onError: () => onToast({ message: "Failed to update range", variant: "error" }),
  });

  const ranges: Record<string, Record<string, { min_amount: number; max_amount: number; currency: string }>> = governance.data?.data?.ranges ?? {};

  function handleSetRange(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    const region = pricingRegions.find((r) => r.code === d.get("region_code"));
    setRangeMut.mutate({
      service_key: showSetRange!,
      region_code: d.get("region_code") as string,
      currency: region?.currency ?? "USD",
      min_amount: Number(d.get("min_amount")),
      max_amount: Number(d.get("max_amount")),
    });
  }

  return (
    <>
      <div className="space-y-4">
        {BOS_SERVICES.map((svc) => {
          const svcRanges = ranges[svc.key] ?? {};
          return (
            <Card key={svc.key}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-bos-purple/10">
                      <ArrowUpDown className="h-5 w-5 text-bos-purple" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{svc.name}</CardTitle>
                      <p className="text-xs text-bos-silver-dark">{svc.description}</p>
                    </div>
                  </div>
                  <Button size="sm" onClick={() => setShowSetRange(svc.key)} className="gap-1" disabled={pricingRegions.length === 0}>
                    <Shield className="h-3 w-3" /> Set Range
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                {pricingRegions.length > 0 && (
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead className="text-xs h-8 px-2">Region</TableHead>
                        <TableHead className="text-center text-xs h-8 px-2">Minimum</TableHead>
                        <TableHead className="text-center text-xs h-8 px-2">Maximum</TableHead>
                        <TableHead className="text-center text-xs h-8 px-2">Spread</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {pricingRegions.map((r) => {
                        const range = svcRanges[r.code];
                        const spread = range ? range.max_amount - range.min_amount : 0;
                        return (
                          <TableRow key={r.code} className="hover:bg-transparent">
                            <TableCell className="px-2 py-2">
                              <Badge variant="outline">{r.code}</Badge>
                            </TableCell>
                            <TableCell className="text-center px-2 py-2">
                              {range ? (
                                <span className="font-mono text-xs font-semibold text-green-700">{r.currency} {range.min_amount.toLocaleString()}</span>
                              ) : (
                                <span className="text-xs text-neutral-300">Not set</span>
                              )}
                            </TableCell>
                            <TableCell className="text-center px-2 py-2">
                              {range ? (
                                <span className="font-mono text-xs font-semibold text-red-700">{r.currency} {range.max_amount.toLocaleString()}</span>
                              ) : (
                                <span className="text-xs text-neutral-300">Not set</span>
                              )}
                            </TableCell>
                            <TableCell className="text-center px-2 py-2">
                              {range ? (
                                <span className="font-mono text-xs text-bos-silver-dark">{r.currency} {spread.toLocaleString()}</span>
                              ) : (
                                <span className="text-xs text-neutral-300">—</span>
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
          );
        })}
      </div>

      <FormDialog
        open={!!showSetRange}
        onClose={() => setShowSetRange(null)}
        title={`Set Price Range — ${BOS_SERVICES.find((s) => s.key === showSetRange)?.name ?? ""}`}
        description="Set the minimum and maximum monthly price that RLAs in this region can charge."
        onSubmit={handleSetRange}
        submitLabel="Save Range"
        loading={setRangeMut.isPending}
      >
        <div>
          <Label>Region</Label>
          <Select name="region_code" required>
            <option value="">Select region...</option>
            {pricingRegions.map((r) => <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>)}
          </Select>
        </div>
        <div>
          <Label>Minimum Monthly Amount</Label>
          <Input name="min_amount" type="number" min={0} required />
          <p className="text-xs text-bos-silver-dark mt-1">Floor price — RLA cannot go below this</p>
        </div>
        <div>
          <Label>Maximum Monthly Amount</Label>
          <Input name="max_amount" type="number" min={0} required />
          <p className="text-xs text-bos-silver-dark mt-1">Ceiling price — RLA cannot exceed this</p>
        </div>
      </FormDialog>
    </>
  );
}

/* ── Services Tab (enable/disable only) ───────────────── */

function ServicesTab({ pricingRegions, onToast }: { pricingRegions: RegionType[]; onToast: ToastFn }) {
  const qc = useQueryClient();

  const services = useQuery({ queryKey: ["saas", "services"], queryFn: getServices });

  const toggleMut = useMutation({
    mutationFn: toggleService,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "services"] }); onToast({ message: "Service toggled", variant: "success" }); },
    onError: () => onToast({ message: "Failed to toggle", variant: "error" }),
  });

  const srvData = services.data?.data ?? {};
  const activeMap: Record<string, boolean> = srvData.active ?? {};

  return (
    <div className="space-y-4">
      <p className="text-sm text-bos-silver-dark mb-2">Enable or disable services available on the platform. RLAs set prices for active services.</p>
      {BOS_SERVICES.map((svc) => {
        const isActive = activeMap[svc.key] !== false;
        return (
          <Card key={svc.key} className={!isActive ? "opacity-60" : ""}>
            <CardContent className="flex items-center justify-between py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-bos-purple/10">
                  <Package className="h-5 w-5 text-bos-purple" />
                </div>
                <div>
                  <p className="font-semibold text-sm">{svc.name}</p>
                  <p className="text-xs text-bos-silver-dark">{svc.description}</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {svc.engines.map((eng) => (
                      <span key={eng} className="inline-flex items-center rounded-md bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
                        {eng}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={isActive ? "success" : "outline"}>{isActive ? "Active" : "Inactive"}</Badge>
                <Button size="sm" variant="ghost" onClick={() => toggleMut.mutate({ service_key: svc.key, active: !isActive })} className="gap-1">
                  {isActive ? <PowerOff className="h-3 w-3" /> : <Power className="h-3 w-3" />}
                  {isActive ? "Disable" : "Enable"}
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

/* ── Capacity Tab ──────────────────────────────────────── */

function CapacityTab({ pricingRegions, onToast }: { pricingRegions: RegionType[]; onToast: ToastFn }) {
  const pricing = useQuery({ queryKey: ["saas", "capacity"], queryFn: getCapacityPricing });

  const pricingData = pricing.data?.data ?? {};
  const tierRates: TierRateMap = pricingData.rates ?? {};

  return (
    <div className="space-y-6">
      <p className="text-sm text-bos-silver-dark">Capacity tier pricing is set by platform and applied uniformly. RLAs do not modify capacity prices.</p>
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
