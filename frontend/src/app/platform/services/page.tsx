"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getServices, setServiceRate, toggleService } from "@/lib/api/saas";
import { BOS_SERVICES, REGIONS } from "@/lib/constants";
import { Package, DollarSign, Power, PowerOff, CheckCircle2, XCircle } from "lucide-react";

type RateMap = Record<string, Record<string, { monthly_amount: number; currency: string }>>;

export default function ServicesPage() {
  const qc = useQueryClient();
  const [showRate, setShowRate] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const services = useQuery({ queryKey: ["saas", "services"], queryFn: getServices });

  const rateMut = useMutation({
    mutationFn: setServiceRate,
    onSuccess: () => { setShowRate(null); qc.invalidateQueries({ queryKey: ["saas", "services"] }); setToast({ message: "Rate updated", variant: "success" }); },
    onError: () => setToast({ message: "Failed to update rate", variant: "error" }),
  });

  const toggleMut = useMutation({
    mutationFn: toggleService,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "services"] }); setToast({ message: "Service toggled", variant: "success" }); },
    onError: () => setToast({ message: "Failed to toggle service", variant: "error" }),
  });

  function handleSetRate(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    const region = REGIONS.find((r) => r.code === d.get("region_code"));
    rateMut.mutate({
      service_key: showRate!,
      region_code: d.get("region_code") as string,
      currency: region?.currency ?? "USD",
      monthly_amount: Number(d.get("monthly_amount")),
    });
  }

  const srvData = services.data?.data ?? {};
  const rates: RateMap = srvData.rates ?? {};
  const activeMap: Record<string, boolean> = srvData.active ?? {};

  const activeCount = BOS_SERVICES.filter((s) => activeMap[s.key] !== false).length;
  const totalRates = Object.values(rates).reduce((sum, r) => sum + Object.keys(r).length, 0);

  return (
    <div>
      <PageHeader
        title="Service Management"
        description="Set pricing for each BOS service per region. Tenants choose which services they need."
      />

      {/* Summary Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bos-purple/10">
              <Package className="h-5 w-5 text-bos-purple" />
            </div>
            <div>
              <p className="text-2xl font-bold">{BOS_SERVICES.length}</p>
              <p className="text-xs text-bos-silver-dark">Total Services</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-green-100 dark:bg-green-900/30">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{activeCount}</p>
              <p className="text-xs text-bos-silver-dark">Active Services</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bos-gold-light">
              <DollarSign className="h-5 w-5 text-bos-gold-dark" />
            </div>
            <div>
              <p className="text-2xl font-bold">{totalRates}</p>
              <p className="text-xs text-bos-silver-dark">Rates Configured</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Info Banner */}
      <div className="mb-6 rounded-lg border border-bos-purple/20 bg-bos-purple/5 p-4">
        <h3 className="mb-1 text-sm font-semibold text-bos-purple">How Services Work</h3>
        <p className="text-xs text-bos-silver-dark">
          Each service gives the tenant <strong>full features</strong> for that business vertical.
          Free engines (cash, documents, reporting, customer) are included with every service automatically.
          Tenants can pick multiple services — a reduction rate applies for multi-service plans.
        </p>
      </div>

      {/* Service Cards with Rate Table */}
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
                    <Badge variant={isActive ? "success" : "outline"}>
                      {isActive ? "Active" : "Inactive"}
                    </Badge>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => toggleMut.mutate({ service_key: svc.key, active: !isActive })}
                      className="gap-1"
                    >
                      {isActive ? <PowerOff className="h-3 w-3" /> : <Power className="h-3 w-3" />}
                      {isActive ? "Disable" : "Enable"}
                    </Button>
                    <Button size="sm" onClick={() => setShowRate(svc.key)} className="gap-1">
                      <DollarSign className="h-3 w-3" />
                      Set Rate
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                {/* Engines included */}
                <div className="mb-3 flex flex-wrap gap-1.5">
                  {svc.engines.map((eng) => (
                    <span
                      key={eng}
                      className="inline-flex items-center rounded-md bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
                    >
                      {eng}
                    </span>
                  ))}
                </div>
                {/* Regional Rates Table */}
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      {REGIONS.map((r) => (
                        <TableHead key={r.code} className="text-center text-xs h-8 px-2">
                          {r.code}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow className="hover:bg-transparent">
                      {REGIONS.map((r) => {
                        const rate = svcRates[r.code];
                        return (
                          <TableCell key={r.code} className="text-center px-2 py-2">
                            {rate ? (
                              <span className="font-mono text-xs font-semibold">
                                {r.currency} {rate.monthly_amount.toLocaleString()}
                              </span>
                            ) : (
                              <span className="text-xs text-neutral-300 dark:text-neutral-600">—</span>
                            )}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Set Rate Dialog */}
      <FormDialog
        open={!!showRate}
        onClose={() => setShowRate(null)}
        title={`Set Rate — ${BOS_SERVICES.find((s) => s.key === showRate)?.name ?? ""}`}
        description="Set the monthly rate for this service in a specific region."
        onSubmit={handleSetRate}
        submitLabel="Save Rate"
        loading={rateMut.isPending}
      >
        <div>
          <Label htmlFor="sr_region">Region</Label>
          <Select id="sr_region" name="region_code" required className="mt-1">
            <option value="">Select region...</option>
            {REGIONS.map((r) => <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="sr_amount">Monthly Amount (in local currency)</Label>
          <Input id="sr_amount" name="monthly_amount" type="number" min={0} required className="mt-1" />
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
