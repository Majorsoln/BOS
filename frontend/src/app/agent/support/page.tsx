"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
} from "@/components/ui";
import { getMySupportTickets, createSupportTicket, escalateTicket, getMyTenants } from "@/lib/api/agents";
import { SUPPORT_CATEGORIES, SUPPORT_PRIORITIES } from "@/lib/constants";
import { LifeBuoy, Plus, ArrowUpCircle } from "lucide-react";

export default function AgentSupportPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [escalateId, setEscalateId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const tickets = useQuery({
    queryKey: ["agent", "support", statusFilter],
    queryFn: () => getMySupportTickets({ status: statusFilter || undefined }),
  });
  const tenants = useQuery({ queryKey: ["agent", "tenants"], queryFn: () => getMyTenants() });

  const createMut = useMutation({
    mutationFn: createSupportTicket,
    onSuccess: () => { setShowCreate(false); qc.invalidateQueries({ queryKey: ["agent", "support"] }); setToast({ message: "Ticket created", variant: "success" }); },
    onError: () => setToast({ message: "Failed to create ticket", variant: "error" }),
  });

  const escalateMut = useMutation({
    mutationFn: escalateTicket,
    onSuccess: () => { setEscalateId(null); qc.invalidateQueries({ queryKey: ["agent", "support"] }); setToast({ message: "Ticket escalated to L2", variant: "success" }); },
    onError: () => setToast({ message: "Failed to escalate", variant: "error" }),
  });

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    createMut.mutate({
      tenant_id: d.get("tenant_id") as string,
      category: d.get("category") as string,
      subject: d.get("subject") as string,
      description: d.get("description") as string,
      priority: d.get("priority") as string,
    });
  }

  function handleEscalate(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    escalateMut.mutate({ ticket_id: escalateId!, reason: d.get("reason") as string });
  }

  const ticketList = tickets.data?.data ?? [];
  const tenantList = tenants.data?.data ?? [];

  return (
    <div>
      <PageHeader
        title="Support Tickets"
        description="L1 support for your tenants — escalate to platform when needed"
        actions={
          <Button onClick={() => setShowCreate(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            New Ticket
          </Button>
        }
      />

      <div className="mb-4">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="ESCALATED">Escalated</option>
          <option value="RESOLVED">Resolved</option>
          <option value="CLOSED">Closed</option>
        </Select>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <LifeBuoy className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Tickets</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Ticket</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Subject</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Priority</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Created</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Actions</th>
                </tr>
              </thead>
              <tbody>
                {ticketList.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-bos-silver-dark">
                    <LifeBuoy className="mx-auto mb-2 h-5 w-5" />
                    No support tickets
                  </td></tr>
                )}
                {ticketList.map((t: {
                  ticket_id: string; subject: string; category: string;
                  priority: string; status: string; created_at: string;
                  tenant_name?: string;
                }) => (
                  <tr key={t.ticket_id} className="border-b border-bos-silver/10 hover:bg-bos-silver-light/50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-3 font-mono text-xs">{t.ticket_id.slice(0, 8)}...</td>
                    <td className="px-4 py-3 font-medium">
                      {t.subject}
                      {t.tenant_name && <span className="ml-1 text-xs text-bos-silver-dark">({t.tenant_name})</span>}
                    </td>
                    <td className="px-4 py-3"><Badge variant="outline">{t.category}</Badge></td>
                    <td className="px-4 py-3"><StatusBadge status={t.priority} /></td>
                    <td className="px-4 py-3"><StatusBadge status={t.status} /></td>
                    <td className="px-4 py-3 text-bos-silver-dark">{t.created_at?.slice(0, 10)}</td>
                    <td className="px-4 py-3 text-right">
                      {(t.status === "OPEN" || t.status === "IN_PROGRESS") && (
                        <Button size="sm" variant="outline" onClick={() => setEscalateId(t.ticket_id)} className="gap-1">
                          <ArrowUpCircle className="h-3 w-3" />
                          Escalate
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Create Ticket Dialog */}
      <FormDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="New Support Ticket"
        description="Create an L1 support ticket for a tenant issue."
        onSubmit={handleCreate}
        submitLabel="Create Ticket"
        loading={createMut.isPending}
      >
        <div>
          <Label htmlFor="st_tenant">Tenant</Label>
          <Select id="st_tenant" name="tenant_id" required className="mt-1">
            <option value="">Select tenant...</option>
            {tenantList.map((t: { tenant_id: string; business_name: string }) => (
              <option key={t.tenant_id} value={t.tenant_id}>{t.business_name}</option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="st_category">Category</Label>
          <Select id="st_category" name="category" required className="mt-1">
            {SUPPORT_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="st_priority">Priority</Label>
          <Select id="st_priority" name="priority" required className="mt-1">
            {SUPPORT_PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="st_subject">Subject</Label>
          <Input id="st_subject" name="subject" required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="st_desc">Description</Label>
          <Input id="st_desc" name="description" required className="mt-1" placeholder="Describe the issue in detail" />
        </div>
      </FormDialog>

      {/* Escalate Dialog */}
      <FormDialog
        open={!!escalateId}
        onClose={() => setEscalateId(null)}
        title="Escalate to L2"
        description="Escalate this ticket to the platform support team."
        onSubmit={handleEscalate}
        submitLabel="Escalate"
        loading={escalateMut.isPending}
      >
        <div>
          <Label htmlFor="esc_reason">Escalation Reason</Label>
          <Input id="esc_reason" name="reason" required className="mt-1" placeholder="Why does this need platform intervention?" />
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
