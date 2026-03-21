"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getRegions, addRegion, updateRegion } from "@/lib/api/saas";
import { COUNTRY_TAX_RULES } from "@/lib/constants";
import { Globe, Plus, Pencil, CheckCircle2, XCircle, Flag, MapPin } from "lucide-react";

/** All African currencies for the dropdown — extend as needed */
const CURRENCY_OPTIONS = [
  "KES", "TZS", "UGX", "RWF", "NGN", "GHS", "ZAR", "XOF", "EGP", "ETB",
  "BIF", "CDF", "MWK", "ZMW", "MZN", "AOA", "BWP", "NAD", "SZL", "LSL",
  "GMD", "GNF", "LRD", "SLL", "XAF", "SDG", "SSP", "DJF", "ERN", "SOS",
  "MAD", "TND", "LYD", "MUR", "SCR", "MVR", "USD",
];

interface Region {
  code: string;
  name: string;
  currency: string;
  tax_name?: string;
  vat_rate?: number;
  digital_tax_rate?: number;
  b2b_reverse_charge?: boolean;
  registration_required?: boolean;
  is_active?: boolean;
}

export default function RegionsPage() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [editRegion, setEditRegion] = useState<Region | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);
  const [search, setSearch] = useState("");

  const regions = useQuery({ queryKey: ["saas", "regions"], queryFn: getRegions });

  const addMut = useMutation({
    mutationFn: addRegion,
    onSuccess: () => {
      setShowAdd(false);
      qc.invalidateQueries({ queryKey: ["saas", "regions"] });
      setToast({ message: "Region added", variant: "success" });
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

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    addMut.mutate({
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

  function handleUpdate(e: React.FormEvent) {
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
  }

  // Merge server data with hardcoded defaults as fallback
  const serverRegions: Region[] = regions.data?.data?.regions ?? [];
  const fallbackRegions: Region[] = serverRegions.length > 0
    ? serverRegions
    : Object.entries(COUNTRY_TAX_RULES).map(([code, rules]) => ({
        code,
        name: regionName(code),
        currency: regionCurrency(code),
        tax_name: rules.tax_name,
        vat_rate: rules.vat_rate,
        digital_tax_rate: rules.digital_tax_rate,
        b2b_reverse_charge: rules.b2b_reverse_charge,
        registration_required: rules.registration_required,
        is_active: true,
      }));

  const filtered = search
    ? fallbackRegions.filter(
        (r) =>
          r.name.toLowerCase().includes(search.toLowerCase()) ||
          r.code.toLowerCase().includes(search.toLowerCase()) ||
          r.currency.toLowerCase().includes(search.toLowerCase()),
      )
    : fallbackRegions;

  const activeCount = fallbackRegions.filter((r) => r.is_active !== false).length;

  return (
    <div>
      <PageHeader
        title="Regions & Countries"
        description="Manage countries where BOS operates. Add new markets, set tax rules, and configure currencies."
        actions={
          <Button onClick={() => setShowAdd(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Country
          </Button>
        }
      />

      {/* Summary Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bos-purple/10">
              <Globe className="h-5 w-5 text-bos-purple" />
            </div>
            <div>
              <p className="text-2xl font-bold">{fallbackRegions.length}</p>
              <p className="text-xs text-bos-silver-dark">Total Countries</p>
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
              <p className="text-xs text-bos-silver-dark">Active Markets</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bos-gold-light">
              <Flag className="h-5 w-5 text-bos-gold-dark" />
            </div>
            <div>
              <p className="text-2xl font-bold">{new Set(fallbackRegions.map((r) => r.currency)).size}</p>
              <p className="text-xs text-bos-silver-dark">Currencies</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="mb-4">
        <Input
          placeholder="Search by country name, code, or currency..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
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
                <TableHead>Tax Name</TableHead>
                <TableHead className="text-right">VAT Rate</TableHead>
                <TableHead className="text-right">Digital Tax</TableHead>
                <TableHead className="text-center">B2B Reverse</TableHead>
                <TableHead className="text-center">Reg. Required</TableHead>
                <TableHead className="text-center">Status</TableHead>
                <TableHead className="text-right w-20">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10} className="text-center py-12 text-bos-silver-dark">
                    <MapPin className="mx-auto mb-2 h-8 w-8 opacity-30" />
                    {search ? "No countries match your search" : "No countries configured yet"}
                  </TableCell>
                </TableRow>
              )}
              {filtered.map((r) => (
                <TableRow key={r.code}>
                  <TableCell>
                    <span className="inline-flex items-center justify-center rounded-md bg-bos-purple/10 px-2 py-0.5 text-xs font-bold text-bos-purple">
                      {r.code}
                    </span>
                  </TableCell>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{r.currency}</Badge>
                  </TableCell>
                  <TableCell className="text-bos-silver-dark">{r.tax_name ?? "—"}</TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {r.vat_rate != null ? `${Math.round(r.vat_rate * 100)}%` : "—"}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {r.digital_tax_rate && r.digital_tax_rate > 0
                      ? `${(r.digital_tax_rate * 100).toFixed(1)}%`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-center">
                    {r.b2b_reverse_charge ? (
                      <CheckCircle2 className="inline h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="inline h-4 w-4 text-neutral-300" />
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    {r.registration_required ? (
                      <CheckCircle2 className="inline h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="inline h-4 w-4 text-neutral-300" />
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant={r.is_active !== false ? "success" : "outline"}>
                      {r.is_active !== false ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setEditRegion(r)}
                      className="gap-1"
                    >
                      <Pencil className="h-3 w-3" />
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Add Country Dialog */}
      <FormDialog
        open={showAdd}
        onClose={() => setShowAdd(false)}
        title="Add Country"
        description="Register a new country/region for BOS operations."
        onSubmit={handleAdd}
        submitLabel="Add Country"
        loading={addMut.isPending}
        wide
      >
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
      </FormDialog>

      {/* Edit Country Dialog */}
      <FormDialog
        open={!!editRegion}
        onClose={() => setEditRegion(null)}
        title={`Edit — ${editRegion?.name ?? ""}`}
        description={`Update details for ${editRegion?.code ?? ""}`}
        onSubmit={handleUpdate}
        submitLabel="Save Changes"
        loading={updateMut.isPending}
        wide
      >
        {editRegion && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Country Code</Label>
                <Input value={editRegion.code} disabled className="mt-1 bg-neutral-50 dark:bg-neutral-900" />
              </div>
              <div>
                <Label htmlFor="e_name">Country Name</Label>
                <Input id="e_name" name="name" required defaultValue={editRegion.name} className="mt-1" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="e_currency">Currency</Label>
                <Select id="e_currency" name="currency" required defaultValue={editRegion.currency} className="mt-1">
                  {CURRENCY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                </Select>
              </div>
              <div>
                <Label htmlFor="e_tax_name">Tax Name</Label>
                <Input id="e_tax_name" name="tax_name" defaultValue={editRegion.tax_name ?? "VAT"} className="mt-1" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="e_vat_rate">VAT Rate</Label>
                <Input id="e_vat_rate" name="vat_rate" type="number" step="0.001" min="0" max="1" defaultValue={editRegion.vat_rate ?? 0} className="mt-1" />
              </div>
              <div>
                <Label htmlFor="e_digital_tax">Digital Tax Rate</Label>
                <Input id="e_digital_tax" name="digital_tax_rate" type="number" step="0.001" min="0" max="1" defaultValue={editRegion.digital_tax_rate ?? 0} className="mt-1" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="e_b2b">B2B Reverse Charge</Label>
                <Select id="e_b2b" name="b2b_reverse_charge" defaultValue={editRegion.b2b_reverse_charge ? "true" : "false"} className="mt-1">
                  <option value="false">No</option>
                  <option value="true">Yes</option>
                </Select>
              </div>
              <div>
                <Label htmlFor="e_reg">Tax Registration Required</Label>
                <Select id="e_reg" name="registration_required" defaultValue={editRegion.registration_required ? "true" : "false"} className="mt-1">
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </Select>
              </div>
            </div>
          </>
        )}
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

/* ── Helpers to resolve region info from hardcoded REGIONS ── */

const REGION_NAMES: Record<string, string> = {
  KE: "Kenya", TZ: "Tanzania", UG: "Uganda", RW: "Rwanda",
  NG: "Nigeria", GH: "Ghana", ZA: "South Africa", CI: "Côte d'Ivoire",
  EG: "Egypt", ET: "Ethiopia",
};
const REGION_CURRENCIES: Record<string, string> = {
  KE: "KES", TZ: "TZS", UG: "UGX", RW: "RWF",
  NG: "NGN", GH: "GHS", ZA: "ZAR", CI: "XOF",
  EG: "EGP", ET: "ETB",
};

function regionName(code: string): string {
  return REGION_NAMES[code] ?? code;
}
function regionCurrency(code: string): string {
  return REGION_CURRENCIES[code] ?? "USD";
}
