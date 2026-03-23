"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import {
  Card, CardContent, Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Badge, Button, Input, Label, Select, Toast,
} from "@/components/ui";
import { FormDialog } from "@/components/shared/form-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import { listBranches } from "@/lib/api/admin";
import api from "@/lib/api/client";
import type { Branch } from "@/types/api";

const TIMEZONES = [
  "Africa/Nairobi",
  "Africa/Dar_es_Salaam",
  "Africa/Kampala",
  "Africa/Kigali",
  "Africa/Lagos",
  "Africa/Accra",
  "Africa/Johannesburg",
  "Africa/Cairo",
  "Africa/Addis_Ababa",
  "Africa/Abidjan",
  "UTC",
];

export default function BranchesPage() {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  // Create dialog
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newTimezone, setNewTimezone] = useState("Africa/Nairobi");
  const [saving, setSaving] = useState(false);

  // Edit dialog
  const [editBranch, setEditBranch] = useState<Branch | null>(null);
  const [editName, setEditName] = useState("");
  const [editTimezone, setEditTimezone] = useState("");
  const [updating, setUpdating] = useState(false);

  function loadBranches() {
    setLoading(true);
    listBranches()
      .then((res) => setBranches(res.branches || []))
      .catch(() => setToast({ message: "Failed to load branches", variant: "error" }))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadBranches(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setSaving(true);
    try {
      await api.post("/admin/branches/create", {
        name: newName.trim(),
        timezone: newTimezone,
      });
      setToast({ message: `Branch "${newName}" created`, variant: "success" });
      setShowCreate(false);
      setNewName("");
      loadBranches();
    } catch {
      setToast({ message: "Failed to create branch", variant: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!editBranch || !editName.trim()) return;
    setUpdating(true);
    try {
      await api.post("/admin/branches/update", {
        branch_id: editBranch.branch_id,
        name: editName.trim(),
        timezone: editTimezone,
      });
      setToast({ message: "Branch updated", variant: "success" });
      setEditBranch(null);
      loadBranches();
    } catch {
      setToast({ message: "Failed to update branch", variant: "error" });
    } finally {
      setUpdating(false);
    }
  }

  function openEdit(b: Branch) {
    setEditBranch(b);
    setEditName(b.name);
    setEditTimezone(b.timezone || "UTC");
  }

  return (
    <AppShell>
      <PageHeader
        title="Branches"
        description="Manage your business locations"
        actions={
          <Button size="sm" onClick={() => setShowCreate(true)}>
            Add Branch
          </Button>
        }
      />

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : branches.length === 0 ? (
            <EmptyState title="No branches found" description="Add your first branch to get started" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Branch ID</TableHead>
                  <TableHead>Timezone</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {branches.map((b) => (
                  <TableRow key={b.branch_id}>
                    <TableCell className="font-medium">{b.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">{b.branch_id.slice(0, 12)}...</Badge>
                    </TableCell>
                    <TableCell>{b.timezone || "UTC"}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="outline" size="sm" onClick={() => openEdit(b)}>
                        Edit
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Branch Dialog */}
      <FormDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Add Branch"
        description="Create a new business location"
        onSubmit={handleCreate}
        submitLabel="Create Branch"
        loading={saving}
      >
        <div>
          <Label htmlFor="branchName">Branch Name</Label>
          <Input
            id="branchName"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="e.g. Westlands Branch"
            required
          />
        </div>
        <div>
          <Label htmlFor="branchTz">Timezone</Label>
          <Select id="branchTz" value={newTimezone} onChange={(e) => setNewTimezone(e.target.value)}>
            {TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>{tz}</option>
            ))}
          </Select>
        </div>
      </FormDialog>

      {/* Edit Branch Dialog */}
      <FormDialog
        open={!!editBranch}
        onClose={() => setEditBranch(null)}
        title="Edit Branch"
        description={`Update ${editBranch?.name || ""}`}
        onSubmit={handleUpdate}
        submitLabel="Update"
        loading={updating}
      >
        <div>
          <Label htmlFor="editName">Branch Name</Label>
          <Input
            id="editName"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="editTz">Timezone</Label>
          <Select id="editTz" value={editTimezone} onChange={(e) => setEditTimezone(e.target.value)}>
            {TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>{tz}</option>
            ))}
          </Select>
        </div>
      </FormDialog>

      {toast && (
        <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />
      )}
    </AppShell>
  );
}
