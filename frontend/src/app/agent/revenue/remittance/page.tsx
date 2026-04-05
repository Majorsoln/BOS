"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, CardHeader, CardTitle, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getLedgerSummary } from "@/lib/api/saas";
import {
  Send, DollarSign, CheckCircle, Clock, AlertTriangle, ArrowUpRight,
} from "lucide-react";

export default function RemittancePage() {
  const now = new Date();
  const currentPeriod = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  const summaryQuery = useQuery({
    queryKey: ["agent", "ledger", "summary", currentPeriod],
    queryFn: () => getLedgerSummary(currentPeriod),
  });

  type Summary = {
    total_entries: number; total_gross: number; total_net: number;
    total_platform_share: number; total_rla_share: number;
    total_agent_share: number; total_reserve: number;
  };

  const summary: Summary | null = summaryQuery.data?.data ?? null;
  const platformOwed = summary?.total_platform_share ?? 0;

  // Mock remittance history — in production, this comes from a dedicated API
  const remittanceHistory: Array<{
    id: string; period: string; expected: number; remitted: number;
    currency: string; status: string; date: string;
  }> = [];

  return (
    <div>
      <PageHeader
        title="Remittance"
        description="Remit platform royalty share. Track what you owe and what you've sent."
      />

      {/* Remittance Doctrine */}
      <Card className="mb-6 border-purple-200/50 bg-purple-50/30 dark:border-purple-800/30 dark:bg-purple-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Send className="mt-0.5 h-5 w-5 text-purple-600" />
            <div className="text-sm">
              <p className="font-semibold text-purple-700 dark:text-purple-400">
                Remittance Rules
              </p>
              <p className="mt-1 text-xs text-bos-silver-dark">
                BOS calculates the platform share automatically from every sale.
                You collect from tenants. After deducting your market share and agent commissions,
                the remaining platform royalty must be remitted. BOS tracks everything — transparency is law.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Current Period Summary */}
      {summary ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard title="Total Collected" value={(summary.total_gross || 0).toLocaleString()} icon={DollarSign} description={`${currentPeriod}`} />
          <StatCard title="Your Share (Keep)" value={(summary.total_rla_share || 0).toLocaleString()} icon={CheckCircle} description="Market share earnings" />
          <StatCard
            title="Platform Share (Owe)"
            value={platformOwed.toLocaleString()}
            icon={ArrowUpRight}
            description="To remit to platform"
          />
          <StatCard title="Agent Commissions" value={(summary.total_agent_share || 0).toLocaleString()} icon={Clock} description="Pay to remote agents" />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard title="Total Collected" value="—" icon={DollarSign} />
          <StatCard title="Your Share" value="—" icon={CheckCircle} />
          <StatCard title="Platform Owed" value="—" icon={ArrowUpRight} />
          <StatCard title="Agent Commissions" value="—" icon={Clock} />
        </div>
      )}

      {/* What You Owe Breakdown */}
      {summary && platformOwed > 0 && (
        <Card className="mt-6 border-amber-200 dark:border-amber-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm text-amber-700">
              <AlertTriangle className="h-4 w-4" /> Outstanding Remittance — {currentPeriod}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-lg border-2 border-purple-200 bg-purple-50 p-4 text-center dark:border-purple-800 dark:bg-purple-950">
                <p className="text-xs text-purple-700 dark:text-purple-400">Platform Royalty</p>
                <p className="text-3xl font-bold font-mono text-purple-700 dark:text-purple-400">
                  {platformOwed.toLocaleString()}
                </p>
                <p className="mt-1 text-xs text-bos-silver-dark">Must remit this amount</p>
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-xs text-bos-silver-dark mb-2">Breakdown</p>
                <dl className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <dt>Gross collected</dt>
                    <dd className="font-mono">{(summary.total_gross || 0).toLocaleString()}</dd>
                  </div>
                  <div className="flex justify-between text-bos-silver-dark">
                    <dt>- Your share</dt>
                    <dd className="font-mono">-{(summary.total_rla_share || 0).toLocaleString()}</dd>
                  </div>
                  <div className="flex justify-between text-bos-silver-dark">
                    <dt>- Agent shares</dt>
                    <dd className="font-mono">-{(summary.total_agent_share || 0).toLocaleString()}</dd>
                  </div>
                  <div className="flex justify-between text-bos-silver-dark">
                    <dt>- Reserve</dt>
                    <dd className="font-mono">-{(summary.total_reserve || 0).toLocaleString()}</dd>
                  </div>
                  <div className="border-t pt-1 flex justify-between font-bold">
                    <dt>= Platform owed</dt>
                    <dd className="font-mono text-purple-600">{platformOwed.toLocaleString()}</dd>
                  </div>
                </dl>
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-xs text-bos-silver-dark mb-2">Remittance Methods</p>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-center gap-2"><CheckCircle className="h-3 w-3 text-green-600" /> M-Pesa Paybill</li>
                  <li className="flex items-center gap-2"><CheckCircle className="h-3 w-3 text-green-600" /> Bank Transfer</li>
                  <li className="flex items-center gap-2"><CheckCircle className="h-3 w-3 text-green-600" /> Mobile Money</li>
                </ul>
                <p className="mt-3 text-xs text-bos-silver-dark">
                  Platform confirms receipt and updates settlement status automatically.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Remittance History */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-sm">Remittance History</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {remittanceHistory.length === 0 ? (
            <EmptyState title="No remittance records yet" description="Your remittance history will appear here once you start remitting to the platform" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  <TableHead className="text-right">Expected</TableHead>
                  <TableHead className="text-right">Remitted</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {remittanceHistory.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-mono">{r.period}</TableCell>
                    <TableCell className="text-right font-mono">{r.expected.toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono">{r.remitted.toLocaleString()}</TableCell>
                    <TableCell className="text-xs">{r.currency}</TableCell>
                    <TableCell className="text-center">
                      <Badge variant={r.status === "CONFIRMED" ? "success" : r.status === "PENDING" ? "gold" : "outline"}>
                        {r.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{r.date}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
