"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge, Textarea,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import {
  getRegions, addRegion, updateRegion, launchRegion, suspendRegion,
  reactivateRegion, sunsetRegion,
} from "@/lib/api/saas";
import { COUNTRY_TAX_RULES } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import {
  Globe, Plus, Pencil, CheckCircle2, XCircle, MapPin, Eye,
  Rocket, PauseCircle, PlayCircle, Sunset, AlertTriangle,
  CreditCard, Building2, BarChart3, Shield,
} from "lucide-react";

const CURRENCY_OPTIONS = [
  "KES", "TZS", "UGX", "RWF", "NGN", "GHS", "ZAR", "XOF", "EGP", "ETB",
  "BIF", "CDF", "MWK", "ZMW", "MZN", "AOA", "BWP", "NAD", "SZL", "LSL",
  "GMD", "GNF", "LRD", "SLL", "XAF", "SDG", "SSP", "DJF", "ERN", "SOS",
  "MAD", "TND", "LYD", "MUR", "SCR", "MVR", "USD",
];

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-neutral-100 text-neutral-600",
  PILOT: "bg-purple-100 text-purple-700",
  ACTIVE: "bg-green-100 text-green-700",
  SUSPENDED: "bg-orange-100 text-orange-700",
  SUNSET: "bg-red-100 text-red-700",
};

interface Region {
  code: string;
  name: string;
  currency: string;
  status?: string;
  tax_name?: string;
  vat_rate?: number;
  digital_tax_rate?: number;
  b2b_reverse_charge?: boolean;
  registration_required?: boolean;
  is_active?: boolean;
  timezone?: string;
  default_language?: string;
  support_phone?: string;
  support_email?: string;
  launched_at?: string;
  suspended_at?: string;
  sunset_at?: string;
  pilot_tenant_limit?: number;
  pilot_tenant_count?: number;
}

type TabKey = "overview" | "lifecycle" | "add-region";
type ToastState = { message: string; variant: "success" | "error" } | null;

export default function RegionsPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [toast, setToast] = useState<ToastState>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [editRegion, setEditRegion] = useState<Region | null>(null);

  // Lifecycle dialogs
  const [launchDialog, setLaunchDialog] = useState<Region | null>(null);
  const [suspendDialog, setSuspendDialog] = useState<Region | null>(null);
  const [reactivateDialog, setReactivateDialog] = useState<Region | null>(null);
  const [sunsetDialog, setSunsetDialog] = useState<Region | null>(null);

  const regions = useQuery({ queryKey: ["saas", "regions"], queryFn: getRegions });

  const addMut = useMutation({
    mutationFn: addRegion,
    onSuccess: () => {
      setActiveTab("overview");
      qc.invalidateQueries({ queryKey: ["saas", "regions"] });
      setToast({ message: "Region added successfully", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to add region", variant: "error" }),
  });

  const updateMut = useMutation({
    mutationFn: updateRegion,
    onSuccess: () => {
      setEditRegion(null);
      qc.invalidateQueries({ queryKey: ["saas", "regions"] });
      setToast({ message: "Region updated", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to update region", variant: "error" }),
  });

  const launchMut = useMutation({
    mutationFn: launchRegion,
    onSuccess: () => {
      setLaunchDialog(null);
      qc.invalidateQueries({ queryKey: ["saas", "regions"] });
      setToast({ message: "Region launched!", variant: "success" });
    },
    onError: (err: any) => setToast({ message: err?.response?.data?.error || "Launch failed — ensure payment channels are configured", variant: "error" }),
  });

  const suspendMut = useMutation({
    mutationFn: suspendRegion,
    onSuccess: () => {
      setSuspendDialog(null);
      qc.invalidateQueries({ queryKey: ["saas", "regions"] });
      setToast({ message: "Region suspended", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to suspend region", variant: "error" }),
  });

  const reactivateMut = useMutation({
    mutationFn: reactivateRegion,
    onSuccess: () => {
      setReactivateDialog(null);
      qc.invalidateQueries({ queryKey: ["saas", "regions"] });
      setToast({ message: "Region reactivated", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to reactivate", variant: "error" }),
  });

  const sunsetMut = useMutation({
    mutationFn: sunsetRegion,
    onSuccess: () => {
      setSunsetDialog(null);
      qc.invalidateQueries({ queryKey: ["saas", "regions"] });
      setToast({ message: "Region sunset initiated", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to sunset region", variant: "error" }),
  });

  // Merge server data with hardcoded defaults
  const serverRegions: Region[] = regions.data?.data?.regions ?? [];
  const allRegions: Region[] = serverRegions.length > 0
    ? serverRegions
    : Object.entries(COUNTRY_TAX_RULES).map(([code, rules]) => ({
        code,
        name: REGION_NAMES[code] ?? code,
        currency: REGION_CURRENCIES[code] ?? "USD",
        status: "DRAFT",
        tax_name: rules.tax_name,
        vat_rate: rules.vat_rate,
        digital_tax_rate: rules.digital_tax_rate,
        b2b_reverse_charge: rules.b2b_reverse_charge,
        registration_required: rules.registration_required,
        is_active: true,
      }));

  const filtered = allRegions.filter((r) => {
    if (statusFilter !== "ALL" && (r.status || "DRAFT") !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return r.name.toLowerCase().includes(q) || r.code.toLowerCase().includes(q) || r.currency.toLowerCase().includes(q);
    }
    return true;
  });

  // Stats
  const counts = allRegions.reduce((acc, r) => {
    const s = r.status || "DRAFT";
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const tabs: { key: TabKey; label: string }[] = [
    { key: "overview", label: "All Regions" },
    { key: "lifecycle", label: "Lifecycle Management" },
    { key: "add-region", label: "Add New Region" },
  ];

  return (
    <div>
      <PageHeader
        title="Region Management"
        description="Manage countries, lifecycles, payment channels, settlement accounts, and regional operations."
        actions={
          <Button onClick={() => setActiveTab("add-region")} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Country
          </Button>
        }
      />

      {/* Stat Cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-5">
        <StatCard title="Total Regions" value={allRegions.length} icon={Globe} />
        <StatCard title="Active" value={counts["ACTIVE"] || 0} icon={CheckCircle2} />
        <StatCard title="Pilot" value={counts["PILOT"] || 0} icon={Rocket} />
        <StatCard title="Draft" value={counts["DRAFT"] || 0} icon={Shield} />
        <StatCard title="Suspended" value={counts["SUSPENDED"] || 0} icon={PauseCircle} />
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-bos-silver-light p-1 dark:bg-neutral-800 w-fit flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-white text-bos-purple shadow-sm dark:bg-neutral-900"
                : "text-bos-silver-dark hover:text-neutral-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <RegionOverview
          regions={filtered}
          search={search}
          statusFilter={statusFilter}
          onSearch={setSearch}
          onStatusFilter={setStatusFilter}
          onEdit={setEditRegion}
          onView={(code) => router.push(`/platform/regions/${code}`)}
          onLaunch={setLaunchDialog}
          onSuspend={setSuspendDialog}
          onReactivate={setReactivateDialog}
          onSunset={setSunsetDialog}
        />
      )}

      {activeTab === "lifecycle" && (
        <LifecycleManagement
          regions={allRegions}
          onLaunch={setLaunchDialog}
          onSuspend={setSuspendDialog}
          onReactivate={setReactivateDialog}
          onSunset={setSunsetDialog}
          onView={(code) => router.push(`/platform/regions/${code}`)}
        />
      )}

      {activeTab === "add-region" && (
        <AddRegionForm onSubmit={(data) => addMut.mutate(data)} loading={addMut.isPending} />
      )}

      {/* Edit Dialog */}
      <FormDialog
        open={!!editRegion}
        onClose={() => setEditRegion(null)}
        title={`Edit — ${editRegion?.name ?? ""}`}
        description={`Update details for ${editRegion?.code ?? ""}`}
        onSubmit={(e) => {
          e.preventDefault();
          if (!editRegion) return;
          const d = new FormData(e.target as HTMLFormElement);
          updateMut.mutate({
            code: editRegion.code,
            name: d.get("name") as string,
            currency: d.get("currency") as string,
            tax_name: d.get("tax_name") as string || "VAT",
            vat_rate: parseFloat(d.get("vat_rate") as string) || 0,
            digital_tax_rate: parseFloat(d.get("digital_tax_rate") as string) || 0,
            b2b_reverse_charge: d.get("b2b_reverse_charge") === "true",
            registration_required: d.get("registration_required") === "true",
          });
        }}
        submitLabel="Save Changes"
        loading={updateMut.isPending}
        wide
      >
        {editRegion && <RegionFormFields region={editRegion} />}
      </FormDialog>

      {/* Launch Confirmation */}
      <ConfirmDialog
        open={!!launchDialog}
        onClose={() => setLaunchDialog(null)}
        title={`Launch ${launchDialog?.name}?`}
        description="This will transition the region from DRAFT/PILOT to ACTIVE. Ensure payment channels and settlement accounts are configured. This action cannot be easily undone."
        confirmLabel="Launch Region"
        onConfirm={() => launchDialog && launchMut.mutate({ region_code: launchDialog.code })}
        loading={launchMut.isPending}
      />

      {/* Suspend Dialog */}
      <FormDialog
        open={!!suspendDialog}
        onClose={() => setSuspendDialog(null)}
        title={`Suspend ${suspendDialog?.name}?`}
        description="All operations in this region will be paused. Existing tenants will not be able to process transactions."
        onSubmit={(e) => {
          e.preventDefault();
          const d = new FormData(e.target as HTMLFormElement);
          suspendDialog && suspendMut.mutate({
            region_code: suspendDialog.code,
            reason: d.get("reason") as string,
          });
        }}
        submitLabel="Suspend Region"
        loading={suspendMut.isPending}
      >
        <div>
          <Label htmlFor="sus_reason">Reason for Suspension</Label>
          <Textarea id="sus_reason" name="reason" required placeholder="e.g. Regulatory compliance issue, payment partner offline..." className="mt-1" />
        </div>
      </FormDialog>

      {/* Reactivate Confirmation */}
      <ConfirmDialog
        open={!!reactivateDialog}
        onClose={() => setReactivateDialog(null)}
        title={`Reactivate ${reactivateDialog?.name}?`}
        description="This will resume all operations in this region. Tenants will be able to process transactions again."
        confirmLabel="Reactivate"
        onConfirm={() => reactivateDialog && reactivateMut.mutate({ region_code: reactivateDialog.code })}
        loading={reactivateMut.isPending}
      />

      {/* Sunset Dialog */}
      <FormDialog
        open={!!sunsetDialog}
        onClose={() => setSunsetDialog(null)}
        title={`Sunset ${sunsetDialog?.name}?`}
        description="This permanently retires the region. No new tenants can be created. Existing tenants must be migrated. This is IRREVERSIBLE."
        onSubmit={(e) => {
          e.preventDefault();
          const d = new FormData(e.target as HTMLFormElement);
          sunsetDialog && sunsetMut.mutate({
            region_code: sunsetDialog.code,
            reason: d.get("reason") as string,
          });
        }}
        submitLabel="Sunset Region"
        loading={sunsetMut.isPending}
      >
        <div>
          <Label htmlFor="sun_reason">Reason for Sunset</Label>
          <Textarea id="sun_reason" name="reason" required placeholder="e.g. Market exit, regulatory prohibition..." className="mt-1" />
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

/* ── Region Overview Tab ─────────────────────────────────── */

function RegionOverview({
  regions, search, statusFilter, onSearch, onStatusFilter,
  onEdit, onView, onLaunch, onSuspend, onReactivate, onSunset,
}: {
  regions: Region[];
  search: string;
  statusFilter: string;
  onSearch: (s: string) => void;
  onStatusFilter: (s: string) => void;
  onEdit: (r: Region) => void;
  onView: (code: string) => void;
  onLaunch: (r: Region) => void;
  onSuspend: (r: Region) => void;
  onReactivate: (r: Region) => void;
  onSunset: (r: Region) => void;
}) {
  return (
    <>
      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <Input
          placeholder="Search by name, code, or currency..."
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          className="max-w-xs"
        />
        <Select
          value={statusFilter}
          onChange={(e) => onStatusFilter(e.target.value)}
          className="w-40"
        >
          <option value="ALL">All Statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="PILOT">Pilot</option>
          <option value="ACTIVE">Active</option>
          <option value="SUSPENDED">Suspended</option>
          <option value="SUNSET">Sunset</option>
        </Select>
      </div>

      {/* Regions Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-bos-silver-light/50 dark:bg-neutral-900 hover:bg-bos-silver-light/50">
                <TableHead className="w-16">Code</TableHead>
                <TableHead>Country</TableHead>
                <TableHead>Currency</TableHead>
                <TableHead className="text-center">Status</TableHead>
                <TableHead>Tax</TableHead>
                <TableHead className="text-right">VAT Rate</TableHead>
                <TableHead className="text-center">B2B Reverse</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {regions.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-12 text-bos-silver-dark">
                    <MapPin className="mx-auto mb-2 h-8 w-8 opacity-30" />
                    {search ? "No regions match your search" : "No regions configured yet"}
                  </TableCell>
                </TableRow>
              )}
              {regions.map((r) => {
                const status = r.status || "DRAFT";
                return (
                  <TableRow key={r.code} className="group">
                    <TableCell>
                      <span className="inline-flex items-center justify-center rounded-md bg-bos-purple/10 px-2 py-0.5 text-xs font-bold text-bos-purple">
                        {r.code}
                      </span>
                    </TableCell>
                    <TableCell className="font-medium">{r.name}</TableCell>
                    <TableCell><Badge variant="outline">{r.currency}</Badge></TableCell>
                    <TableCell className="text-center">
                      <StatusBadge status={status} />
                    </TableCell>
                    <TableCell className="text-bos-silver-dark text-sm">{r.tax_name ?? "VAT"}</TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {r.vat_rate != null ? `${Math.round(r.vat_rate * 100)}%` : "—"}
                    </TableCell>
                    <TableCell className="text-center">
                      {r.b2b_reverse_charge ? (
                        <CheckCircle2 className="inline h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="inline h-4 w-4 text-neutral-300" />
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button size="sm" variant="ghost" onClick={() => onView(r.code)} title="View Details">
                          <Eye className="h-3.5 w-3.5" />
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => onEdit(r)} title="Edit">
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        {status === "DRAFT" && (
                          <Button size="sm" variant="ghost" onClick={() => onLaunch(r)} title="Launch" className="text-green-600 hover:text-green-700">
                            <Rocket className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        {status === "PILOT" && (
                          <Button size="sm" variant="ghost" onClick={() => onLaunch(r)} title="Go Live" className="text-green-600 hover:text-green-700">
                            <Rocket className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        {status === "ACTIVE" && (
                          <Button size="sm" variant="ghost" onClick={() => onSuspend(r)} title="Suspend" className="text-orange-600 hover:text-orange-700">
                            <PauseCircle className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        {status === "SUSPENDED" && (
                          <Button size="sm" variant="ghost" onClick={() => onReactivate(r)} title="Reactivate" className="text-green-600 hover:text-green-700">
                            <PlayCircle className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}

/* ── Lifecycle Management Tab ────────────────────────────── */

function LifecycleManagement({
  regions, onLaunch, onSuspend, onReactivate, onSunset, onView,
}: {
  regions: Region[];
  onLaunch: (r: Region) => void;
  onSuspend: (r: Region) => void;
  onReactivate: (r: Region) => void;
  onSunset: (r: Region) => void;
  onView: (code: string) => void;
}) {
  const stages = [
    { key: "DRAFT", label: "Draft", icon: Shield, color: "text-neutral-500", description: "Region configured but not yet operational" },
    { key: "PILOT", label: "Pilot", icon: Rocket, color: "text-purple-600", description: "Limited rollout with pilot tenants" },
    { key: "ACTIVE", label: "Active", icon: CheckCircle2, color: "text-green-600", description: "Fully operational, accepting tenants" },
    { key: "SUSPENDED", label: "Suspended", icon: PauseCircle, color: "text-orange-600", description: "Operations paused temporarily" },
    { key: "SUNSET", label: "Sunset", icon: Sunset, color: "text-red-600", description: "Permanently retired" },
  ];

  return (
    <div className="space-y-6">
      {/* Lifecycle Flow Diagram */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Region Lifecycle Flow</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center justify-center gap-2">
            {stages.map((stage, i) => {
              const Icon = stage.icon;
              const count = regions.filter((r) => (r.status || "DRAFT") === stage.key).length;
              return (
                <div key={stage.key} className="flex items-center gap-2">
                  <div className="flex flex-col items-center rounded-lg border border-bos-silver/30 p-3 min-w-[120px] dark:border-bos-silver/20">
                    <Icon className={`h-6 w-6 ${stage.color}`} />
                    <span className="mt-1 text-sm font-semibold">{stage.label}</span>
                    <span className="text-xs text-bos-silver-dark">{count} region{count !== 1 ? "s" : ""}</span>
                  </div>
                  {i < stages.length - 1 && (
                    <span className="text-bos-silver-dark text-lg">&rarr;</span>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Regions by Stage */}
      {stages.map((stage) => {
        const stageRegions = regions.filter((r) => (r.status || "DRAFT") === stage.key);
        if (stageRegions.length === 0) return null;

        return (
          <Card key={stage.key}>
            <CardHeader>
              <div className="flex items-center gap-2">
                <stage.icon className={`h-5 w-5 ${stage.color}`} />
                <CardTitle className="text-base">{stage.label} Regions ({stageRegions.length})</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {stageRegions.map((r) => (
                  <div key={r.code} className="flex items-center justify-between rounded-lg border border-bos-silver/30 p-3 dark:border-bos-silver/20">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-bos-purple/10 px-1.5 py-0.5 text-xs font-bold text-bos-purple">{r.code}</span>
                        <span className="font-medium text-sm">{r.name}</span>
                      </div>
                      <div className="mt-1 flex gap-2 text-xs text-bos-silver-dark">
                        <span>{r.currency}</span>
                        {r.launched_at && <span>Launched: {formatDate(r.launched_at)}</span>}
                        {r.suspended_at && <span>Suspended: {formatDate(r.suspended_at)}</span>}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => onView(r.code)} title="View">
                        <Eye className="h-3.5 w-3.5" />
                      </Button>
                      {stage.key === "DRAFT" && (
                        <Button size="sm" variant="ghost" onClick={() => onLaunch(r)} className="text-green-600" title="Launch">
                          <Rocket className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      {stage.key === "PILOT" && (
                        <Button size="sm" variant="ghost" onClick={() => onLaunch(r)} className="text-green-600" title="Go Live">
                          <Rocket className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      {stage.key === "ACTIVE" && (
                        <>
                          <Button size="sm" variant="ghost" onClick={() => onSuspend(r)} className="text-orange-600" title="Suspend">
                            <PauseCircle className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => onSunset(r)} className="text-red-600" title="Sunset">
                            <Sunset className="h-3.5 w-3.5" />
                          </Button>
                        </>
                      )}
                      {stage.key === "SUSPENDED" && (
                        <>
                          <Button size="sm" variant="ghost" onClick={() => onReactivate(r)} className="text-green-600" title="Reactivate">
                            <PlayCircle className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => onSunset(r)} className="text-red-600" title="Sunset">
                            <Sunset className="h-3.5 w-3.5" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

/* ── Add Region Form (Inline Tab) ────────────────────────── */

function AddRegionForm({ onSubmit, loading }: { onSubmit: (data: any) => void; loading: boolean }) {
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    onSubmit({
      code: (d.get("code") as string).toUpperCase(),
      name: d.get("name") as string,
      currency: d.get("currency") as string,
      tax_name: d.get("tax_name") as string || "VAT",
      vat_rate: parseFloat(d.get("vat_rate") as string) || 0,
      digital_tax_rate: parseFloat(d.get("digital_tax_rate") as string) || 0,
      b2b_reverse_charge: d.get("b2b_reverse_charge") === "true",
      registration_required: d.get("registration_required") === "true",
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Register New Country / Region</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4 max-w-2xl">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="r_code">Country Code (ISO 3166-1 alpha-2)</Label>
              <Input id="r_code" name="code" required maxLength={2} placeholder="e.g. CD" className="mt-1 uppercase" />
            </div>
            <div>
              <Label htmlFor="r_name">Country Name</Label>
              <Input id="r_name" name="name" required placeholder="e.g. DR Congo" className="mt-1" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="r_currency">Currency</Label>
              <Select id="r_currency" name="currency" required className="mt-1">
                <option value="">Select currency...</option>
                {CURRENCY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
              </Select>
            </div>
            <div>
              <Label htmlFor="r_tax_name">Tax Name</Label>
              <Input id="r_tax_name" name="tax_name" placeholder="e.g. VAT, TVA, GST" defaultValue="VAT" className="mt-1" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="r_vat_rate">VAT Rate (decimal, e.g. 0.16 = 16%)</Label>
              <Input id="r_vat_rate" name="vat_rate" type="number" step="0.001" min="0" max="1" placeholder="0.16" className="mt-1" />
            </div>
            <div>
              <Label htmlFor="r_digital_tax">Digital Tax Rate (decimal, 0 if none)</Label>
              <Input id="r_digital_tax" name="digital_tax_rate" type="number" step="0.001" min="0" max="1" placeholder="0" defaultValue="0" className="mt-1" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="r_b2b">B2B Reverse Charge</Label>
              <Select id="r_b2b" name="b2b_reverse_charge" className="mt-1">
                <option value="false">No</option>
                <option value="true">Yes</option>
              </Select>
            </div>
            <div>
              <Label htmlFor="r_reg">Tax Registration Required</Label>
              <Select id="r_reg" name="registration_required" className="mt-1">
                <option value="true">Yes</option>
                <option value="false">No</option>
              </Select>
            </div>
          </div>
          <Button type="submit" disabled={loading} className="gap-2">
            <Plus className="h-4 w-4" />
            {loading ? "Adding..." : "Add Country"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

/* ── Shared Region Form Fields ───────────────────────────── */

function RegionFormFields({ region }: { region: Region }) {
  return (
    <>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Country Code</Label>
          <Input value={region.code} disabled className="mt-1 bg-neutral-50 dark:bg-neutral-900" />
        </div>
        <div>
          <Label htmlFor="e_name">Country Name</Label>
          <Input id="e_name" name="name" required defaultValue={region.name} className="mt-1" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="e_currency">Currency</Label>
          <Select id="e_currency" name="currency" required defaultValue={region.currency} className="mt-1">
            {CURRENCY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="e_tax_name">Tax Name</Label>
          <Input id="e_tax_name" name="tax_name" defaultValue={region.tax_name ?? "VAT"} className="mt-1" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="e_vat_rate">VAT Rate</Label>
          <Input id="e_vat_rate" name="vat_rate" type="number" step="0.001" min="0" max="1" defaultValue={region.vat_rate ?? 0} className="mt-1" />
        </div>
        <div>
          <Label htmlFor="e_digital_tax">Digital Tax Rate</Label>
          <Input id="e_digital_tax" name="digital_tax_rate" type="number" step="0.001" min="0" max="1" defaultValue={region.digital_tax_rate ?? 0} className="mt-1" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="e_b2b">B2B Reverse Charge</Label>
          <Select id="e_b2b" name="b2b_reverse_charge" defaultValue={region.b2b_reverse_charge ? "true" : "false"} className="mt-1">
            <option value="false">No</option>
            <option value="true">Yes</option>
          </Select>
        </div>
        <div>
          <Label htmlFor="e_reg">Tax Registration Required</Label>
          <Select id="e_reg" name="registration_required" defaultValue={region.registration_required ? "true" : "false"} className="mt-1">
            <option value="true">Yes</option>
            <option value="false">No</option>
          </Select>
        </div>
      </div>
    </>
  );
}

/* ── Region Name/Currency Helpers ────────────────────────── */

const REGION_NAMES: Record<string, string> = {
  KE: "Kenya", TZ: "Tanzania", UG: "Uganda", RW: "Rwanda",
  NG: "Nigeria", GH: "Ghana", ZA: "South Africa", CI: "Cote d'Ivoire",
  EG: "Egypt", ET: "Ethiopia",
};
const REGION_CURRENCIES: Record<string, string> = {
  KE: "KES", TZ: "TZS", UG: "UGX", RW: "RWF",
  NG: "NGN", GH: "GHS", ZA: "ZAR", CI: "XOF",
  EG: "EGP", ET: "ETB",
};
