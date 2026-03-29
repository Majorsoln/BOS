"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, CardHeader, CardTitle, Badge, Select,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getLedgerEntries } from "@/lib/api/saas";
import { formatDate } from "@/lib/utils";
import {
  BookOpen, DollarSign, TrendingUp, Building2, Layers, ArrowDownRight,
} from "lucide-react";

export default function RlaLedgerPage() {
  const [statusFilter, setStatusFilter] = useState("");

  const entriesQuery = useQuery({
    queryKey: ["agent", "ledger", "entries", statusFilter],
    queryFn: () => getLedgerEntries({
      status: statusFilter || undefined,
      limit: 100,
    }),
  });

  type Entry = {
    entry_id: string; created_at: string; tenant_name: string;
    gross_amount: number; currency: string; tax_amount: number;
    gateway_fee: number; net_distributable: number; status: string;
    period: string; remote_agent_name: string;
    shares: Array<{ share_type: string; amount: number; rate_pct: string }>;
  };

  const entries: Entry[] = entriesQuery.data?.data ?? [];

  const totalGross = entries.reduce((s, e) => s + (e.gross_amount || 0), 0);
  const totalNet = entries.reduce((s, e) => s + (e.net_distributable || 0), 0);
  const rlaTotal = entries.reduce((s, e) => {
    const share = (e.shares ?? []).find((sh) => sh.share_type === "RLA_SHARE");
    return s + (share?.amount || 0);
  }, 0);
  const platformTotal = entries.reduce((s, e) => {
    const share = (e.shares ?? []).find((sh) => sh.share_type === "PLATFORM_ROYALTY");
    return s + (share?.amount || 0);
  }, 0);

  return (
    <div>
      <PageHeader
        title="Revenue Ledger — Daftari la Mapato"
        description="Per-sale breakdown showing exactly how every shilling is distributed."
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <StatCard title="Entries" value={entries.length} icon={Layers} />
        <StatCard title="Gross" value={totalGross.toLocaleString()} icon={DollarSign} />
        <StatCard title="Net" value={totalNet.toLocaleString()} icon={TrendingUp} />
        <StatCard title="Your Share" value={rlaTotal.toLocaleString()} icon={Building2} description="RLA market share" />
        <StatCard title="Platform" value={platformTotal.toLocaleString()} icon={ArrowDownRight} description="To remit" />
      </div>

      <div className="mt-4 flex gap-3">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-48">
          <option value="">All Statuses</option>
          <option value="RECORDED">Recorded</option>
          <option value="SETTLED">Settled</option>
          <option value="PAYABLE">Payable</option>
          <option value="PAID">Paid</option>
          <option value="REVERSED">Reversed</option>
        </Select>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-sm">All Ledger Entries — Kila Sale, Kila Mgao</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {entries.length === 0 ? (
            <EmptyState title="No entries" description="Sales will appear here with full distribution breakdown" />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tenant</TableHead>
                    <TableHead>Agent</TableHead>
                    <TableHead className="text-right">Gross</TableHead>
                    <TableHead className="text-right">Tax</TableHead>
                    <TableHead className="text-right">Fee</TableHead>
                    <TableHead className="text-right">Net</TableHead>
                    <TableHead className="text-right">Your Share</TableHead>
                    <TableHead className="text-right">Platform</TableHead>
                    <TableHead className="text-right">Agent Share</TableHead>
                    <TableHead>Currency</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {entries.map((e) => {
                    const rlaShare = (e.shares ?? []).find((s) => s.share_type === "RLA_SHARE");
                    const platformShare = (e.shares ?? []).find((s) => s.share_type === "PLATFORM_ROYALTY");
                    const agentShare = (e.shares ?? []).find((s) => s.share_type === "REMOTE_AGENT_SHARE");
                    return (
                      <TableRow key={e.entry_id} className={e.status === "REVERSED" ? "opacity-60 line-through" : ""}>
                        <TableCell className="text-sm font-medium max-w-[120px] truncate">{e.tenant_name || "—"}</TableCell>
                        <TableCell className="text-xs max-w-[100px] truncate">
                          {e.remote_agent_name || <span className="italic text-bos-silver-dark">Direct</span>}
                        </TableCell>
                        <TableCell className="text-right font-mono font-medium">{(e.gross_amount || 0).toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono text-xs text-bos-silver-dark">{(e.tax_amount || 0).toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono text-xs text-bos-silver-dark">{(e.gateway_fee || 0).toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono text-green-600 font-medium">{(e.net_distributable || 0).toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono text-blue-600">{rlaShare ? rlaShare.amount.toLocaleString() : "—"}</TableCell>
                        <TableCell className="text-right font-mono text-purple-600">{platformShare ? platformShare.amount.toLocaleString() : "—"}</TableCell>
                        <TableCell className="text-right font-mono text-green-600">{agentShare ? agentShare.amount.toLocaleString() : "—"}</TableCell>
                        <TableCell className="text-xs">{e.currency}</TableCell>
                        <TableCell className="text-center">
                          <Badge variant={
                            e.status === "PAID" ? "success" : e.status === "REVERSED" ? "destructive" :
                            e.status === "PAYABLE" ? "gold" : e.status === "SETTLED" ? "blue" : "outline"
                          }>{e.status}</Badge>
                        </TableCell>
                        <TableCell className="text-xs text-bos-silver-dark">{e.period || "—"}</TableCell>
                        <TableCell className="text-xs text-bos-silver-dark">{e.created_at ? formatDate(e.created_at) : "—"}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
