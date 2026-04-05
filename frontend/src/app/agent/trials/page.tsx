"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Card, CardContent, CardHeader, CardTitle, Badge, Button, Input,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui";
import { getMyTenants } from "@/lib/api/agents";
import { convertTrial, extendTrial } from "@/lib/api/saas";
import { formatDate } from "@/lib/utils";
import { Clock, Users, TrendingUp, AlertTriangle, ArrowRight, CheckCircle } from "lucide-react";

export default function TrialsPage() {
  const qc = useQueryClient();
  const [showExtend, setShowExtend] = useState<string | null>(null);
  const [extraDays, setExtraDays] = useState("30");
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const tenants = useQuery({ queryKey: ["agent", "tenants"], queryFn: () => getMyTenants() });

  type Tenant = {
    business_id: string; business_name?: string; status: string;
    trial_expires_at?: string; combo_name?: string; created_at?: string;
    monthly_amount?: string; currency?: string;
  };

  const all: Tenant[] = tenants.data?.data ?? [];
  const trials = all.filter((t) => t.status === "TRIAL");
  const paying = all.filter((t) => t.status === "ACTIVE");
  const expired = all.filter((t) => t.status === "EXPIRED" || t.status === "CANCELLED");

  const now = Date.now();
  const expiringSoon = trials.filter((t) => {
    if (!t.trial_expires_at) return false;
    const days = Math.ceil((new Date(t.trial_expires_at).getTime() - now) / 86400000);
    return days <= 14 && days >= 0;
  });

  const convertMut = useMutation({
    mutationFn: (businessId: string) => convertTrial({ business_id: businessId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agent", "tenants"] });
      setToast({ msg: "Trial converted to paying!", ok: true });
    },
    onError: () => setToast({ msg: "Failed to convert trial", ok: false }),
  });

  const extendMut = useMutation({
    mutationFn: () => extendTrial({ business_id: showExtend!, extra_days: parseInt(extraDays) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agent", "tenants"] });
      setShowExtend(null);
      setToast({ msg: "Trial extended!", ok: true });
    },
    onError: () => setToast({ msg: "Failed to extend trial", ok: false }),
  });

  function daysLeft(expiresAt?: string): number {
    if (!expiresAt) return 0;
    return Math.ceil((new Date(expiresAt).getTime() - now) / 86400000);
  }

  return (
    <div>
      <PageHeader
        title="Trials & Subscriptions"
        description="Manage trials, convert to paying, extend when needed."
      />

      {toast && (
        <div className={`mb-4 rounded-md p-3 text-sm ${toast.ok ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}>
          {toast.msg}
          <button onClick={() => setToast(null)} className="ml-2 font-bold">x</button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active Trials" value={trials.length} icon={Clock} />
        <StatCard title="Paying Tenants" value={paying.length} icon={CheckCircle} />
        <StatCard title="Expiring Soon" value={expiringSoon.length} icon={AlertTriangle} description="Within 14 days" />
        <StatCard title="Conversion Rate" value={
          all.length > 0 ? `${Math.round((paying.length / Math.max(1, paying.length + expired.length)) * 100)}%` : "—"
        } icon={TrendingUp} />
      </div>

      {/* Expiring Soon Alert */}
      {expiringSoon.length > 0 && (
        <Card className="mt-4 border-amber-200 dark:border-amber-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm text-amber-700">
              <AlertTriangle className="h-4 w-4" /> Trials Expiring Soon — Follow Up!
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Business</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead className="text-center">Days Left</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {expiringSoon.map((t) => (
                  <TableRow key={t.business_id}>
                    <TableCell className="font-medium">{t.business_name || t.business_id.slice(0, 8)}</TableCell>
                    <TableCell className="text-xs">{t.combo_name || "—"}</TableCell>
                    <TableCell className="text-center">
                      <Badge variant={daysLeft(t.trial_expires_at) <= 3 ? "destructive" : "gold"}>
                        {daysLeft(t.trial_expires_at)} days
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{t.trial_expires_at ? formatDate(t.trial_expires_at) : "—"}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => convertMut.mutate(t.business_id)} disabled={convertMut.isPending}>
                          Convert
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowExtend(t.business_id)}>
                          Extend
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* All Trials */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-sm">All Trials ({trials.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {trials.length === 0 ? (
            <EmptyState title="No active trials" description="Onboard tenants to start trials" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Business</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead className="text-center">Days Left</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trials.map((t) => (
                  <TableRow key={t.business_id}>
                    <TableCell className="font-medium">{t.business_name || t.business_id.slice(0, 8)}</TableCell>
                    <TableCell className="text-xs">{t.combo_name || "—"}</TableCell>
                    <TableCell className="text-center font-mono">
                      {daysLeft(t.trial_expires_at)}
                    </TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{t.created_at ? formatDate(t.created_at) : "—"}</TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{t.trial_expires_at ? formatDate(t.trial_expires_at) : "—"}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => convertMut.mutate(t.business_id)} disabled={convertMut.isPending}>
                          Convert
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowExtend(t.business_id)}>
                          Extend
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Paying Tenants */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-sm">Paying Tenants ({paying.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {paying.length === 0 ? (
            <EmptyState title="No paying tenants yet" description="Convert trials to start earning" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Business</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead className="text-right">Monthly</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead>Since</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paying.map((t) => (
                  <TableRow key={t.business_id}>
                    <TableCell className="font-medium">{t.business_name || t.business_id.slice(0, 8)}</TableCell>
                    <TableCell className="text-xs">{t.combo_name || "—"}</TableCell>
                    <TableCell className="text-right font-mono">{t.monthly_amount || "—"}</TableCell>
                    <TableCell className="text-xs">{t.currency || "—"}</TableCell>
                    <TableCell className="text-xs text-bos-silver-dark">{t.created_at ? formatDate(t.created_at) : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Extend Dialog */}
      <Dialog open={!!showExtend} onOpenChange={() => setShowExtend(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Extend Trial</DialogTitle></DialogHeader>
          <p className="text-sm text-bos-silver-dark">How many extra days?</p>
          <Input type="number" value={extraDays} onChange={(e) => setExtraDays(e.target.value)} min="1" max="90" />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowExtend(null)}>Cancel</Button>
            <Button onClick={() => extendMut.mutate()} disabled={extendMut.isPending}>
              {extendMut.isPending ? "Extending..." : "Extend Trial"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
