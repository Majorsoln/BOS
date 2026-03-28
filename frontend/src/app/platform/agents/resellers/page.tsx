"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Button, Card, CardContent, CardHeader, CardTitle,
  Input, Select, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui";
import { getAgents, registerAgent, suspendAgent, reinstateAgent, terminateAgent } from "@/lib/api/agents";
import { REGIONS, PAYOUT_METHODS } from "@/lib/constants";
import {
  Users, UserPlus, Award, TrendingUp, Search,
  MoreVertical, Pause, Play, XCircle,
} from "lucide-react";

type ToastState = { message: string; variant: "success" | "error" } | null;

export default function ResellersPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showRegister, setShowRegister] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);

  // Form state
  const [form, setForm] = useState({
    agent_name: "", contact_email: "", contact_phone: "",
    contact_person: "", payout_method: "MPESA", payout_phone: "",
    region_codes: [] as string[],
  });

  const query = useQuery({
    queryKey: ["saas", "agents", "RESELLER"],
    queryFn: () => getAgents({ type: "RESELLER" }),
  });

  const registerMut = useMutation({
    mutationFn: () => registerAgent({
      ...form,
      agent_type: "RESELLER",
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saas", "agents"] });
      setShowRegister(false);
      setForm({ agent_name: "", contact_email: "", contact_phone: "", contact_person: "", payout_method: "MPESA", payout_phone: "", region_codes: [] });
      setToast({ message: "Reseller registered successfully", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to register reseller", variant: "error" }),
  });

  const suspendMut = useMutation({
    mutationFn: (id: string) => suspendAgent({ agent_id: id, reason: "Suspended by admin" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "agents"] }); setToast({ message: "Reseller suspended", variant: "success" }); },
  });

  const reinstateMut = useMutation({
    mutationFn: (id: string) => reinstateAgent({ agent_id: id }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "agents"] }); setToast({ message: "Reseller reinstated", variant: "success" }); },
  });

  const terminateMut = useMutation({
    mutationFn: (id: string) => terminateAgent({ agent_id: id, reason: "Terminated by admin" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["saas", "agents"] }); setToast({ message: "Reseller terminated", variant: "success" }); },
  });

  const list: Array<{
    agent_id: string; agent_name: string; contact_email: string;
    contact_phone: string; status: string; tier: string;
    commission_rate: string; active_tenant_count: number;
    total_commission_earned: string; pending_commission: string;
    region_codes: string[];
  }> = query.data?.data ?? [];

  const filtered = list.filter((a) => {
    if (statusFilter && a.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return a.agent_name.toLowerCase().includes(q) || a.contact_email.toLowerCase().includes(q);
    }
    return true;
  });

  const activeCount = list.filter((a) => a.status === "ACTIVE").length;
  const totalTenants = list.reduce((s, a) => s + (a.active_tenant_count || 0), 0);
  const bronzeCount = list.filter((a) => a.tier === "BRONZE" && a.status === "ACTIVE").length;
  const silverGoldCount = list.filter((a) => (a.tier === "SILVER" || a.tier === "GOLD") && a.status === "ACTIVE").length;

  return (
    <div>
      <PageHeader
        title="Resellers (Wakala wa BOS)"
        description="Referral partners who earn commission by connecting businesses to BOS"
        action={<Button onClick={() => setShowRegister(true)}><UserPlus className="mr-2 h-4 w-4" /> Register Reseller</Button>}
      />

      {toast && (
        <div className={`mb-4 rounded-md p-3 text-sm ${toast.variant === "success" ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}>
          {toast.message}
          <button onClick={() => setToast(null)} className="ml-2 font-bold">x</button>
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active Resellers" value={activeCount} icon={Users} />
        <StatCard title="Total Tenants" value={totalTenants} icon={TrendingUp} />
        <StatCard title="Bronze Tier" value={bronzeCount} icon={Award} description="0-10 tenants, 10%" />
        <StatCard title="Silver/Gold Tier" value={silverGoldCount} icon={Award} description="11+ tenants, 15-20%" />
      </div>

      {/* Doctrine */}
      <Card className="mb-6 border-amber-200 bg-amber-50">
        <CardContent className="p-4">
          <h3 className="text-sm font-semibold text-amber-900">Reseller (Wakala) Doctrine</h3>
          <ul className="mt-2 space-y-1 text-xs text-amber-800">
            <li>Resellers earn commission by referring businesses to BOS</li>
            <li>Tier auto-upgrades: Bronze (0-10, 10%) &rarr; Silver (11-50, 15%) &rarr; Gold (51+, 20%)</li>
            <li>90-day churn clawback: if tenant cancels within 90 days, commission reversed</li>
            <li>Resellers do NOT provide L1 support or manage compliance (that&apos;s RLA&apos;s role)</li>
            <li>Payouts: Monthly for Bronze/Silver, Weekly for Gold</li>
          </ul>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-bos-silver-dark" />
          <Input placeholder="Search by name or email..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-36">
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="SUSPENDED">Suspended</option>
          <option value="TERMINATED">Terminated</option>
        </Select>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <EmptyState title="No resellers found" description="Register a new reseller to get started" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Reseller</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Regions</TableHead>
                  <TableHead className="text-center">Tenants</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Commission Rate</TableHead>
                  <TableHead className="text-right">Earned</TableHead>
                  <TableHead className="text-right">Pending</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((a) => (
                  <TableRow key={a.agent_id}>
                    <TableCell>
                      <p className="font-medium">{a.agent_name}</p>
                      <p className="text-xs text-bos-silver-dark">{a.contact_email}</p>
                    </TableCell>
                    <TableCell>
                      <Badge variant={a.tier === "GOLD" ? "warning" : a.tier === "SILVER" ? "outline" : "secondary"}>
                        {a.tier}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {a.region_codes.map((rc) => (
                          <Badge key={rc} variant="outline" className="text-xs">{rc}</Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-center font-mono">{a.active_tenant_count}</TableCell>
                    <TableCell className="text-center"><StatusBadge status={a.status} /></TableCell>
                    <TableCell className="text-right font-mono">{(parseFloat(a.commission_rate) * 100).toFixed(0)}%</TableCell>
                    <TableCell className="text-right font-mono text-sm">{parseFloat(a.total_commission_earned).toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{parseFloat(a.pending_commission).toLocaleString()}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {a.status === "ACTIVE" && (
                          <button onClick={() => suspendMut.mutate(a.agent_id)} className="rounded p-1 hover:bg-gray-100" title="Suspend">
                            <Pause className="h-4 w-4 text-amber-600" />
                          </button>
                        )}
                        {a.status === "SUSPENDED" && (
                          <button onClick={() => reinstateMut.mutate(a.agent_id)} className="rounded p-1 hover:bg-gray-100" title="Reinstate">
                            <Play className="h-4 w-4 text-green-600" />
                          </button>
                        )}
                        {a.status !== "TERMINATED" && (
                          <button onClick={() => terminateMut.mutate(a.agent_id)} className="rounded p-1 hover:bg-gray-100" title="Terminate">
                            <XCircle className="h-4 w-4 text-red-600" />
                          </button>
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

      {/* Register Dialog */}
      <Dialog open={showRegister} onOpenChange={setShowRegister}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Register New Reseller</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Company / Reseller Name" value={form.agent_name} onChange={(e) => setForm({ ...form, agent_name: e.target.value })} />
            <Input placeholder="Contact Person" value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
            <Input placeholder="Email" type="email" value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} />
            <Input placeholder="Phone" value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
            <div>
              <label className="mb-1 block text-sm font-medium">Payout Method</label>
              <Select value={form.payout_method} onChange={(e) => setForm({ ...form, payout_method: e.target.value })}>
                {PAYOUT_METHODS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </Select>
            </div>
            {form.payout_method === "MPESA" && (
              <Input placeholder="M-Pesa Phone Number" value={form.payout_phone} onChange={(e) => setForm({ ...form, payout_phone: e.target.value })} />
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRegister(false)}>Cancel</Button>
            <Button onClick={() => registerMut.mutate()} disabled={!form.agent_name || !form.contact_email || registerMut.isPending}>
              {registerMut.isPending ? "Registering..." : "Register Reseller"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
