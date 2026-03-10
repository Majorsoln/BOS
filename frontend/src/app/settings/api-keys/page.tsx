"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { Button, Card, CardContent, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge } from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import { listApiKeys, revokeApiKey } from "@/lib/api/admin";
import type { ApiKeyRecord } from "@/types/api";
import { formatDateTime } from "@/lib/utils";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [loading, setLoading] = useState(true);

  function loadKeys() {
    listApiKeys()
      .then((res) => setKeys(res.api_keys || res.keys || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadKeys(); }, []);

  async function handleRevoke(keyId: string) {
    if (!confirm("Revoke this API key? This cannot be undone.")) return;
    try {
      await revokeApiKey(keyId);
      loadKeys();
    } catch {
      alert("Failed to revoke key");
    }
  }

  return (
    <AppShell>
      <PageHeader title="API Keys" description="Manage API credentials for your business" />
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : keys.length === 0 ? (
            <EmptyState title="No API keys found" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Key ID</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((k) => (
                  <TableRow key={k.key_id}>
                    <TableCell className="font-mono text-xs">{k.key_id.slice(0, 12)}...</TableCell>
                    <TableCell>{k.actor_id}</TableCell>
                    <TableCell><Badge variant="secondary">{k.actor_type}</Badge></TableCell>
                    <TableCell>
                      <Badge variant={k.status === "ACTIVE" ? "success" : "destructive"}>
                        {k.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{formatDateTime(k.created_at)}</TableCell>
                    <TableCell className="text-right">
                      {k.status === "ACTIVE" && (
                        <Button variant="destructive" size="sm" onClick={() => handleRevoke(k.key_id)}>
                          Revoke
                        </Button>
                      )}
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
