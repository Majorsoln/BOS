"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import { listTaxRules, setTaxRule } from "@/lib/api/admin";

interface TaxRule {
  tax_code: string;
  rate: number;
}

export default function TaxRulesPage() {
  const [rules, setRules] = useState<TaxRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [newCode, setNewCode] = useState("");
  const [newRate, setNewRate] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  function loadRules() {
    listTaxRules()
      .then((res) => setRules(res.tax_rules || res.rules || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadRules(); }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newCode || !newRate) return;
    setSaving(true);
    setMessage("");
    try {
      await setTaxRule(newCode, parseFloat(newRate));
      setNewCode("");
      setNewRate("");
      setMessage("Tax rule saved");
      loadRules();
    } catch {
      setMessage("Failed to save tax rule");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <PageHeader title="Tax Rules" description="Configure tax rates for your business" />

      {/* Add new rule */}
      <Card className="mb-6 max-w-xl">
        <CardHeader>
          <CardTitle>Add Tax Rule</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAdd} className="flex items-end gap-3">
            <div className="flex-1 space-y-1">
              <Label htmlFor="taxCode">Tax Code</Label>
              <Input id="taxCode" placeholder="e.g. VAT" value={newCode} onChange={(e) => setNewCode(e.target.value)} />
            </div>
            <div className="w-32 space-y-1">
              <Label htmlFor="rate">Rate (0-1)</Label>
              <Input id="rate" type="number" step="0.01" min="0" max="1" placeholder="0.16" value={newRate} onChange={(e) => setNewRate(e.target.value)} />
            </div>
            <Button type="submit" disabled={saving}>{saving ? "Saving..." : "Add"}</Button>
          </form>
          {message && <p className={`mt-2 text-sm ${message.includes("saved") ? "text-green-600" : "text-red-600"}`}>{message}</p>}
        </CardContent>
      </Card>

      {/* Rules list */}
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : rules.length === 0 ? (
            <EmptyState title="No tax rules configured" description="Add a tax rule above to get started" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tax Code</TableHead>
                  <TableHead>Rate</TableHead>
                  <TableHead>Percentage</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((r) => (
                  <TableRow key={r.tax_code}>
                    <TableCell className="font-medium">{r.tax_code}</TableCell>
                    <TableCell>{r.rate}</TableCell>
                    <TableCell>{(r.rate * 100).toFixed(1)}%</TableCell>
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
