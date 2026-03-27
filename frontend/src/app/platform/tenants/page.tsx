"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, Input, Select, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getSubscriptions } from "@/lib/api/saas";
import { formatDate } from "@/lib/utils";
import { Users, UserCheck, Clock, XCircle, Search } from "lucide-react";

type ToastState = { message: string; variant: "success" | "error" } | null;

export default function TenantsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const subs = useQuery({
    queryKey: ["saas", "subscriptions", statusFilter],
    queryFn: () => getSubscriptions({ status: statusFilter || undefined }),
  });

  const allTenants: Array<{
    subscription_id: string;
    business_id: string;
    business_name?: string;
    combo_id?: string;
    services?: string;
    status: string;
    activated_at?: string;
    billing_starts_at?: string;
    region_code?: string;
    monthly_amount?: number;
    currency?: string;
    renewal_count?: number;
    created_at?: string;
  }> = subs.data?.data ?? [];

  const filtered = allTenants.filter((t) => {
    if (search) {
      const q = search.toLowerCase();
      return (
        (t.business_id ?? "").toLowerCase().includes(q) ||
        (t.business_name ?? "").toLowerCase().includes(q) ||
        (t.combo_id ?? "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const activeCount = allTenants.filter((t) => t.status === "ACTIVE").length;
  const trialCount = allTenants.filter((t) => t.status === "TRIAL").length;
  const cancelledCount = allTenants.filter((t) => t.status === "CANCELLED").length;

  return (
    <div>
      <PageHeader
        title="All Tenants"
        description="Browse and manage all registered tenants across all regions"
      />

      {/* Stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Total Tenants" value={allTenants.length} icon={Users} />
        <StatCard title="Active (Paying)" value={activeCount} icon={UserCheck} />
        <StatCard title="On Trial" value={trialCount} icon={Clock} />
        <StatCard title="Cancelled" value={cancelledCount} icon={XCircle} />
      </div>

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-bos-silver-dark" />
          <Input
            placeholder="Search by Business ID, name, or combo..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
          <option value="">All Statuses</option>
          <option value="TRIAL">Trial</option>
          <option value="ACTIVE">Active</option>
          <option value="CANCELLED">Cancelled</option>
          <option value="SUSPENDED">Suspended</option>
        </Select>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <EmptyState
              title="No tenants found"
              description={search ? "Try adjusting your search or filters" : "No tenants registered yet"}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Business</TableHead>
                  <TableHead>Combo / Services</TableHead>
                  <TableHead>Region</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead>Billing Starts</TableHead>
                  <TableHead className="text-right">Monthly</TableHead>
                  <TableHead className="text-right">Renewals</TableHead>
                  <TableHead>Registered</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((t) => (
                  <TableRow key={t.subscription_id || t.business_id}>
                    <TableCell>
                      <p className="font-medium">{t.business_name || "—"}</p>
                      <p className="font-mono text-xs text-bos-silver-dark">{t.business_id}</p>
                    </TableCell>
                    <TableCell>
                      {t.combo_id ? (
                        <Badge variant="purple">{t.combo_id}</Badge>
                      ) : (
                        <span className="text-sm text-bos-silver-dark">{t.services || "—"}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {t.region_code ? (
                        <Badge variant="outline">{t.region_code}</Badge>
                      ) : (
                        <span className="text-bos-silver-dark">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <StatusBadge status={t.status} />
                    </TableCell>
                    <TableCell className="text-sm text-bos-silver-dark">
                      {t.billing_starts_at ? formatDate(t.billing_starts_at) : "—"}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {t.monthly_amount != null
                        ? `${t.currency ?? ""} ${t.monthly_amount.toLocaleString()}`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {t.renewal_count ?? 0}
                    </TableCell>
                    <TableCell className="text-sm text-bos-silver-dark">
                      {formatDate(t.created_at || t.activated_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
