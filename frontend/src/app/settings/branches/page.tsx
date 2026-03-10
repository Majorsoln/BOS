"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge } from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import { listBranches } from "@/lib/api/admin";
import type { Branch } from "@/types/api";

export default function BranchesPage() {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listBranches()
      .then((res) => setBranches(res.branches || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <PageHeader title="Branches" description="Manage your business locations" />
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : branches.length === 0 ? (
            <EmptyState title="No branches found" description="Branches are created during business bootstrap" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Branch ID</TableHead>
                  <TableHead>Timezone</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {branches.map((b) => (
                  <TableRow key={b.branch_id}>
                    <TableCell className="font-medium">{b.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">{b.branch_id}</Badge>
                    </TableCell>
                    <TableCell>{b.timezone || "UTC"}</TableCell>
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
