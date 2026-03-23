"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Badge, Input, Label, Select, Toast,
} from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import { listApiKeys, createApiKey, revokeApiKey, listActors } from "@/lib/api/admin";
import { ACTOR_TYPES } from "@/lib/constants";
import { formatDateTime } from "@/lib/utils";
import type { ApiKeyRecord, Actor } from "@/types/api";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [actors, setActors] = useState<Actor[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  // Create key dialog
  const [showCreate, setShowCreate] = useState(false);
  const [newActorId, setNewActorId] = useState("");
  const [newActorType, setNewActorType] = useState("SYSTEM");
  const [saving, setSaving] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  // Revoke dialog
  const [revokeTarget, setRevokeTarget] = useState<ApiKeyRecord | null>(null);
  const [revoking, setRevoking] = useState(false);

  function loadData() {
    setLoading(true);
    Promise.all([listApiKeys(), listActors()])
      .then(([keysRes, actorsRes]) => {
        setKeys(keysRes.api_keys || keysRes.keys || []);
        setActors(actorsRes.actors || []);
      })
      .catch(() => setToast({ message: "Failed to load API keys", variant: "error" }))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newActorId.trim()) return;
    setSaving(true);
    try {
      const res = await createApiKey(newActorId.trim(), newActorType, {});
      const key = res.api_key || res.key || res.key_id || "";
      setCreatedKey(key);
      setToast({ message: "API key created", variant: "success" });
      setNewActorId("");
      loadData();
    } catch {
      setToast({ message: "Failed to create API key", variant: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function handleRevoke() {
    if (!revokeTarget) return;
    setRevoking(true);
    try {
      await revokeApiKey(revokeTarget.key_id);
      setToast({ message: "API key revoked", variant: "success" });
      setRevokeTarget(null);
      loadData();
    } catch {
      setToast({ message: "Failed to revoke key", variant: "error" });
    } finally {
      setRevoking(false);
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="API Keys"
        description="Manage API credentials for your business"
        actions={
          <Button size="sm" onClick={() => { setShowCreate(true); setCreatedKey(null); }}>
            Generate New Key
          </Button>
        }
      />

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : keys.length === 0 ? (
            <EmptyState title="No API keys found" description="Generate your first API key to integrate with BOS" />
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
                    <TableCell className="font-mono text-xs">{k.actor_id.slice(0, 12)}...</TableCell>
                    <TableCell><Badge variant="secondary">{k.actor_type}</Badge></TableCell>
                    <TableCell>
                      <Badge variant={k.status === "ACTIVE" ? "success" : "destructive"}>
                        {k.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{formatDateTime(k.created_at)}</TableCell>
                    <TableCell className="text-right">
                      {k.status === "ACTIVE" && (
                        <Button variant="destructive" size="sm" onClick={() => setRevokeTarget(k)}>
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

      {/* Create Key Dialog */}
      <FormDialog
        open={showCreate}
        onClose={() => { setShowCreate(false); setCreatedKey(null); }}
        title="Generate API Key"
        description="Create a new API key for system integration"
        onSubmit={handleCreate}
        submitLabel="Generate"
        loading={saving}
      >
        {createdKey ? (
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950">
            <p className="mb-2 text-sm font-semibold text-green-700 dark:text-green-300">
              Key created! Copy it now — it won't be shown again.
            </p>
            <code className="block break-all rounded bg-white p-2 text-sm dark:bg-neutral-900">
              {createdKey}
            </code>
          </div>
        ) : (
          <>
            <div>
              <Label htmlFor="actorSelect">Actor</Label>
              {actors.length > 0 ? (
                <Select
                  id="actorSelect"
                  value={newActorId}
                  onChange={(e) => setNewActorId(e.target.value)}
                  required
                >
                  <option value="">-- Select an actor --</option>
                  {actors.map((a) => (
                    <option key={a.actor_id} value={a.actor_id}>
                      {a.display_name || a.actor_id.slice(0, 12)}
                    </option>
                  ))}
                </Select>
              ) : (
                <Input
                  id="actorId"
                  value={newActorId}
                  onChange={(e) => setNewActorId(e.target.value)}
                  placeholder="Actor ID (UUID)"
                  required
                />
              )}
            </div>
            <div>
              <Label htmlFor="actorType">Actor Type</Label>
              <Select
                id="actorType"
                value={newActorType}
                onChange={(e) => setNewActorType(e.target.value)}
              >
                {ACTOR_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </Select>
            </div>
          </>
        )}
      </FormDialog>

      {/* Revoke Confirmation */}
      <ConfirmDialog
        open={!!revokeTarget}
        onClose={() => setRevokeTarget(null)}
        onConfirm={handleRevoke}
        title="Revoke API Key"
        description={`Revoke key ${revokeTarget?.key_id.slice(0, 12)}...? This cannot be undone. Any integration using this key will stop working.`}
        confirmLabel="Revoke"
        confirmVariant="destructive"
        loading={revoking}
      />

      {toast && (
        <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />
      )}
    </AppShell>
  );
}
