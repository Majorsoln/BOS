"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, CardHeader, CardTitle, Badge, Select,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getLedgerSummary, getLedgerEntries } from "@/lib/api/saas";
import { getMyCommissions } from "@/lib/api/agents";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import {
  DollarSign, TrendingUp, PiggyBank, ArrowUpRight, ArrowDownRight,
  Building2, BookOpen, Send, Shield, BarChart3,
} from "lucide-react";

export default function RevenuePage() {
  const now = new Date();
  const currentPeriod = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const [period, setPeriod] = useState(currentPeriod);

  const summaryQuery = useQuery({
    queryKey: ["agent", "ledger", "summary", period],
    queryFn: () => getLedgerSummary(period),
  });

  const commissionsQuery = useQuery({
    queryKey: ["agent", "commissions"],
    queryFn: getMyCommissions,
  });

  type Summary = {
    total_entries: number; total_gross: number; total_tax: number;
    total_gateway_fees: number; total_net: number;
    total_platform_share: number; total_rla_share: number;
    total_agent_share: number; total_reserve: number;
  };

  const summary: Summary | null = summaryQuery.data?.data ?? null;
  const commissions: Array<Record<string, unknown>> = commissionsQuery.data?.data ?? [];

  const totalEarned = commissions.reduce((s, c) => s + parseFloat((c.amount as string) || "0"), 0);

  // Period selector
  const periods: string[] = [];
  for (let i = 0; i < 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    periods.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }

  return (
    <div>
      <PageHeader
        title="Revenue Overview — Muhtasari wa Mapato"
        description="Your regional revenue, market share earnings, and distribution."
      />

      {/* Revenue Flow Doctrine */}
      <Card className="mb-6 border-green-200/50 bg-green-50/30 dark:border-green-800/30 dark:bg-green-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <PiggyBank className="mt-0.5 h-5 w-5 text-green-600" />
            <div className="text-sm">
              <p className="font-semibold text-green-700 dark:text-green-400">Mtiririko wa Pesa — Revenue Flow</p>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-4">
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">1. Tenant Pays</p>
                  <p className="text-xs text-bos-silver-dark">Gross amount collected</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">2. Tax + Fees Out</p>
                  <p className="text-xs text-bos-silver-dark">Tax + gateway fees deducted</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">3. Your Share</p>
                  <p className="text-xs text-bos-silver-dark">Market share % of net</p>
                </div>
                <div className="rounded-md bg-white/60 p-2 dark:bg-neutral-900/60">
                  <p className="font-medium text-neutral-800 dark:text-neutral-200">4. Remit Platform</p>
                  <p className="text-xs text-bos-silver-dark">Send platform royalty share</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Period Selector */}
      <div className="mb-4 flex items-center gap-3">
        <span className="text-sm font-medium">Period:</span>
        <Select value={period} onChange={(e) => setPeriod(e.target.value)} className="w-48">
          {periods.map((p) => <option key={p} value={p}>{p}</option>)}
        </Select>
      </div>

      {/* Stats */}
      {summary ? (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <StatCard title="Gross Revenue" value={(summary.total_gross || 0).toLocaleString()} icon={DollarSign} />
            <StatCard title="Tax Collected" value={(summary.total_tax || 0).toLocaleString()} icon={Building2} />
            <StatCard title="Net Distributable" value={(summary.total_net || 0).toLocaleString()} icon={TrendingUp} />
            <StatCard title="Your Share (RLA)" value={(summary.total_rla_share || 0).toLocaleString()} icon={Shield} />
            <StatCard title="Platform Share" value={(summary.total_platform_share || 0).toLocaleString()} icon={ArrowUpRight} description="To remit" />
          </div>

          {/* Distribution Breakdown */}
          <Card className="mt-6">
            <CardHeader><CardTitle className="text-sm">Distribution — Mgao wa {period}</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-lg border-2 border-blue-200 bg-blue-50 p-4 text-center dark:border-blue-800 dark:bg-blue-950">
                  <p className="text-xs text-blue-700 dark:text-blue-400">Your RLA Share</p>
                  <p className="text-2xl font-bold font-mono text-blue-700 dark:text-blue-400">
                    {(summary.total_rla_share || 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-bos-silver-dark">Keep this</p>
                </div>
                <div className="rounded-lg border-2 border-purple-200 bg-purple-50 p-4 text-center dark:border-purple-800 dark:bg-purple-950">
                  <p className="text-xs text-purple-700 dark:text-purple-400">Platform Royalty</p>
                  <p className="text-2xl font-bold font-mono text-purple-700 dark:text-purple-400">
                    {(summary.total_platform_share || 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-bos-silver-dark">Remit this</p>
                </div>
                <div className="rounded-lg border-2 border-green-200 bg-green-50 p-4 text-center dark:border-green-800 dark:bg-green-950">
                  <p className="text-xs text-green-700 dark:text-green-400">Agent Commissions</p>
                  <p className="text-2xl font-bold font-mono text-green-700 dark:text-green-400">
                    {(summary.total_agent_share || 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-bos-silver-dark">Pay to agents</p>
                </div>
                <div className="rounded-lg border-2 border-amber-200 bg-amber-50 p-4 text-center dark:border-amber-800 dark:bg-amber-950">
                  <p className="text-xs text-amber-700 dark:text-amber-400">Reserve / Held</p>
                  <p className="text-2xl font-bold font-mono text-amber-700 dark:text-amber-400">
                    {(summary.total_reserve || 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-bos-silver-dark">On hold</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <EmptyState title="No revenue data" description={`No ledger entries for ${period}`} />
      )}

      {/* Quick Links */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Link href="/agent/revenue/ledger">
          <Card className="group cursor-pointer transition-shadow hover:shadow-md">
            <CardContent className="flex items-center gap-3 p-4">
              <BookOpen className="h-5 w-5 text-bos-purple" />
              <div>
                <p className="font-semibold text-sm">Revenue Ledger</p>
                <p className="text-xs text-bos-silver-dark">Per-sale breakdown with full distribution</p>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link href="/agent/revenue/remittance">
          <Card className="group cursor-pointer transition-shadow hover:shadow-md">
            <CardContent className="flex items-center gap-3 p-4">
              <Send className="h-5 w-5 text-bos-purple" />
              <div>
                <p className="font-semibold text-sm">Remittance</p>
                <p className="text-xs text-bos-silver-dark">Submit platform share remittance</p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
