"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, CardHeader, CardTitle, Badge, Button, Input, Select,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui";
import { UsersRound, UserPlus, Shield, Phone, Mail } from "lucide-react";

type StaffMember = {
  id: string;
  name: string;
  email: string;
  phone: string;
  role: string;
  status: string;
  joined_at: string;
};

const STAFF_ROLES = [
  { value: "OFFICE_MANAGER", label: "Office Manager — Meneja wa Ofisi" },
  { value: "SALES_REP", label: "Sales Representative — Mwakilishi wa Mauzo" },
  { value: "SUPPORT_AGENT", label: "Support Agent — Wakala wa Msaada" },
  { value: "ACCOUNTANT", label: "Accountant — Mhasibu" },
  { value: "FIELD_AGENT", label: "Field Agent — Wakala wa Shambani" },
  { value: "TRAINER", label: "Trainer — Mkufunzi" },
];

export default function StaffPage() {
  const [showAddStaff, setShowAddStaff] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newRole, setNewRole] = useState("SALES_REP");

  // TODO: Wire to backend API when staff management endpoint exists
  const [staff] = useState<StaffMember[]>([]);

  const activeStaff = staff.filter((s) => s.status === "ACTIVE");
  const roleCount = new Set(activeStaff.map((s) => s.role)).size;

  return (
    <div>
      <PageHeader
        title="Staff Management — Wafanyakazi"
        description="Manage your office team. Assign roles and track who handles what."
        action={
          <Button onClick={() => setShowAddStaff(true)}>
            <UserPlus className="mr-1 h-4 w-4" /> Add Staff
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Total Staff" value={staff.length} icon={UsersRound} />
        <StatCard title="Active" value={activeStaff.length} icon={UsersRound} />
        <StatCard title="Roles" value={roleCount} icon={Shield} />
        <StatCard title="Field Agents" value={staff.filter((s) => s.role === "FIELD_AGENT").length} icon={UsersRound} />
      </div>

      {/* Role Descriptions */}
      <Card className="mt-4 border-blue-200/50 bg-blue-50/30 dark:border-blue-800/30 dark:bg-blue-950/20">
        <CardContent className="pt-6">
          <p className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">Majukumu ya Wafanyakazi — Staff Roles</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {STAFF_ROLES.map((r) => (
              <div key={r.value} className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                <p className="text-xs font-medium text-neutral-800 dark:text-neutral-200">{r.label}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Staff Table */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-sm">All Staff ({staff.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {staff.length === 0 ? (
            <EmptyState
              title="No staff added yet"
              description="Add your team members to manage operations. Sales reps, support agents, field agents, and more."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead>Joined</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {staff.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.name}</TableCell>
                    <TableCell>
                      <Badge variant="purple">
                        {STAFF_ROLES.find((r) => r.value === s.role)?.label.split("—")[0].trim() || s.role}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{s.email}</TableCell>
                    <TableCell className="text-xs">{s.phone}</TableCell>
                    <TableCell className="text-center"><StatusBadge status={s.status} /></TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{s.joined_at}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add Staff Dialog */}
      <Dialog open={showAddStaff} onOpenChange={setShowAddStaff}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add Staff Member — Ongeza Mfanyakazi</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input placeholder="Full name" value={newName} onChange={(e) => setNewName(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium">Email</label>
              <Input type="email" placeholder="email@example.com" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium">Phone</label>
              <Input placeholder="+254 7XX XXX XXX" value={newPhone} onChange={(e) => setNewPhone(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium">Role</label>
              <Select value={newRole} onChange={(e) => setNewRole(e.target.value)}>
                {STAFF_ROLES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddStaff(false)}>Cancel</Button>
            <Button disabled={!newName || !newEmail}>Add Staff</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
