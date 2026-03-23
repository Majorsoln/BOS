"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Card, CardHeader, CardTitle, CardContent, CardDescription, Badge, Skeleton } from "@/components/ui";
import { listDocuments, listCustomers } from "@/lib/api/admin";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import { DollarSign, FileText, Users, Wallet } from "lucide-react";

const QUICK_ACTIONS = [
  { title: "Customers", description: "Manage customer profiles", href: "/customers", icon: "\u263A" },
  { title: "Documents", description: "View issued documents", href: "/documents", icon: "\u2630" },
  { title: "Business Settings", description: "Update business profile", href: "/settings/business", icon: "\u2302" },
  { title: "Users & Roles", description: "Manage access control", href: "/settings/users", icon: "\u26E8" },
  { title: "Tax Rules", description: "Configure tax rates", href: "/settings/tax-rules", icon: "%" },
  { title: "Data Migration", description: "Import from other systems", href: "/migration", icon: "\u21E7" },
];

interface DashboardKPIs {
  totalDocuments: number;
  todayDocuments: number;
  totalCustomers: number;
  recentDocuments: Array<{
    document_id: string;
    document_type: string;
    document_number: string;
    issued_at: string;
  }>;
}

export default function DashboardPage() {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const today = new Date().toISOString().split("T")[0];

    Promise.all([listDocuments(), listCustomers()])
      .then(([docsRes, custRes]) => {
        const docs = docsRes.documents || [];
        const customers = custRes.customers || [];
        const todayDocs = docs.filter(
          (d: { issued_at?: string }) => d.issued_at && d.issued_at.startsWith(today),
        );

        setKpis({
          totalDocuments: docs.length,
          todayDocuments: todayDocs.length,
          totalCustomers: customers.length,
          recentDocuments: docs.slice(0, 8),
        });
      })
      .catch(() => {
        setKpis({
          totalDocuments: 0,
          todayDocuments: 0,
          totalCustomers: 0,
          recentDocuments: [],
        });
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <PageHeader
        title="Dashboard"
        description="Welcome to your Business Operations Suite"
      />

      {/* KPI Cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading ? (
          <>
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-28 rounded-lg" />
            ))}
          </>
        ) : (
          <>
            <StatCard
              title="Documents Issued"
              value={kpis?.totalDocuments ?? 0}
              icon={FileText}
              description={`${kpis?.todayDocuments ?? 0} issued today`}
            />
            <StatCard
              title="Customers"
              value={kpis?.totalCustomers ?? 0}
              icon={Users}
              description="Active profiles"
            />
            <StatCard
              title="Today's Documents"
              value={kpis?.todayDocuments ?? 0}
              icon={DollarSign}
              description="Issued today"
            />
            <StatCard
              title="Cash Balance"
              value="--"
              icon={Wallet}
              description="Open a cash session to track"
            />
          </>
        )}
      </div>

      {/* Recent Documents */}
      <Card className="mb-8">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Documents</CardTitle>
            <CardDescription>Latest issued documents</CardDescription>
          </div>
          <Link href="/documents">
            <span className="text-sm text-bos-purple hover:underline">View all</span>
          </Link>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 rounded" />
              ))}
            </div>
          ) : !kpis?.recentDocuments.length ? (
            <p className="text-sm text-neutral-400">No documents issued yet</p>
          ) : (
            <div className="space-y-2">
              {kpis.recentDocuments.map((doc) => (
                <div
                  key={doc.document_id}
                  className="flex items-center justify-between rounded-lg border border-bos-silver/20 px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant="purple" className="text-xs">
                      {doc.document_type.replace(/_/g, " ")}
                    </Badge>
                    <span className="font-mono text-sm">{doc.document_number || doc.document_id.slice(0, 12)}</span>
                  </div>
                  <span className="text-xs text-neutral-400">
                    {formatDateTime(doc.issued_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <h2 className="mb-4 text-lg font-semibold">Quick Actions</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {QUICK_ACTIONS.map((action) => (
          <Link key={action.href} href={action.href}>
            <Card className="cursor-pointer transition-shadow hover:shadow-md">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{action.icon}</span>
                  <div>
                    <CardTitle className="text-base">{action.title}</CardTitle>
                    <CardDescription>{action.description}</CardDescription>
                  </div>
                </div>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </AppShell>
  );
}
