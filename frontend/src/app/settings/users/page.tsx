"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Card, CardContent, CardHeader, CardTitle,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Badge, Button, Input, Label, Select, Toast,
} from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import {
  listActors, listRoles, createRole, assignRole, revokeRole, deactivateActor,
} from "@/lib/api/admin";
import { VALID_PERMISSIONS } from "@/lib/constants";
import type { Actor, Role } from "@/types/api";

export default function UsersPage() {
  const [actors, setActors] = useState<Actor[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  // Create role dialog
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [newRoleName, setNewRoleName] = useState("");
  const [newRolePerms, setNewRolePerms] = useState<string[]>([]);
  const [savingRole, setSavingRole] = useState(false);

  // Assign role dialog
  const [assignTarget, setAssignTarget] = useState<Actor | null>(null);
  const [assignRoleId, setAssignRoleId] = useState("");
  const [assigningRole, setAssigningRole] = useState(false);

  // Deactivate dialog
  const [deactivateTarget, setDeactivateTarget] = useState<Actor | null>(null);
  const [deactivating, setDeactivating] = useState(false);

  function loadData() {
    setLoading(true);
    Promise.all([listActors(), listRoles()])
      .then(([actorsRes, rolesRes]) => {
        setActors(actorsRes.actors || []);
        setRoles(rolesRes.roles || []);
      })
      .catch(() => setToast({ message: "Failed to load data", variant: "error" }))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, []);

  async function handleCreateRole(e: React.FormEvent) {
    e.preventDefault();
    if (!newRoleName.trim() || newRolePerms.length === 0) return;
    setSavingRole(true);
    try {
      await createRole(newRoleName.trim(), newRolePerms);
      setToast({ message: `Role "${newRoleName}" created`, variant: "success" });
      setShowCreateRole(false);
      setNewRoleName("");
      setNewRolePerms([]);
      loadData();
    } catch {
      setToast({ message: "Failed to create role", variant: "error" });
    } finally {
      setSavingRole(false);
    }
  }

  async function handleAssignRole(e: React.FormEvent) {
    e.preventDefault();
    if (!assignTarget || !assignRoleId) return;
    setAssigningRole(true);
    try {
      await assignRole(assignTarget.actor_id, assignRoleId);
      setToast({ message: `Role assigned to ${assignTarget.display_name || assignTarget.actor_id}`, variant: "success" });
      setAssignTarget(null);
      setAssignRoleId("");
      loadData();
    } catch {
      setToast({ message: "Failed to assign role", variant: "error" });
    } finally {
      setAssigningRole(false);
    }
  }

  async function handleRevokeRole(actorId: string, roleId: string, roleName: string) {
    if (!confirm(`Revoke role "${roleName}" from this actor?`)) return;
    try {
      await revokeRole(actorId, roleId);
      setToast({ message: `Role "${roleName}" revoked`, variant: "success" });
      loadData();
    } catch {
      setToast({ message: "Failed to revoke role", variant: "error" });
    }
  }

  async function handleDeactivate() {
    if (!deactivateTarget) return;
    setDeactivating(true);
    try {
      await deactivateActor(deactivateTarget.actor_id);
      setToast({ message: "Actor deactivated", variant: "success" });
      setDeactivateTarget(null);
      loadData();
    } catch {
      setToast({ message: "Failed to deactivate actor", variant: "error" });
    } finally {
      setDeactivating(false);
    }
  }

  function togglePerm(perm: string) {
    setNewRolePerms((prev) =>
      prev.includes(perm) ? prev.filter((p) => p !== perm) : [...prev, perm],
    );
  }

  return (
    <AppShell>
      <PageHeader title="Users & Roles" description="Manage actors, roles, and permissions" />

      {/* Actors */}
      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Actors</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : actors.length === 0 ? (
            <EmptyState title="No actors found" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Actor ID</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Display Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {actors.map((a) => (
                  <TableRow key={a.actor_id}>
                    <TableCell className="font-mono text-sm">{a.actor_id.slice(0, 12)}...</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{a.actor_type}</Badge>
                    </TableCell>
                    <TableCell>{a.display_name || "\u2014"}</TableCell>
                    <TableCell>
                      <Badge variant={a.status === "ACTIVE" ? "success" : "destructive"}>
                        {a.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => { setAssignTarget(a); setAssignRoleId(""); }}
                        >
                          Assign Role
                        </Button>
                        {a.status === "ACTIVE" && (
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => setDeactivateTarget(a)}
                          >
                            Deactivate
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Roles */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Roles</CardTitle>
          <Button size="sm" onClick={() => setShowCreateRole(true)}>
            Create Role
          </Button>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : roles.length === 0 ? (
            <EmptyState title="No roles found" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Role Name</TableHead>
                  <TableHead>Permissions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {roles.map((r) => (
                  <TableRow key={r.role_id}>
                    <TableCell className="font-medium">{r.name}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {(r.permissions || []).map((p) => (
                          <Badge key={p} variant="outline" className="text-xs">{p}</Badge>
                        ))}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Role Dialog */}
      <FormDialog
        open={showCreateRole}
        onClose={() => setShowCreateRole(false)}
        title="Create Custom Role"
        description="Define a new role with specific permissions"
        onSubmit={handleCreateRole}
        submitLabel="Create Role"
        loading={savingRole}
        wide
      >
        <div>
          <Label htmlFor="roleName">Role Name</Label>
          <Input
            id="roleName"
            value={newRoleName}
            onChange={(e) => setNewRoleName(e.target.value)}
            placeholder="e.g. SUPERVISOR"
            required
          />
        </div>
        <div>
          <Label>Permissions</Label>
          <p className="mb-2 text-xs text-neutral-400">Select one or more permissions</p>
          <div className="grid grid-cols-2 gap-2">
            {VALID_PERMISSIONS.map((perm) => (
              <label
                key={perm}
                className="flex cursor-pointer items-center gap-2 rounded border border-bos-silver/30 px-3 py-2 text-sm hover:bg-bos-purple-light/20"
              >
                <input
                  type="checkbox"
                  checked={newRolePerms.includes(perm)}
                  onChange={() => togglePerm(perm)}
                  className="rounded"
                />
                {perm}
              </label>
            ))}
          </div>
        </div>
      </FormDialog>

      {/* Assign Role Dialog */}
      <FormDialog
        open={!!assignTarget}
        onClose={() => setAssignTarget(null)}
        title="Assign Role"
        description={`Assign a role to ${assignTarget?.display_name || assignTarget?.actor_id || ""}`}
        onSubmit={handleAssignRole}
        submitLabel="Assign"
        loading={assigningRole}
      >
        <div>
          <Label htmlFor="roleSelect">Select Role</Label>
          <Select
            id="roleSelect"
            value={assignRoleId}
            onChange={(e) => setAssignRoleId(e.target.value)}
            required
          >
            <option value="">-- Select a role --</option>
            {roles.map((r) => (
              <option key={r.role_id} value={r.role_id}>{r.name}</option>
            ))}
          </Select>
        </div>
      </FormDialog>

      {/* Deactivate Confirmation */}
      <ConfirmDialog
        open={!!deactivateTarget}
        onClose={() => setDeactivateTarget(null)}
        onConfirm={handleDeactivate}
        title="Deactivate Actor"
        description={`Are you sure you want to deactivate "${deactivateTarget?.display_name || deactivateTarget?.actor_id}"? They will lose access.`}
        confirmLabel="Deactivate"
        confirmVariant="destructive"
        loading={deactivating}
      />

      {toast && (
        <Toast
          message={toast.message}
          variant={toast.variant}
          onClose={() => setToast(null)}
        />
      )}
    </AppShell>
  );
}
