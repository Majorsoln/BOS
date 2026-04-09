"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, CardHeader, CardTitle, Badge, Button,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
  Input, Label, Select, Toast,
} from "@/components/ui";
import {
  getPlatformAdmins, addPlatformAdmin, updatePlatformAdminRole,
  suspendPlatformAdmin, reinstatePlatformAdmin,
} from "@/lib/api/platform";
import { usePlatformAuthStore, ROLE_LABELS } from "@/stores/platform-auth-store";
import type { PlatformAdminRole } from "@/stores/platform-auth-store";
import { UserCog, ShieldCheck, Eye, AlertTriangle, UserPlus, Lock } from "lucide-react";

type ToastState = { message: string; variant: "success" | "error" } | null;

const ROLE_OPTIONS: { value: PlatformAdminRole; label: string; desc: string }[] = [
  { value: "SUPER_ADMIN", label: "Super Admin", desc: "Full access — all sections, all actions" },
  { value: "FINANCE_ADMIN", label: "Finance Admin", desc: "Finance, rates, subscriptions, audit" },
  { value: "AGENT_MANAGER", label: "Agent Manager", desc: "Agents, tenants, promotions, escalations" },
  { value: "COMPLIANCE_OFFICER", label: "Compliance Officer", desc: "Compliance, regions, governance, audit" },
  { value: "VIEWER", label: "Viewer", desc: "Dashboard and audit log — read only" },
];

const ROLE_ICON_COLORS: Record<PlatformAdminRole, string> = {
  SUPER_ADMIN: "bg-bos-purple-light text-bos-purple",
  FINANCE_ADMIN: "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400",
  AGENT_MANAGER: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400",
  COMPLIANCE_OFFICER: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
  VIEWER: "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
};

export default function PlatformAdminsPage() {
  const { role: currentRole, can } = usePlatformAuthStore();
  const [toast, setToast] = useState<ToastState>(null);
  const [showAddForm, setShowAddForm] = useState(false);

  // Only SUPER_ADMIN can access this page
  if (!can("admins")) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <Lock className="h-12 w-12 text-bos-silver" />
        <h2 className="text-lg font-semibold">Access Restricted</h2>
        <p className="text-sm text-bos-silver-dark">
          Only Super Admins can manage platform admin users.
        </p>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Platform Admins"
        description="Manage who can access the platform admin portal and at what level."
      />

      {/* Role matrix reference */}
      <Card className="mb-6 border-bos-purple/20 bg-bos-purple-light/30 dark:border-bos-purple/10 dark:bg-bos-purple-light/10">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 text-bos-purple" />
            <div className="text-sm">
              <p className="font-semibold text-bos-purple">Role Permissions Matrix</p>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-5">
                {ROLE_OPTIONS.map((r) => (
                  <div key={r.value} className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                    <Badge className={`mb-1 text-[10px] ${ROLE_ICON_COLORS[r.value]}`}>{r.label}</Badge>
                    <p className="text-xs text-bos-silver-dark">{r.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Add Admin form (toggled) */}
      {showAddForm ? (
        <AddAdminForm
          onSuccess={() => { setShowAddForm(false); setToast({ message: "Admin added", variant: "success" }); }}
          onCancel={() => setShowAddForm(false)}
          onError={(msg) => setToast({ message: msg, variant: "error" })}
          currentUserRole={currentRole}
        />
      ) : (
        <div className="mb-4 flex justify-end">
          <Button onClick={() => setShowAddForm(true)} className="gap-2">
            <UserPlus className="h-4 w-4" /> Add Platform Admin
          </Button>
        </div>
      )}

      <AdminsTable
        onToast={setToast}
        currentRole={currentRole}
      />

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

/* ── Add Admin Form ──────────────────────────────────────── */
function AddAdminForm({
  onSuccess, onCancel, onError, currentUserRole,
}: {
  onSuccess: () => void;
  onCancel: () => void;
  onError: (msg: string) => void;
  currentUserRole: PlatformAdminRole;
}) {
  const qc = useQueryClient();
  const mut = useMutation({
    mutationFn: addPlatformAdmin,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["platform", "admins"] }); onSuccess(); },
    onError: () => onError("Failed to add admin — check details and try again"),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    mut.mutate({
      name: String(d.get("name")),
      email: String(d.get("email")),
      role: String(d.get("role")) as PlatformAdminRole,
    });
  }

  // Non-super-admins cannot add super-admins
  const allowedRoles = currentUserRole === "SUPER_ADMIN"
    ? ROLE_OPTIONS
    : ROLE_OPTIONS.filter((r) => r.value !== "SUPER_ADMIN");

  return (
    <Card className="mb-6 border-bos-purple/30">
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <UserPlus className="h-4 w-4 text-bos-purple" /> New Platform Admin
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <Label>Full Name</Label>
            <Input name="name" required placeholder="e.g. Jane Mwangi" />
          </div>
          <div>
            <Label>Email Address</Label>
            <Input name="email" type="email" required placeholder="jane@company.com" />
          </div>
          <div>
            <Label>Role</Label>
            <Select name="role" defaultValue="VIEWER">
              {allowedRoles.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </Select>
          </div>
          <div className="flex gap-2 sm:col-span-3">
            <Button type="submit" disabled={mut.isPending}>
              {mut.isPending ? "Adding..." : "Add Admin"}
            </Button>
            <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

/* ── Admins Table ────────────────────────────────────────── */
function AdminsTable({
  onToast, currentRole,
}: {
  onToast: (t: { message: string; variant: "success" | "error" }) => void;
  currentRole: PlatformAdminRole;
}) {
  const qc = useQueryClient();
  const adminsQuery = useQuery({
    queryKey: ["platform", "admins"],
    queryFn: () => getPlatformAdmins(),
  });

  const updateRoleMut = useMutation({
    mutationFn: updatePlatformAdminRole,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["platform", "admins"] }); onToast({ message: "Role updated", variant: "success" }); },
    onError: () => onToast({ message: "Failed to update role", variant: "error" }),
  });

  const suspendMut = useMutation({
    mutationFn: (id: string) => suspendPlatformAdmin(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["platform", "admins"] }); onToast({ message: "Admin suspended", variant: "success" }); },
    onError: () => onToast({ message: "Failed to suspend", variant: "error" }),
  });

  const reinstateMut = useMutation({
    mutationFn: (id: string) => reinstatePlatformAdmin(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["platform", "admins"] }); onToast({ message: "Admin reinstated", variant: "success" }); },
    onError: () => onToast({ message: "Failed to reinstate", variant: "error" }),
  });

  type AdminRow = {
    admin_id: string; name: string; email: string;
    role: PlatformAdminRole; status: string;
    last_active_at: string | null;
  };

  const admins: AdminRow[] = adminsQuery.data?.data ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <UserCog className="h-5 w-5 text-bos-purple" />
          <CardTitle className="text-sm">Platform Admins ({admins.length})</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {admins.length === 0 ? (
          <EmptyState title="No platform admins" description="Add the first platform admin using the button above" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead className="text-center">Role</TableHead>
                <TableHead className="text-center">Status</TableHead>
                <TableHead>Last Active</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {admins.map((a) => (
                <TableRow key={a.admin_id}>
                  <TableCell className="font-medium">{a.name}</TableCell>
                  <TableCell className="text-xs text-bos-silver-dark">{a.email}</TableCell>
                  <TableCell className="text-center">
                    <Select
                      defaultValue={a.role}
                      disabled={currentRole !== "SUPER_ADMIN" || a.role === "SUPER_ADMIN"}
                      className="h-7 text-xs"
                      onChange={(e) => updateRoleMut.mutate({
                        admin_id: a.admin_id,
                        role: e.target.value as PlatformAdminRole,
                      })}
                    >
                      {ROLE_OPTIONS.map((r) => (
                        <option key={r.value} value={r.value}>{r.label}</option>
                      ))}
                    </Select>
                  </TableCell>
                  <TableCell className="text-center">
                    <StatusBadge status={a.status} />
                  </TableCell>
                  <TableCell className="text-xs text-bos-silver-dark">
                    {a.last_active_at
                      ? new Date(a.last_active_at).toLocaleDateString()
                      : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    {currentRole === "SUPER_ADMIN" && a.role !== "SUPER_ADMIN" && (
                      a.status === "ACTIVE" ? (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs text-amber-600 border-amber-300"
                          onClick={() => suspendMut.mutate(a.admin_id)}
                          disabled={suspendMut.isPending}
                        >
                          Suspend
                        </Button>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs text-green-600 border-green-300"
                          onClick={() => reinstateMut.mutate(a.admin_id)}
                          disabled={reinstateMut.isPending}
                        >
                          Reinstate
                        </Button>
                      )
                    )}
                    {a.role === "SUPER_ADMIN" && (
                      <span className="flex items-center justify-end gap-1 text-xs text-bos-silver-dark">
                        <Lock className="h-3 w-3" /> Protected
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
