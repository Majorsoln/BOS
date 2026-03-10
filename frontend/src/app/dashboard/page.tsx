"use client";

import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui";

const QUICK_ACTIONS = [
  { title: "Customers", description: "Manage customer profiles", href: "/customers", icon: "\u263A" },
  { title: "Documents", description: "View issued documents", href: "/documents", icon: "\u2630" },
  { title: "Business Settings", description: "Update business profile", href: "/settings/business", icon: "\u2302" },
  { title: "Users & Roles", description: "Manage access control", href: "/settings/users", icon: "\u26E8" },
  { title: "Tax Rules", description: "Configure tax rates", href: "/settings/tax-rules", icon: "%" },
  { title: "Data Migration", description: "Import from other systems", href: "/migration", icon: "\u21E7" },
];

export default function DashboardPage() {
  return (
    <AppShell>
      <PageHeader
        title="Dashboard"
        description="Welcome to your Business Operations Suite"
      />

      {/* KPI Cards — placeholder */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Total Sales", value: "--", sub: "Connect POS to track" },
          { label: "Documents", value: "--", sub: "Issued today" },
          { label: "Customers", value: "--", sub: "Active profiles" },
          { label: "Cash Balance", value: "--", sub: "Current session" },
        ].map((kpi) => (
          <Card key={kpi.label}>
            <CardHeader className="pb-2">
              <CardDescription>{kpi.label}</CardDescription>
              <CardTitle className="text-3xl">{kpi.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-neutral-400">{kpi.sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

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
