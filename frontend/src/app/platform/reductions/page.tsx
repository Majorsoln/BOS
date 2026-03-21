"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getReductionRates, setReductionRate } from "@/lib/api/saas";
import { REGIONS } from "@/lib/constants";
import { Percent, ArrowDown, Calculator, Globe } from "lucide-react";

const SERVICE_COUNTS = [
  { count: 2, label: "2 Services" },
  { count: 3, label: "3 Services" },
  { count: 4, label: "4 Services" },
  { count: 5, label: "5 Services (All)" },
];

type ReductionMap = Record<string, Record<number, number>>;

export default function ReductionsPage() {
  const qc = useQueryClient();
  const [showSet, setShowSet] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const reductions = useQuery({ queryKey: ["saas", "reductions"], queryFn: getReductionRates });

  const setMut = useMutation({
    mutationFn: setReductionRate,
    onSuccess: () => { setShowSet(false); qc.invalidateQueries({ queryKey: ["saas", "reductions"] }); setToast({ message: "Reduction rate saved", variant: "success" }); },
    onError: () => setToast({ message: "Failed to save rate", variant: "error" }),
  });

  function handleSet(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    setMut.mutate({
      region_code: d.get("region_code") as string,
      service_count: Number(d.get("service_count")),
      reduction_pct: Number(d.get("reduction_pct")),
    });
  }

  const rateMap: ReductionMap = reductions.data?.data ?? {};

  // Stats
  const configuredCount = Object.values(rateMap).reduce(
    (s, r) => s + Object.keys(r).length,
    0,
  );
  const regionsConfigured = Object.keys(rateMap).length;

  return (
    <div>
      <PageHeader
        title="Multi-Service Reduction Rates"
        description="Set reduction rates when tenants subscribe to multiple services"
        actions={
          <Button onClick={() => setShowSet(true)} className="gap-2">
            <Percent className="h-4 w-4" />
            Set Rate
          </Button>
        }
      />

      {/* Summary Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bos-purple/10">
              <Percent className="h-5 w-5 text-bos-purple" />
            </div>
            <div>
              <p className="text-2xl font-bold">{configuredCount}</p>
              <p className="text-xs text-bos-silver-dark">Rates Configured</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-green-100 dark:bg-green-900/30">
              <Globe className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{regionsConfigured}</p>
              <p className="text-xs text-bos-silver-dark">Regions Set</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bos-gold-light">
              <ArrowDown className="h-5 w-5 text-bos-gold-dark" />
            </div>
            <div>
              <p className="text-2xl font-bold">{SERVICE_COUNTS.length}</p>
              <p className="text-xs text-bos-silver-dark">Service Tiers (2–5)</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Info Banner */}
      <div className="mb-6 rounded-lg border border-bos-purple/20 bg-bos-purple/5 p-4">
        <h3 className="mb-1 text-sm font-semibold text-bos-purple">How Reduction Works</h3>
        <p className="text-xs text-bos-silver-dark">
          This is <strong>not a discount</strong> — it is a reducible rate applied to the service total
          when a tenant subscribes to more than one service. The reduction applies only to the
          service layer, not to capacity charges. Set rates per region.
        </p>
        <div className="mt-3 rounded-md bg-white p-3 text-xs dark:bg-neutral-900">
          <p className="font-mono text-bos-purple">
            monthly_total = (service_total - service_total x reduction_rate) + capacity_total
          </p>
        </div>
      </div>

      {/* Reduction Table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <ArrowDown className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Reduction Rates by Region</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-bos-silver-light/50 dark:bg-neutral-900 hover:bg-bos-silver-light/50">
                <TableHead className="h-10">Region</TableHead>
                <TableHead className="h-10 w-20">Currency</TableHead>
                {SERVICE_COUNTS.map((sc) => (
                  <TableHead key={sc.count} className="text-center h-10">
                    {sc.label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {REGIONS.map((r) => {
                const regionRates = rateMap[r.code] ?? {};
                return (
                  <TableRow key={r.code}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center justify-center rounded-md bg-bos-purple/10 px-1.5 py-0.5 text-[10px] font-bold text-bos-purple">
                          {r.code}
                        </span>
                        {r.name}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{r.currency}</Badge>
                    </TableCell>
                    {SERVICE_COUNTS.map((sc) => {
                      const rate = regionRates[sc.count];
                      return (
                        <TableCell key={sc.count} className="text-center">
                          {rate !== undefined ? (
                            <span className="inline-flex items-center rounded-lg bg-bos-purple/10 px-3 py-1 font-mono text-sm font-bold text-bos-purple">
                              {rate}%
                            </span>
                          ) : (
                            <span className="text-xs text-neutral-300 dark:text-neutral-600">—</span>
                          )}
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

      {/* Example Calculator */}
      <Card className="mt-4">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Calculator className="h-5 w-5 text-bos-gold-dark" />
            <CardTitle className="text-base">Example Calculation</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg bg-bos-silver-light p-4 text-sm dark:bg-neutral-900">
            <p className="font-semibold">Kenya — Tenant picks BOS Retail + BOS HR (2 services, 10% reduction):</p>
            <div className="mt-3 space-y-1.5 font-mono text-xs">
              <div className="flex justify-between max-w-xs">
                <span>BOS Retail</span>
                <span>KES 3,000</span>
              </div>
              <div className="flex justify-between max-w-xs">
                <span>BOS HR</span>
                <span>KES 2,500</span>
              </div>
              <div className="flex justify-between max-w-xs border-t border-bos-silver/40 pt-1.5">
                <span>Service Total</span>
                <span>KES 5,500</span>
              </div>
              <div className="flex justify-between max-w-xs text-bos-purple font-semibold">
                <span>Reduction (10%)</span>
                <span>- KES 550</span>
              </div>
              <div className="flex justify-between max-w-xs border-t border-bos-silver/40 pt-1.5 font-bold">
                <span>Service After Reduction</span>
                <span>KES 4,950</span>
              </div>
              <div className="flex justify-between max-w-xs text-bos-silver-dark">
                <span>+ Capacity charges...</span>
                <span></span>
              </div>
              <div className="flex justify-between max-w-xs font-bold text-base pt-1">
                <span>= Monthly Total</span>
                <span></span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <FormDialog
        open={showSet}
        onClose={() => setShowSet(false)}
        title="Set Reduction Rate"
        description="Set the reduction percentage for a specific service count in a region."
        onSubmit={handleSet}
        submitLabel="Save"
        loading={setMut.isPending}
      >
        <div>
          <Label htmlFor="rd_region">Region</Label>
          <Select id="rd_region" name="region_code" required className="mt-1">
            <option value="">Select region...</option>
            {REGIONS.map((r) => <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="rd_count">Service Count</Label>
          <Select id="rd_count" name="service_count" required className="mt-1">
            {SERVICE_COUNTS.map((sc) => <option key={sc.count} value={sc.count}>{sc.label}</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="rd_pct">Reduction %</Label>
          <Input id="rd_pct" name="reduction_pct" type="number" min={0} max={50} required className="mt-1" placeholder="e.g. 10" />
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
