"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { Button, Card, CardContent, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge } from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import { listFeatureFlags, setFeatureFlag } from "@/lib/api/admin";

interface Flag {
  flag_name: string;
  enabled: boolean;
}

export default function FeatureFlagsPage() {
  const [flags, setFlags] = useState<Flag[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);

  function loadFlags() {
    listFeatureFlags()
      .then((res) => setFlags(res.flags || res.feature_flags || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadFlags(); }, []);

  async function handleToggle(flagName: string, currentEnabled: boolean) {
    setToggling(flagName);
    try {
      await setFeatureFlag(flagName, !currentEnabled);
      loadFlags();
    } catch {
      // silently fail
    } finally {
      setToggling(null);
    }
  }

  return (
    <AppShell>
      <PageHeader title="Feature Flags" description="Enable or disable platform features" />
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : flags.length === 0 ? (
            <EmptyState title="No feature flags configured" description="Feature flags are set up during platform initialization" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Flag Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {flags.map((f) => (
                  <TableRow key={f.flag_name}>
                    <TableCell className="font-mono text-sm">{f.flag_name}</TableCell>
                    <TableCell>
                      <Badge variant={f.enabled ? "success" : "secondary"}>
                        {f.enabled ? "Enabled" : "Disabled"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggle(f.flag_name, f.enabled)}
                        disabled={toggling === f.flag_name}
                      >
                        {toggling === f.flag_name ? "..." : f.enabled ? "Disable" : "Enable"}
                      </Button>
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
