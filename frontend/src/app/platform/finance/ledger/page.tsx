"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, CardHeader, CardTitle, Badge, Select,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import {
  getLedgerEntries, getLedgerEntry, getLedgerSummary, getOperatingLaws,
} from "@/lib/api/saas";
import { REGIONS } from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import {
  BookOpen, DollarSign, TrendingUp, Shield, UserCheck, Clock,
  ArrowUpRight, ArrowDownRight, Eye, Scale, AlertTriangle,
  Building2, Layers, FileText, ChevronDown, ChevronUp,
} from "lucide-react";

type TabKey = "entries" | "summary" | "laws";

const STATUS_COLORS: Record<string, string> = {
  RECORDED: "outline",
  SETTLED: "blue",
  PAYABLE: "gold",
  PAID: "success",
  REVERSED: "destructive",
  DISPUTED: "destructive",
};

export default function RevenueLedgerPage() {
  const [tab, setTab] = useState<TabKey>("entries");

  const tabs: { key: TabKey; label: string }[] = [
    { key: "entries", label: "Ledger Entries" },
    { key: "summary", label: "Period Summary" },
    { key: "laws", label: "Operating Laws" },
  ];

  return (
    <div>
      <PageHeader
        title="Revenue Ledger"
        description="Source of truth for all revenue distribution. BOS holds truth. RLA holds money."
      />

      {/* Doctrine Banner */}
      <Card className="mb-6 border-amber-200/50 bg-amber-50/30 dark:border-amber-800/30 dark:bg-amber-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Scale className="mt-0.5 h-5 w-5 text-amber-600" />
            <div className="text-sm">
              <p className="font-semibold text-amber-700 dark:text-amber-400">
                Ledger Doctrine: Every Sale Has Full Transparency
              </p>
              <p className="mt-1 text-xs text-bos-silver-dark">
                Every sale auto-records: Gross &rarr; Tax &rarr; Gateway Fee &rarr; Net &rarr;
                Platform Royalty + RLA Share + Agent Share + Reserve.
                Immutable entries. Reversals create new negative entries. Historical sales never
                recalculate under new rules.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="mb-6 flex gap-1 rounded-lg bg-bos-silver-light p-1 dark:bg-neutral-800 w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-white text-bos-purple shadow-sm dark:bg-neutral-900"
                : "text-bos-silver-dark hover:text-neutral-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "entries" && <LedgerEntriesTab />}
      {tab === "summary" && <PeriodSummaryTab />}
      {tab === "laws" && <OperatingLawsTab />}
    </div>
  );
}

/* ── Ledger Entries Tab ────────────────────────────────── */

function LedgerEntriesTab() {
  const [regionFilter, setRegionFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);

  const entriesQuery = useQuery({
    queryKey: ["saas", "ledger", "entries", regionFilter, statusFilter],
    queryFn: () => getLedgerEntries({
      region_code: regionFilter || undefined,
      status: statusFilter || undefined,
      limit: 100,
    }),
  });

  const detailQuery = useQuery({
    queryKey: ["saas", "ledger", "entry", selectedEntryId],
    queryFn: () => getLedgerEntry(selectedEntryId!),
    enabled: !!selectedEntryId,
  });

  type Entry = {
    entry_id: string; created_at: string; tenant_id: string; tenant_name: string;
    region_code: string; rla_id: string; rla_name: string;
    remote_agent_id: string; remote_agent_name: string;
    sale_reference: string; gross_amount: number; currency: string;
    tax_treatment: string; tax_amount: number; gateway_provider: string;
    gateway_fee: number; net_distributable: number;
    status: string; hold_until: string; period: string;
    commission_rule_version: string; contract_version: string;
    shares: Array<{
      share_type: string; party_id: string; party_name: string;
      rate_pct: string; amount: number; currency: string;
      rule_version: string; notes?: string;
    }>;
    reversal_reason: string; reversal_entry_id: string;
    settled_at: string; payable_at: string; paid_at: string; notes: string;
  };

  const entries: Entry[] = entriesQuery.data?.data ?? [];

  // Stats
  const totalGross = entries.reduce((s, e) => s + (e.gross_amount || 0), 0);
  const totalNet = entries.reduce((s, e) => s + (e.net_distributable || 0), 0);
  const totalTax = entries.reduce((s, e) => s + (e.tax_amount || 0), 0);
  const totalFees = entries.reduce((s, e) => s + (e.gateway_fee || 0), 0);
  const reversedCount = entries.filter((e) => e.status === "REVERSED").length;

  // Regions from data
  const activeRegions = [...new Set(entries.map((e) => e.region_code).filter(Boolean))];

  const selectedEntry: Entry | null = detailQuery.data?.data ?? null;

  return (
    <div className="space-y-6">
      {/* Top Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <StatCard title="Entries" value={entries.length} icon={Layers} description="Total ledger entries" />
        <StatCard title="Gross Revenue" value={fmt(totalGross)} icon={DollarSign} description="Before deductions" />
        <StatCard title="Tax Collected" value={fmt(totalTax)} icon={Building2} description="For tax authority" />
        <StatCard title="Net Distributable" value={fmt(totalNet)} icon={TrendingUp} description="After tax & fees" />
        <StatCard
          title="Reversals"
          value={reversedCount}
          icon={ArrowDownRight}
          description={reversedCount > 0 ? "Refunds/chargebacks" : "None"}
        />
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <Select value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)} className="w-48">
          <option value="">All Regions</option>
          {activeRegions.map((r) => (
            <option key={r} value={r}>{r} — {REGIONS.find((reg) => reg.code === r)?.name || r}</option>
          ))}
        </Select>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-48">
          <option value="">All Statuses</option>
          <option value="RECORDED">Recorded</option>
          <option value="SETTLED">Settled</option>
          <option value="PAYABLE">Payable</option>
          <option value="PAID">Paid</option>
          <option value="REVERSED">Reversed</option>
          <option value="DISPUTED">Disputed</option>
        </Select>
      </div>

      {/* Entries Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Per-Sale Revenue Breakdown</CardTitle>
            <span className="text-xs text-bos-silver-dark">{entries.length} entries</span>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {entries.length === 0 ? (
            <EmptyState title="No ledger entries" description="Sales recorded through agents will appear here with full distribution breakdown" />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tenant</TableHead>
                    <TableHead>Region</TableHead>
                    <TableHead>RLA</TableHead>
                    <TableHead>Remote Agent</TableHead>
                    <TableHead className="text-right">Gross</TableHead>
                    <TableHead>Currency</TableHead>
                    <TableHead className="text-right">Tax</TableHead>
                    <TableHead className="text-right">Fee</TableHead>
                    <TableHead className="text-right">Net</TableHead>
                    <TableHead>Rule Ver.</TableHead>
                    <TableHead className="text-right">Platform</TableHead>
                    <TableHead className="text-right">RLA Share</TableHead>
                    <TableHead className="text-right">Agent Share</TableHead>
                    <TableHead>Hold Until</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {entries.map((e) => {
                    const platformShare = (e.shares ?? []).find((s) => s.share_type === "PLATFORM_ROYALTY");
                    const rlaShare = (e.shares ?? []).find((s) => s.share_type === "RLA_SHARE");
                    const agentShare = (e.shares ?? []).find((s) => s.share_type === "REMOTE_AGENT_SHARE");

                    return (
                      <TableRow key={e.entry_id} className={e.status === "REVERSED" ? "opacity-60 line-through" : ""}>
                        <TableCell className="text-sm font-medium max-w-[120px] truncate" title={e.tenant_name}>
                          {e.tenant_name || e.tenant_id?.slice(0, 8) || "—"}
                        </TableCell>
                        <TableCell>
                          <span className="text-xs font-medium">{e.region_code || "—"}</span>
                        </TableCell>
                        <TableCell className="text-sm max-w-[100px] truncate" title={e.rla_name}>
                          {e.rla_name || "—"}
                        </TableCell>
                        <TableCell className="text-sm max-w-[100px] truncate" title={e.remote_agent_name}>
                          {e.remote_agent_name || <span className="text-bos-silver-dark italic">Direct</span>}
                        </TableCell>
                        <TableCell className="text-right font-mono font-medium">{fmt(e.gross_amount)}</TableCell>
                        <TableCell className="text-xs">{e.currency}</TableCell>
                        <TableCell className="text-right font-mono text-xs text-bos-silver-dark">{fmt(e.tax_amount)}</TableCell>
                        <TableCell className="text-right font-mono text-xs text-bos-silver-dark">{fmt(e.gateway_fee)}</TableCell>
                        <TableCell className="text-right font-mono font-medium text-green-600">{fmt(e.net_distributable)}</TableCell>
                        <TableCell className="text-xs text-bos-silver-dark">{e.commission_rule_version || "—"}</TableCell>
                        <TableCell className="text-right font-mono text-xs text-purple-600">
                          {platformShare ? fmt(platformShare.amount) : "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-blue-600">
                          {rlaShare ? fmt(rlaShare.amount) : "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-green-600">
                          {agentShare ? fmt(agentShare.amount) : "—"}
                        </TableCell>
                        <TableCell className="text-xs text-bos-silver-dark">
                          {e.hold_until ? formatDate(e.hold_until) : "—"}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant={(STATUS_COLORS[e.status] as "outline" | "blue" | "gold" | "success" | "destructive" | "purple") || "outline"}>
                            {e.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-bos-silver-dark">{e.period || "—"}</TableCell>
                        <TableCell>
                          <button
                            onClick={() => setSelectedEntryId(e.entry_id)}
                            className="text-bos-purple hover:underline text-xs"
                          >
                            Detail
                          </button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Entry Detail Panel */}
      {selectedEntryId && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Ledger Entry Detail</CardTitle>
              <button onClick={() => setSelectedEntryId(null)} className="text-xs text-bos-purple hover:underline">
                Close
              </button>
            </div>
          </CardHeader>
          <CardContent>
            {selectedEntry ? (
              <EntryDetail entry={selectedEntry} />
            ) : (
              <p className="text-sm text-bos-silver-dark">Loading...</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ── Entry Detail ──────────────────────────────────────── */

function EntryDetail({ entry }: { entry: Record<string, unknown> }) {
  const e = entry as Record<string, unknown>;
  const shares = (e.shares as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="space-y-4 text-sm">
      {/* Attribution */}
      <div className="grid grid-cols-2 gap-3">
        <Field label="Entry ID" value={(e.entry_id as string)?.slice(0, 12) + "..."} />
        <Field label="Date" value={formatDate(e.created_at as string)} />
        <Field label="Tenant" value={e.tenant_name as string} />
        <Field label="Region" value={e.region_code as string} />
        <Field label="RLA" value={e.rla_name as string} />
        <Field label="Remote Agent" value={(e.remote_agent_name as string) || "Direct (no agent)"} />
        <Field label="Sale Reference" value={e.sale_reference as string} />
        <Field label="Period" value={e.period as string} />
      </div>

      {/* Amounts */}
      <div className="rounded-lg border p-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-bos-silver-dark">Financial Breakdown</p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <AmountField label="Gross" amount={e.gross_amount as number} currency={e.currency as string} />
          <AmountField label="Tax" amount={e.tax_amount as number} currency={e.currency as string} muted />
          <AmountField label="Gateway Fee" amount={e.gateway_fee as number} currency={e.currency as string} muted />
          <AmountField label="Net Distributable" amount={e.net_distributable as number} currency={e.currency as string} highlight />
        </div>
        <div className="mt-2 flex gap-4 text-xs text-bos-silver-dark">
          <span>Tax: {e.tax_treatment as string}</span>
          <span>Gateway: {(e.gateway_provider as string) || "—"}</span>
        </div>
      </div>

      {/* Distribution Shares */}
      <div className="rounded-lg border p-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-bos-silver-dark">Distribution Shares</p>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Party</TableHead>
              <TableHead className="text-right">Rate</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Rule Ver.</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shares.map((s, i) => (
              <TableRow key={i}>
                <TableCell>
                  <ShareTypeBadge type={s.share_type as string} />
                </TableCell>
                <TableCell className="text-sm">{s.party_name as string}</TableCell>
                <TableCell className="text-right font-mono text-xs">
                  {parseFloat((s.rate_pct as string) || "0") > 0 ? `${s.rate_pct}%` : "—"}
                </TableCell>
                <TableCell className="text-right font-mono font-medium">
                  {fmt(s.amount as number)} {s.currency as string}
                </TableCell>
                <TableCell className="text-xs text-bos-silver-dark">{s.rule_version as string}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Settlement Lifecycle */}
      <div className="rounded-lg border p-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-bos-silver-dark">Settlement Lifecycle</p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Field label="Status" value={e.status as string} />
          <Field label="Hold Until" value={e.hold_until ? formatDate(e.hold_until as string) : "—"} />
          <Field label="Settled At" value={e.settled_at ? formatDate(e.settled_at as string) : "—"} />
          <Field label="Paid At" value={e.paid_at ? formatDate(e.paid_at as string) : "—"} />
        </div>
        {(e.reversal_reason as string) && (
          <div className="mt-2 rounded-md bg-red-50 p-2 dark:bg-red-950">
            <p className="text-xs text-red-600">Reversal: {e.reversal_reason as string}</p>
          </div>
        )}
      </div>

      {/* Rule Versions */}
      <div className="flex gap-4 text-xs text-bos-silver-dark">
        <span>Contract: {(e.contract_version as string) || "—"}</span>
        <span>Commission Rules: {(e.commission_rule_version as string) || "—"}</span>
      </div>
    </div>
  );
}

/* ── Period Summary Tab ───────────────────────────────── */

function PeriodSummaryTab() {
  const now = new Date();
  const currentPeriod = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const [period, setPeriod] = useState(currentPeriod);

  const summaryQuery = useQuery({
    queryKey: ["saas", "ledger", "summary", period],
    queryFn: () => getLedgerSummary(period),
  });

  type Summary = {
    period: string;
    total_entries: number;
    total_gross: number;
    total_tax: number;
    total_gateway_fees: number;
    total_net: number;
    total_platform_share: number;
    total_rla_share: number;
    total_agent_share: number;
    total_reserve: number;
    by_region?: Record<string, {
      gross: number; net: number; platform: number; rla: number; agent: number; entries: number;
    }>;
    by_status?: Record<string, number>;
    currency?: string;
  };

  const summary: Summary | null = summaryQuery.data?.data ?? null;

  // Generate last 6 months for period selector
  const periods: string[] = [];
  for (let i = 0; i < 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    periods.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }

  return (
    <div className="space-y-6">
      {/* Period Selector */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium">Period:</span>
        <Select value={period} onChange={(e) => setPeriod(e.target.value)} className="w-48">
          {periods.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </Select>
      </div>

      {!summary ? (
        <EmptyState title="No data" description="No ledger entries for this period" />
      ) : (
        <>
          {/* Aggregate Stats */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <StatCard title="Entries" value={summary.total_entries} icon={Layers} />
            <StatCard title="Gross Revenue" value={fmt(summary.total_gross)} icon={DollarSign} />
            <StatCard title="Tax Collected" value={fmt(summary.total_tax)} icon={Building2} />
            <StatCard title="Gateway Fees" value={fmt(summary.total_gateway_fees)} icon={ArrowDownRight} />
            <StatCard title="Net Distributable" value={fmt(summary.total_net)} icon={TrendingUp} />
          </div>

          {/* Distribution Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Distribution Breakdown — {period}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-lg border-2 border-purple-200 bg-purple-50 p-4 text-center dark:border-purple-800 dark:bg-purple-950">
                  <p className="text-xs text-purple-700 dark:text-purple-400">Platform Royalty</p>
                  <p className="text-2xl font-bold font-mono text-purple-700 dark:text-purple-400">
                    {fmt(summary.total_platform_share)}
                  </p>
                </div>
                <div className="rounded-lg border-2 border-blue-200 bg-blue-50 p-4 text-center dark:border-blue-800 dark:bg-blue-950">
                  <p className="text-xs text-blue-700 dark:text-blue-400">RLA Share</p>
                  <p className="text-2xl font-bold font-mono text-blue-700 dark:text-blue-400">
                    {fmt(summary.total_rla_share)}
                  </p>
                </div>
                <div className="rounded-lg border-2 border-green-200 bg-green-50 p-4 text-center dark:border-green-800 dark:bg-green-950">
                  <p className="text-xs text-green-700 dark:text-green-400">Agent Commissions</p>
                  <p className="text-2xl font-bold font-mono text-green-700 dark:text-green-400">
                    {fmt(summary.total_agent_share)}
                  </p>
                </div>
                <div className="rounded-lg border-2 border-amber-200 bg-amber-50 p-4 text-center dark:border-amber-800 dark:bg-amber-950">
                  <p className="text-xs text-amber-700 dark:text-amber-400">Reserve / Held</p>
                  <p className="text-2xl font-bold font-mono text-amber-700 dark:text-amber-400">
                    {fmt(summary.total_reserve)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* By Region */}
          {summary.by_region && Object.keys(summary.by_region).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Revenue by Region — {period}</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Region</TableHead>
                      <TableHead className="text-center">Entries</TableHead>
                      <TableHead className="text-right">Gross</TableHead>
                      <TableHead className="text-right">Net</TableHead>
                      <TableHead className="text-right">Platform</TableHead>
                      <TableHead className="text-right">RLA</TableHead>
                      <TableHead className="text-right">Agent</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(summary.by_region).map(([region, data]) => (
                      <TableRow key={region}>
                        <TableCell className="font-medium">{region}</TableCell>
                        <TableCell className="text-center font-mono">{data.entries}</TableCell>
                        <TableCell className="text-right font-mono">{fmt(data.gross)}</TableCell>
                        <TableCell className="text-right font-mono text-green-600">{fmt(data.net)}</TableCell>
                        <TableCell className="text-right font-mono text-purple-600">{fmt(data.platform)}</TableCell>
                        <TableCell className="text-right font-mono text-blue-600">{fmt(data.rla)}</TableCell>
                        <TableCell className="text-right font-mono text-green-600">{fmt(data.agent)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {/* By Status */}
          {summary.by_status && Object.keys(summary.by_status).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Settlement Status Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-3">
                  {Object.entries(summary.by_status).map(([status, count]) => (
                    <div key={status} className="rounded-lg border px-4 py-2 text-center">
                      <Badge variant={(STATUS_COLORS[status] as "outline" | "blue" | "gold" | "success" | "destructive" | "purple") || "outline"}>
                        {status}
                      </Badge>
                      <p className="mt-1 text-lg font-bold font-mono">{count}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

/* ── Operating Laws Tab ──────────────────────────────── */

function OperatingLawsTab() {
  const lawsQuery = useQuery({
    queryKey: ["saas", "ledger", "operating-laws"],
    queryFn: getOperatingLaws,
  });

  type Law = { number: number; law: string; detail: string };
  const laws: Law[] = lawsQuery.data?.data ?? [];

  return (
    <div className="space-y-6">
      {/* Preamble */}
      <Card className="border-amber-200/50 bg-amber-50/30 dark:border-amber-800/30 dark:bg-amber-950/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Scale className="mt-0.5 h-5 w-5 text-amber-600" />
            <div>
              <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">
                BOS Revenue Operating Laws — Sheria za Mapato
              </p>
              <p className="mt-1 text-xs text-bos-silver-dark">
                These 10 laws govern all revenue distribution, settlement, and payout on the BOS platform.
                They are immutable doctrine. No admin, agent, or system process may violate them.
                Violations are logged and flagged automatically.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Laws */}
      {laws.length === 0 ? (
        <EmptyState title="Loading..." description="Fetching operating laws" />
      ) : (
        <div className="space-y-3">
          {laws.map((law) => (
            <Card key={law.number} className="overflow-hidden">
              <CardContent className="p-0">
                <div className="flex">
                  <div className="flex w-16 shrink-0 items-center justify-center bg-bos-purple text-white font-bold text-lg">
                    {law.number}
                  </div>
                  <div className="flex-1 p-4">
                    <p className="font-semibold text-sm">{law.law}</p>
                    <p className="mt-1 text-xs text-bos-silver-dark leading-relaxed">{law.detail}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Summary Box */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-neutral-50 p-4 dark:bg-neutral-900">
              <p className="text-xs font-semibold uppercase tracking-wider text-bos-silver-dark mb-2">Key Principle</p>
              <p className="text-sm font-medium">RLA holds money. BOS holds truth.</p>
              <p className="mt-1 text-xs text-bos-silver-dark">
                BOS never touches money. BOS calculates entitlements, records distributions,
                and tracks settlements. The RLA collects from tenants and remits to the platform.
              </p>
            </div>
            <div className="rounded-lg bg-neutral-50 p-4 dark:bg-neutral-900">
              <p className="text-xs font-semibold uppercase tracking-wider text-bos-silver-dark mb-2">Settlement Flow</p>
              <div className="flex items-center gap-2 text-xs">
                <Badge variant="outline">RECORDED</Badge>
                <span>&rarr;</span>
                <Badge variant="blue">SETTLED</Badge>
                <span>&rarr;</span>
                <Badge variant="gold">PAYABLE</Badge>
                <span>&rarr;</span>
                <Badge variant="success">PAID</Badge>
              </div>
              <p className="mt-2 text-xs text-bos-silver-dark">
                Reversals create new negative entries (Law #6). Never mutate existing records.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Shared Components ────────────────────────────────── */

function ShareTypeBadge({ type }: { type: string }) {
  const map: Record<string, { variant: string; label: string }> = {
    PLATFORM_ROYALTY: { variant: "purple", label: "Platform" },
    RLA_SHARE: { variant: "blue", label: "RLA" },
    REMOTE_AGENT_SHARE: { variant: "success", label: "Agent" },
    TAX_COLLECTED: { variant: "outline", label: "Tax" },
    GATEWAY_FEE: { variant: "outline", label: "Gateway" },
    RESERVE_HOLD: { variant: "gold", label: "Reserve" },
  };
  const info = map[type] || { variant: "outline", label: type };
  return <Badge variant={info.variant as "outline" | "blue" | "gold" | "success" | "destructive" | "purple"}>{info.label}</Badge>;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-bos-silver-dark">{label}</p>
      <p className="font-medium">{value || "—"}</p>
    </div>
  );
}

function AmountField({ label, amount, currency, muted, highlight }: {
  label: string; amount: number; currency: string; muted?: boolean; highlight?: boolean;
}) {
  return (
    <div className="text-center">
      <p className="text-xs text-bos-silver-dark">{label}</p>
      <p className={`font-mono font-bold ${highlight ? "text-green-600" : muted ? "text-bos-silver-dark" : ""}`}>
        {fmt(amount)}
      </p>
      <p className="text-[10px] text-bos-silver-dark">{currency}</p>
    </div>
  );
}

function fmt(amount: number | undefined | null): string {
  if (amount == null) return "—";
  return amount.toLocaleString();
}
