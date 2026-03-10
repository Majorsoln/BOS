"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { Button, Card, CardContent, Input, Label, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge } from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import { listCustomers, createCustomer } from "@/lib/api/admin";
import type { CustomerProfile } from "@/types/api";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<CustomerProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ display_name: "", phone: "", email: "", address: "" });
  const [saving, setSaving] = useState(false);

  function loadCustomers() {
    listCustomers()
      .then((res) => setCustomers(res.customers || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadCustomers(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await createCustomer(form);
      setForm({ display_name: "", phone: "", email: "", address: "" });
      setShowForm(false);
      loadCustomers();
    } catch {
      alert("Failed to create customer");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Customers"
        description="Manage customer profiles"
        actions={
          <Button onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "New Customer"}
          </Button>
        }
      />

      {/* Create form */}
      {showForm && (
        <Card className="mb-6 max-w-xl">
          <CardContent className="pt-6">
            <form onSubmit={handleCreate} className="space-y-3">
              <div className="space-y-1">
                <Label>Name *</Label>
                <Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} required />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label>Phone</Label>
                  <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </div>
                <div className="space-y-1">
                  <Label>Email</Label>
                  <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
              </div>
              <div className="space-y-1">
                <Label>Address</Label>
                <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
              </div>
              <Button type="submit" disabled={saving}>{saving ? "Creating..." : "Create Customer"}</Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Customer list */}
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : customers.length === 0 ? (
            <EmptyState
              title="No customers yet"
              description="Create your first customer profile"
              action={<Button onClick={() => setShowForm(true)}>New Customer</Button>}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {customers.map((c) => (
                  <TableRow key={c.customer_id}>
                    <TableCell className="font-medium">{c.display_name}</TableCell>
                    <TableCell>{c.phone || "—"}</TableCell>
                    <TableCell>{c.email || "—"}</TableCell>
                    <TableCell>
                      <Badge variant={c.status === "ACTIVE" ? "success" : "secondary"}>{c.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
