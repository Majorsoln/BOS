"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, Select, Badge } from "@/components/ui";
import { getMyTenants } from "@/lib/api/agents";
import { formatDate } from "@/lib/utils";
import { Users } from "lucide-react";

export default function MyTenantsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const tenants = useQuery({
    queryKey: ["agent", "tenants", statusFilter],
    queryFn: () => getMyTenants({ status: statusFilter || undefined }),
  });

  const tenantList = tenants.data?.data ?? [];

  return (
    <div>
      <PageHeader title="My Tenants" description="All tenants attributed to you" />

      <div className="mb-4">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
          <option value="">All Statuses</option>
          <option value="TRIAL">Trial</option>
          <option value="ACTIVE">Active</option>
          <option value="SUSPENDED">Suspended</option>
          <option value="CANCELLED">Cancelled</option>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Business</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Country</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Monthly</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Commission</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Onboarded</th>
                </tr>
              </thead>
              <tbody>
                {tenantList.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-bos-silver-dark">
                    <Users className="mx-auto mb-2 h-5 w-5" />
                    No tenants yet. Start by onboarding a new tenant.
                  </td></tr>
                )}
                {tenantList.map((t: {
                  tenant_id: string; business_name: string; business_type: string;
                  country: string; status: string; monthly_amount?: number;
                  commission_amount?: number; currency?: string; onboarded_at?: string;
                }) => (
                  <tr key={t.tenant_id} className="border-b border-bos-silver/10 hover:bg-bos-silver-light/50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-3 font-medium">{t.business_name}</td>
                    <td className="px-4 py-3"><Badge variant="outline">{t.business_type}</Badge></td>
                    <td className="px-4 py-3 text-bos-silver-dark">{t.country}</td>
                    <td className="px-4 py-3"><StatusBadge status={t.status} /></td>
                    <td className="px-4 py-3 text-right font-mono">{t.currency} {t.monthly_amount?.toLocaleString() ?? "—"}</td>
                    <td className="px-4 py-3 text-right font-mono text-bos-purple">{t.currency} {t.commission_amount?.toLocaleString() ?? "—"}</td>
                    <td className="px-4 py-3 text-bos-silver-dark">{formatDate(t.onboarded_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
