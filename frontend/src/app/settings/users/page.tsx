"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge, Button } from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import { listActors, listRoles } from "@/lib/api/admin";
import type { Actor, Role } from "@/types/api";

export default function UsersPage() {
  const [actors, setActors] = useState<Actor[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([listActors(), listRoles()])
      .then(([actorsRes, rolesRes]) => {
        setActors(actorsRes.actors || []);
        setRoles(rolesRes.roles || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <PageHeader title="Users & Roles" description="Manage actors and role assignments" />

      {/* Actors */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Actors</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : actors.length === 0 ? (
            <EmptyState title="No actors found" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Actor ID</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Display Name</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {actors.map((a) => (
                  <TableRow key={a.actor_id}>
                    <TableCell className="font-mono text-sm">{a.actor_id}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{a.actor_type}</Badge>
                    </TableCell>
                    <TableCell>{a.display_name || "—"}</TableCell>
                    <TableCell>
                      <Badge variant={a.status === "ACTIVE" ? "success" : "destructive"}>
                        {a.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Roles */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Roles</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : roles.length === 0 ? (
            <EmptyState title="No roles found" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Role Name</TableHead>
                  <TableHead>Permissions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {roles.map((r) => (
                  <TableRow key={r.role_id}>
                    <TableCell className="font-medium">{r.name}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {(r.permissions || []).map((p) => (
                          <Badge key={p} variant="outline" className="text-xs">{p}</Badge>
                        ))}
                      </div>
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
