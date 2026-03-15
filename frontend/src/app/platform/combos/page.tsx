"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Button, Card, CardContent, Input, Label, Select, Textarea, Toast,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Badge,
} from "@/components/ui";
import { getCombos, defineCombo, updateCombo, deactivateCombo, setComboRate } from "@/lib/api/saas";
import { REGIONS, BACKEND_ENGINES } from "@/lib/constants";
import { Plus, Edit, DollarSign, XCircle } from "lucide-react";

export default function CombosPage() {
  const queryClient = useQueryClient();
  const [showDefine, setShowDefine] = useState(false);
  const [showEdit, setShowEdit] = useState<string | null>(null);
  const [showRate, setShowRate] = useState<string | null>(null);
  const [showDeactivate, setShowDeactivate] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const combos = useQuery({ queryKey: ["saas", "combos"], queryFn: getCombos });

  const defineMut = useMutation({
    mutationFn: defineCombo,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["saas", "combos"] }); setShowDefine(false); setToast({ message: "Combo defined", variant: "success" }); },
    onError: () => setToast({ message: "Failed to define combo", variant: "error" }),
  });

  const updateMut = useMutation({
    mutationFn: updateCombo,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["saas", "combos"] }); setShowEdit(null); setToast({ message: "Combo updated", variant: "success" }); },
    onError: () => setToast({ message: "Failed to update combo", variant: "error" }),
  });

  const deactivateMut = useMutation({
    mutationFn: deactivateCombo,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["saas", "combos"] }); setShowDeactivate(null); setToast({ message: "Combo deactivated", variant: "success" }); },
    onError: () => setToast({ message: "Failed to deactivate combo", variant: "error" }),
  });

  const rateMut = useMutation({
    mutationFn: setComboRate,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["saas", "combos"] }); setShowRate(null); setToast({ message: "Rate set successfully", variant: "success" }); },
    onError: () => setToast({ message: "Failed to set rate", variant: "error" }),
  });

  const comboList = combos.data?.data ?? [];
  const paidEngines = BACKEND_ENGINES.filter((e) => e.category === "PAID");
  const editingCombo = comboList.find((c: { combo_id: string }) => c.combo_id === showEdit);

  function handleDefine(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const data = new FormData(form);
    const selectedEngines = data.getAll("paid_engines") as string[];
    defineMut.mutate({
      name: data.get("name") as string,
      slug: data.get("slug") as string,
      description: data.get("description") as string,
      business_model: data.get("business_model") as "B2B" | "B2C" | "BOTH",
      paid_engines: selectedEngines,
      max_branches: Number(data.get("max_branches")) || undefined,
      max_users: Number(data.get("max_users")) || undefined,
      max_api_calls_per_month: Number(data.get("max_api_calls")) || undefined,
      max_documents_per_month: Number(data.get("max_documents")) || undefined,
    });
  }

  function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!showEdit) return;
    const form = e.target as HTMLFormElement;
    const data = new FormData(form);
    updateMut.mutate({
      combo_id: showEdit,
      name: data.get("name") as string,
      description: data.get("description") as string,
    });
  }

  function handleSetRate(e: React.FormEvent) {
    e.preventDefault();
    if (!showRate) return;
    const form = e.target as HTMLFormElement;
    const data = new FormData(form);
    const regionCode = data.get("region_code") as string;
    const region = REGIONS.find((r) => r.code === regionCode);
    rateMut.mutate({
      combo_id: showRate,
      region_code: regionCode,
      currency: region?.currency ?? "KES",
      monthly_amount: Number(data.get("monthly_amount")),
    });
  }

  return (
    <div>
      <PageHeader
        title="Engine Combos"
        description="Mipango ya engine combo ambayo tenants wanachagua"
        actions={
          <Button onClick={() => setShowDefine(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Define Combo
          </Button>
        }
      />

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Combo Name</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Model</TableHead>
              <TableHead>Engines</TableHead>
              <TableHead>Quotas</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {comboList.map((combo: {
              combo_id: string; name: string; slug: string; business_model: string;
              paid_engines: string[]; quota?: { max_branches?: number; max_users?: number };
              status: string;
            }) => (
              <TableRow key={combo.combo_id}>
                <TableCell className="font-medium">{combo.name}</TableCell>
                <TableCell><code className="text-xs text-bos-silver-dark">{combo.slug}</code></TableCell>
                <TableCell><StatusBadge status={combo.business_model} /></TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {combo.paid_engines?.map((e) => (
                      <Badge key={e} variant="purple" className="text-[10px]">{e}</Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell className="text-xs text-bos-silver-dark">
                  {combo.quota ? `${combo.quota.max_branches ?? "∞"} branches, ${combo.quota.max_users ?? "∞"} users` : "—"}
                </TableCell>
                <TableCell><StatusBadge status={combo.status} /></TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" onClick={() => setShowEdit(combo.combo_id)} title="Edit">
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setShowRate(combo.combo_id)} title="Set Rate">
                      <DollarSign className="h-4 w-4" />
                    </Button>
                    {combo.status === "ACTIVE" && (
                      <Button variant="ghost" size="icon" onClick={() => setShowDeactivate(combo.combo_id)} title="Deactivate">
                        <XCircle className="h-4 w-4 text-red-500" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {comboList.length === 0 && !combos.isLoading && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-bos-silver-dark py-8">
                  No combos defined yet. Click "Define Combo" to create one.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Define Combo Dialog */}
      <FormDialog
        open={showDefine}
        onClose={() => setShowDefine(false)}
        title="Define Engine Combo"
        description="Tengeneza mpango mpya wa engine combo"
        onSubmit={handleDefine}
        submitLabel="Define"
        loading={defineMut.isPending}
        wide
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="name">Combo Name</Label>
            <Input id="name" name="name" placeholder="e.g. BOS Duka" required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="slug">Slug</Label>
            <Input id="slug" name="slug" placeholder="e.g. bos-duka" required className="mt-1" />
          </div>
        </div>
        <div>
          <Label htmlFor="description">Description</Label>
          <Textarea id="description" name="description" placeholder="Short description..." className="mt-1" />
        </div>
        <div>
          <Label htmlFor="business_model">Business Model</Label>
          <Select id="business_model" name="business_model" className="mt-1">
            <option value="B2C">B2C — Consumer-facing</option>
            <option value="B2B">B2B — Business-to-business</option>
            <option value="BOTH">BOTH</option>
          </Select>
        </div>
        <div>
          <Label>Paid Engines</Label>
          <div className="mt-1 grid grid-cols-2 gap-2 rounded-md border border-bos-silver/30 p-3">
            {paidEngines.map((eng) => (
              <label key={eng.key} className="flex items-center gap-2 text-sm">
                <input type="checkbox" name="paid_engines" value={eng.key} className="rounded" />
                <span>{eng.displayName}</span>
                <code className="text-[10px] text-bos-silver-dark">({eng.key})</code>
              </label>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="max_branches">Max Branches</Label>
            <Input id="max_branches" name="max_branches" type="number" placeholder="e.g. 5" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="max_users">Max Users</Label>
            <Input id="max_users" name="max_users" type="number" placeholder="e.g. 20" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="max_api_calls">Max API Calls/Month</Label>
            <Input id="max_api_calls" name="max_api_calls" type="number" placeholder="e.g. 10000" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="max_documents">Max Documents/Month</Label>
            <Input id="max_documents" name="max_documents" type="number" placeholder="e.g. 500" className="mt-1" />
          </div>
        </div>
      </FormDialog>

      {/* Edit Combo Dialog */}
      <FormDialog
        open={!!showEdit}
        onClose={() => setShowEdit(null)}
        title="Edit Combo"
        onSubmit={handleUpdate}
        submitLabel="Update"
        loading={updateMut.isPending}
      >
        <div>
          <Label htmlFor="edit_name">Combo Name</Label>
          <Input id="edit_name" name="name" defaultValue={editingCombo?.name ?? ""} required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="edit_desc">Description</Label>
          <Textarea id="edit_desc" name="description" defaultValue={editingCombo?.description ?? ""} className="mt-1" />
        </div>
      </FormDialog>

      {/* Set Rate Dialog */}
      <FormDialog
        open={!!showRate}
        onClose={() => setShowRate(null)}
        title="Set Combo Rate"
        description="Weka bei ya kila mwezi kwa region maalum"
        onSubmit={handleSetRate}
        submitLabel="Set Rate"
        loading={rateMut.isPending}
      >
        <div>
          <Label htmlFor="region_code">Region</Label>
          <Select id="region_code" name="region_code" className="mt-1">
            {REGIONS.map((r) => (
              <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="monthly_amount">Monthly Amount</Label>
          <Input id="monthly_amount" name="monthly_amount" type="number" placeholder="e.g. 4500" required className="mt-1" />
        </div>
      </FormDialog>

      {/* Deactivate Confirmation */}
      <ConfirmDialog
        open={!!showDeactivate}
        onClose={() => setShowDeactivate(null)}
        onConfirm={() => showDeactivate && deactivateMut.mutate({ combo_id: showDeactivate })}
        title="Deactivate Combo"
        description="Combo hii itaondolewa kwa tenants wapya. Tenants waliopo hawataathiriwa. Huwezi kurudisha hali hii."
        confirmLabel="Deactivate"
        confirmVariant="destructive"
        loading={deactivateMut.isPending}
      />

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
