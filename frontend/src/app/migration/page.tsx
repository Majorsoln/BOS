"use client";

import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, Badge } from "@/components/ui";

const SUPPORTED_SOURCES = [
  "QuickBooks", "Xero", "Sage", "Odoo", "ERPNext",
  "Tally", "Wave", "Zoho Books", "FreshBooks",
  "CSV", "JSON", "Excel",
];

const ENTITY_TYPES = [
  { type: "CUSTOMER", description: "Import customer profiles with names, contacts, addresses" },
  { type: "SUPPLIER", description: "Import supplier records for procurement" },
  { type: "PRODUCT", description: "Import product catalog with SKUs and pricing" },
  { type: "OPENING_BALANCE", description: "Import account opening balances for accounting" },
  { type: "TRANSACTION", description: "Import historical transactions for reporting continuity" },
];

export default function MigrationPage() {
  return (
    <AppShell>
      <PageHeader
        title="Data Migration"
        description="Import data from other ERP systems into BOS (Hamisha Data)"
      />

      {/* Supported Sources */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Supported Source Systems</CardTitle>
          <CardDescription>We can import data from these platforms</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {SUPPORTED_SOURCES.map((s) => (
              <Badge key={s} variant="outline" className="text-sm">{s}</Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Entity Types */}
      <Card>
        <CardHeader>
          <CardTitle>What Can Be Imported</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {ENTITY_TYPES.map((e) => (
              <div key={e.type} className="flex items-start gap-3 rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
                <Badge variant="secondary" className="mt-0.5">{e.type}</Badge>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">{e.description}</p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-neutral-400">
            Use the API endpoints (<code>POST /admin/migration/create-job</code>, <code>POST /admin/migration/upload</code>) to programmatically import data.
            A full UI wizard is coming in a future release.
          </p>
        </CardContent>
      </Card>
    </AppShell>
  );
}
