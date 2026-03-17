"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast,
} from "@/components/ui";
import { getReductionRates, setReductionRate } from "@/lib/api/saas";
import { REGIONS } from "@/lib/constants";
import { Percent, ArrowDown } from "lucide-react";

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

  // { KE: { 2: 10, 3: 15, 4: 20, 5: 25 }, TZ: {...} }
  const rateMap: ReductionMap = reductions.data?.data ?? {};

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

      <div className="mb-6 rounded-lg border border-bos-purple/20 bg-bos-purple/5 p-4">
        <h3 className="mb-1 text-sm font-semibold text-bos-purple">How Reduction Works</h3>
        <p className="text-xs text-bos-silver-dark">
          This is <strong>not a discount</strong> — it is a reducible rate applied to the service total
          when a tenant subscribes to more than one service. The reduction applies only to the
          service layer, not to capacity charges. Set rates per region.
        </p>
        <div className="mt-3 rounded-md bg-white p-3 text-xs dark:bg-neutral-900">
          <p className="font-mono">
            monthly_total = (service_total − service_total × reduction_rate) + capacity_total
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ArrowDown className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Reduction Rates by Region</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Region</th>
                  {SERVICE_COUNTS.map((sc) => (
                    <th key={sc.count} className="px-4 py-3 text-center text-xs font-semibold uppercase text-bos-silver-dark">
                      {sc.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {REGIONS.map((r) => {
                  const regionRates = rateMap[r.code] ?? {};
                  return (
                    <tr key={r.code} className="border-b border-bos-silver/10 hover:bg-bos-silver-light/50 dark:hover:bg-neutral-900/50">
                      <td className="px-4 py-3">
                        <div>
                          <span className="font-medium">{r.name}</span>
                          <span className="ml-1 text-xs text-bos-silver-dark">({r.code})</span>
                        </div>
                      </td>
                      {SERVICE_COUNTS.map((sc) => {
                        const rate = regionRates[sc.count];
                        return (
                          <td key={sc.count} className="px-4 py-3 text-center">
                            {rate !== undefined ? (
                              <span className="rounded-md bg-bos-purple/10 px-2 py-1 font-mono text-sm font-bold text-bos-purple">
                                {rate}%
                              </span>
                            ) : (
                              <span className="text-bos-silver">Not set</span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Example Calculator */}
      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">Example Calculation</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg bg-bos-silver-light p-4 text-sm dark:bg-neutral-900">
            <p className="font-semibold">Kenya — Tenant picks BOS Retail + BOS HR (2 services, 10% reduction):</p>
            <div className="mt-2 space-y-1 font-mono text-xs">
              <p>BOS Retail:            KES 3,000</p>
              <p>BOS HR:                KES 2,500</p>
              <p>Service Total:         KES 5,500</p>
              <p className="text-bos-purple">Reduction (10%):     − KES   550</p>
              <p className="font-bold">Service After Reduction: KES 4,950</p>
              <p>+ Capacity (branches, docs, users, AI)...</p>
              <p className="font-bold">= Monthly Total</p>
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
