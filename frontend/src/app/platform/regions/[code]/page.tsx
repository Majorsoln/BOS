"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { StatCard } from "@/components/shared/stat-card";
import { FormDialog } from "@/components/shared/form-dialog";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge, Textarea,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Separator,
} from "@/components/ui";
import {
  getRegionDetail, getRegionPaymentChannels, getRegionSettlementAccounts,
  getRegionDashboard, getRegionResellers, getRegionTerritories,
  setRegionPaymentChannel, removeRegionPaymentChannel, setRegionSettlement,
  launchRegion, suspendRegion, reactivateRegion, sunsetRegion,
} from "@/lib/api/saas";
import { formatDate } from "@/lib/utils";
import {
  ArrowLeft, Globe, CreditCard, Building2, BarChart3, Users, MapPin,
  Plus, Trash2, CheckCircle2, XCircle, Rocket, PauseCircle, PlayCircle,
  Sunset, Wallet, Landmark, Phone, Mail, Clock, Shield, Eye,
  DollarSign, TrendingUp, Activity,
} from "lucide-react";

type TabKey = "overview" | "payment-channels" | "settlements" | "dashboard" | "resellers";
type ToastState = { message: string; variant: "success" | "error" } | null;

const CHANNEL_TYPES = ["MOBILE_MONEY", "CARD", "BANK_TRANSFER", "WALLET", "USSD"];
const PROVIDERS = ["MPESA", "MTN_MOMO", "AIRTEL_MONEY", "FLUTTERWAVE", "PAYSTACK", "STRIPE", "DPO", "PESAPAL", "BANK_DIRECT"];

export default function RegionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const code = params.code as string;

  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [toast, setToast] = useState<ToastState>(null);
  const [showAddChannel, setShowAddChannel] = useState(false);
  const [showAddSettlement, setShowAddSettlement] = useState(false);
  const [removeChannelKey, setRemoveChannelKey] = useState<string | null>(null);

  // Queries
  const detail = useQuery({ queryKey: ["region", code, "detail"], queryFn: () => getRegionDetail(code) });
  const channels = useQuery({ queryKey: ["region", code, "channels"], queryFn: () => getRegionPaymentChannels(code) });
  const settlements = useQuery({ queryKey: ["region", code, "settlements"], queryFn: () => getRegionSettlementAccounts(code) });
  const dashboard = useQuery({ queryKey: ["region", code, "dashboard"], queryFn: () => getRegionDashboard(code), enabled: activeTab === "dashboard" });
  const resellers = useQuery({ queryKey: ["region", code, "resellers"], queryFn: () => getRegionResellers(code), enabled: activeTab === "resellers" });
  const territories = useQuery({ queryKey: ["region", code, "territories"], queryFn: () => getRegionTerritories(code), enabled: activeTab === "resellers" });

  // Mutations
  const addChannelMut = useMutation({
    mutationFn: setRegionPaymentChannel,
    onSuccess: () => {
      setShowAddChannel(false);
      qc.invalidateQueries({ queryKey: ["region", code, "channels"] });
      setToast({ message: "Payment channel added", variant: "success" });
    },
    onError: (err: any) => setToast({ message: err?.response?.data?.error || "Failed to add channel", variant: "error" }),
  });

  const removeChannelMut = useMutation({
    mutationFn: removeRegionPaymentChannel,
    onSuccess: () => {
      setRemoveChannelKey(null);
      qc.invalidateQueries({ queryKey: ["region", code, "channels"] });
      setToast({ message: "Payment channel removed", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to remove channel", variant: "error" }),
  });

  const addSettlementMut = useMutation({
    mutationFn: setRegionSettlement,
    onSuccess: () => {
      setShowAddSettlement(false);
      qc.invalidateQueries({ queryKey: ["region", code, "settlements"] });
      setToast({ message: "Settlement account added", variant: "success" });
    },
    onError: (err: any) => setToast({ message: err?.response?.data?.error || "Failed to add settlement", variant: "error" }),
  });

  const launchMut = useMutation({
    mutationFn: launchRegion,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["region", code] }); qc.invalidateQueries({ queryKey: ["saas", "regions"] }); setToast({ message: "Region launched!", variant: "success" }); },
    onError: (err: any) => setToast({ message: err?.response?.data?.error || "Launch failed", variant: "error" }),
  });

  const suspendMut = useMutation({
    mutationFn: suspendRegion,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["region", code] }); qc.invalidateQueries({ queryKey: ["saas", "regions"] }); setToast({ message: "Region suspended", variant: "success" }); },
    onError: () => setToast({ message: "Failed to suspend", variant: "error" }),
  });

  const reactivateMut = useMutation({
    mutationFn: reactivateRegion,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["region", code] }); qc.invalidateQueries({ queryKey: ["saas", "regions"] }); setToast({ message: "Region reactivated", variant: "success" }); },
    onError: () => setToast({ message: "Failed to reactivate", variant: "error" }),
  });

  const region = detail.data?.data?.region;
  const status = region?.status || "DRAFT";

  const tabs: { key: TabKey; label: string; icon: typeof Globe }[] = [
    { key: "overview", label: "Overview", icon: Globe },
    { key: "payment-channels", label: "Payment Channels", icon: CreditCard },
    { key: "settlements", label: "Settlement Accounts", icon: Landmark },
    { key: "dashboard", label: "Dashboard", icon: BarChart3 },
    { key: "resellers", label: "Resellers & Territories", icon: Users },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => router.push("/platform/regions")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{region?.name || code}</h1>
            <span className="rounded bg-bos-purple/10 px-2 py-0.5 text-sm font-bold text-bos-purple">{code}</span>
            <StatusBadge status={status} />
          </div>
          <p className="text-sm text-bos-silver-dark mt-0.5">
            {region?.currency || "—"} &middot; {region?.tax_name || "VAT"} {region?.vat_rate ? `${Math.round(region.vat_rate * 100)}%` : ""}
            {region?.timezone && <> &middot; {region.timezone}</>}
          </p>
        </div>
        {/* Lifecycle Actions */}
        <div className="flex gap-2">
          {(status === "DRAFT" || status === "PILOT") && (
            <Button size="sm" onClick={() => launchMut.mutate({ region_code: code })} className="gap-1 bg-green-600 hover:bg-green-700" disabled={launchMut.isPending}>
              <Rocket className="h-4 w-4" /> {status === "DRAFT" ? "Launch" : "Go Live"}
            </Button>
          )}
          {status === "ACTIVE" && (
            <Button size="sm" variant="outline" onClick={() => suspendMut.mutate({ region_code: code, reason: "Admin action" })} className="gap-1 text-orange-600 border-orange-300" disabled={suspendMut.isPending}>
              <PauseCircle className="h-4 w-4" /> Suspend
            </Button>
          )}
          {status === "SUSPENDED" && (
            <Button size="sm" onClick={() => reactivateMut.mutate({ region_code: code })} className="gap-1 bg-green-600 hover:bg-green-700" disabled={reactivateMut.isPending}>
              <PlayCircle className="h-4 w-4" /> Reactivate
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-bos-silver-light p-1 dark:bg-neutral-800 w-fit flex-wrap">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "bg-white text-bos-purple shadow-sm dark:bg-neutral-900"
                  : "text-bos-silver-dark hover:text-neutral-900"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && <OverviewTab region={region} />}
      {activeTab === "payment-channels" && (
        <PaymentChannelsTab
          code={code}
          channels={channels.data?.data?.channels ?? []}
          loading={channels.isLoading}
          onAdd={() => setShowAddChannel(true)}
          onRemove={setRemoveChannelKey}
        />
      )}
      {activeTab === "settlements" && (
        <SettlementsTab
          code={code}
          accounts={settlements.data?.data?.accounts ?? []}
          loading={settlements.isLoading}
          onAdd={() => setShowAddSettlement(true)}
        />
      )}
      {activeTab === "dashboard" && (
        <DashboardTab data={dashboard.data?.data} loading={dashboard.isLoading} />
      )}
      {activeTab === "resellers" && (
        <ResellersTab
          resellers={resellers.data?.data?.resellers ?? []}
          territories={territories.data?.data?.territories ?? []}
          loading={resellers.isLoading}
        />
      )}

      {/* Add Payment Channel Dialog */}
      <FormDialog
        open={showAddChannel}
        onClose={() => setShowAddChannel(false)}
        title="Add Payment Channel"
        description={`Configure a new payment method for ${code}`}
        onSubmit={(e) => {
          e.preventDefault();
          const d = new FormData(e.target as HTMLFormElement);
          addChannelMut.mutate({
            region_code: code,
            channel_key: (d.get("channel_key") as string).toLowerCase().replace(/\s+/g, "_"),
            display_name: d.get("display_name") as string,
            provider: d.get("provider") as string,
            channel_type: d.get("channel_type") as string,
            is_active: d.get("is_active") === "true",
            min_amount: parseInt(d.get("min_amount") as string) || 0,
            max_amount: parseInt(d.get("max_amount") as string) || 0,
            settlement_delay_days: parseInt(d.get("settlement_delay_days") as string) || 1,
          });
        }}
        submitLabel="Add Channel"
        loading={addChannelMut.isPending}
        wide
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="ch_key">Channel Key</Label>
            <Input id="ch_key" name="channel_key" required placeholder="e.g. mpesa_ke" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="ch_display">Display Name</Label>
            <Input id="ch_display" name="display_name" required placeholder="e.g. M-Pesa Kenya" className="mt-1" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="ch_provider">Provider</Label>
            <Select id="ch_provider" name="provider" required className="mt-1">
              <option value="">Select provider...</option>
              {PROVIDERS.map((p) => <option key={p} value={p}>{p.replace(/_/g, " ")}</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="ch_type">Channel Type</Label>
            <Select id="ch_type" name="channel_type" required className="mt-1">
              <option value="">Select type...</option>
              {CHANNEL_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="ch_min">Min Amount (minor units)</Label>
            <Input id="ch_min" name="min_amount" type="number" min="0" placeholder="100" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="ch_max">Max Amount (minor units)</Label>
            <Input id="ch_max" name="max_amount" type="number" min="0" placeholder="15000000" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="ch_delay">Settlement Delay (days)</Label>
            <Input id="ch_delay" name="settlement_delay_days" type="number" min="0" max="30" defaultValue="1" className="mt-1" />
          </div>
        </div>
        <div>
          <Label htmlFor="ch_active">Status</Label>
          <Select id="ch_active" name="is_active" defaultValue="true" className="mt-1">
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </Select>
        </div>
      </FormDialog>

      {/* Remove Channel Confirmation */}
      <ConfirmDialog
        open={!!removeChannelKey}
        onClose={() => setRemoveChannelKey(null)}
        title="Remove Payment Channel?"
        description={`This will remove "${removeChannelKey}" from ${code}. Tenants using this channel will no longer be able to pay through it.`}
        confirmLabel="Remove Channel"
        onConfirm={() => removeChannelKey && removeChannelMut.mutate({ region_code: code, channel_key: removeChannelKey })}
        loading={removeChannelMut.isPending}
      />

      {/* Add Settlement Account Dialog */}
      <FormDialog
        open={showAddSettlement}
        onClose={() => setShowAddSettlement(false)}
        title="Add Settlement Account"
        description={`Add a bank account where ${code} funds will settle`}
        onSubmit={(e) => {
          e.preventDefault();
          const d = new FormData(e.target as HTMLFormElement);
          addSettlementMut.mutate({
            region_code: code,
            bank_name: d.get("bank_name") as string,
            account_name: d.get("account_name") as string,
            account_number: d.get("account_number") as string,
            branch_code: d.get("branch_code") as string || undefined,
            swift_code: d.get("swift_code") as string || undefined,
            currency: d.get("currency") as string,
            is_primary: d.get("is_primary") === "true",
          });
        }}
        submitLabel="Add Account"
        loading={addSettlementMut.isPending}
        wide
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="st_bank">Bank Name</Label>
            <Input id="st_bank" name="bank_name" required placeholder="e.g. Equity Bank" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="st_name">Account Name</Label>
            <Input id="st_name" name="account_name" required placeholder="e.g. BOS Kenya Operations" className="mt-1" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="st_number">Account Number</Label>
            <Input id="st_number" name="account_number" required placeholder="e.g. 0180-123-456789" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="st_currency">Currency</Label>
            <Input id="st_currency" name="currency" required placeholder="e.g. KES" className="mt-1" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="st_branch">Branch Code</Label>
            <Input id="st_branch" name="branch_code" placeholder="Optional" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="st_swift">SWIFT Code</Label>
            <Input id="st_swift" name="swift_code" placeholder="e.g. EABORKENX" className="mt-1" />
          </div>
          <div>
            <Label htmlFor="st_primary">Primary Account</Label>
            <Select id="st_primary" name="is_primary" defaultValue="false" className="mt-1">
              <option value="true">Yes</option>
              <option value="false">No</option>
            </Select>
          </div>
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

/* ── Overview Tab ─────────────────────────────────────────── */

function OverviewTab({ region }: { region: any }) {
  if (!region) return <Card className="p-8 text-center text-bos-silver-dark">Loading region details...</Card>;

  const sections = [
    {
      title: "Identity",
      icon: Globe,
      fields: [
        { label: "Country Code", value: region.code },
        { label: "Country Name", value: region.name },
        { label: "Currency", value: region.currency },
        { label: "Status", value: region.status || "DRAFT", badge: true },
      ],
    },
    {
      title: "Tax & Compliance",
      icon: Shield,
      fields: [
        { label: "Tax Name", value: region.tax_name || "VAT" },
        { label: "VAT Rate", value: region.vat_rate != null ? `${Math.round(region.vat_rate * 100)}%` : "—" },
        { label: "Digital Tax Rate", value: region.digital_tax_rate ? `${(region.digital_tax_rate * 100).toFixed(1)}%` : "None" },
        { label: "B2B Reverse Charge", value: region.b2b_reverse_charge ? "Yes" : "No" },
        { label: "Registration Required", value: region.registration_required ? "Yes" : "No" },
        { label: "Regulatory Body", value: region.regulatory_body || "—" },
        { label: "Business License Required", value: region.business_license_required ? "Yes" : "No" },
        { label: "Data Residency Required", value: region.data_residency_required ? "Yes" : "No" },
      ],
    },
    {
      title: "Operations",
      icon: Clock,
      fields: [
        { label: "Default Language", value: region.default_language || "en" },
        { label: "Timezone", value: region.timezone || "—" },
        { label: "Calling Code", value: region.country_calling_code || "—" },
        { label: "Phone Format", value: region.phone_format || "—" },
        { label: "Support Phone", value: region.support_phone || "—" },
        { label: "Support Email", value: region.support_email || "—" },
        { label: "Support Hours", value: region.support_hours || "—" },
      ],
    },
    {
      title: "Financial",
      icon: DollarSign,
      fields: [
        { label: "Min Payout Amount", value: region.min_payout_amount != null ? region.min_payout_amount.toLocaleString() : "—" },
        { label: "Payout Currency", value: region.payout_currency || region.currency || "—" },
      ],
    },
    {
      title: "Launch Management",
      icon: Rocket,
      fields: [
        { label: "Launched At", value: region.launched_at ? formatDate(region.launched_at) : "—" },
        { label: "Suspended At", value: region.suspended_at ? formatDate(region.suspended_at) : "—" },
        { label: "Sunset At", value: region.sunset_at ? formatDate(region.sunset_at) : "—" },
        { label: "Pilot Tenant Limit", value: region.pilot_tenant_limit ?? "—" },
        { label: "Pilot Tenants", value: region.pilot_tenant_count ?? 0 },
        { label: "Launch Notes", value: region.launch_notes || "—" },
      ],
    },
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {sections.map((section) => {
        const Icon = section.icon;
        return (
          <Card key={section.title}>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-bos-purple" />
                <CardTitle className="text-sm">{section.title}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <dl className="space-y-2">
                {section.fields.map((f) => (
                  <div key={f.label} className="flex justify-between text-sm">
                    <dt className="text-bos-silver-dark">{f.label}</dt>
                    <dd className="font-medium text-right max-w-[60%] truncate">
                      {f.badge ? <StatusBadge status={f.value} /> : f.value}
                    </dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

/* ── Payment Channels Tab ─────────────────────────────────── */

interface PaymentChannel {
  channel_key: string;
  display_name: string;
  provider: string;
  channel_type: string;
  is_active: boolean;
  min_amount?: number;
  max_amount?: number;
  settlement_delay_days?: number;
}

function PaymentChannelsTab({
  code, channels, loading, onAdd, onRemove,
}: {
  code: string;
  channels: PaymentChannel[];
  loading: boolean;
  onAdd: () => void;
  onRemove: (key: string) => void;
}) {
  const activeChannels = channels.filter((c) => c.is_active);

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-bos-silver-dark">
            {channels.length} channel{channels.length !== 1 ? "s" : ""} configured &middot; {activeChannels.length} active
          </p>
        </div>
        <Button onClick={onAdd} className="gap-2" size="sm">
          <Plus className="h-4 w-4" /> Add Channel
        </Button>
      </div>

      {/* Channel Cards */}
      {loading ? (
        <Card className="p-8 text-center text-bos-silver-dark">Loading payment channels...</Card>
      ) : channels.length === 0 ? (
        <EmptyState
          title="No Payment Channels"
          description="Configure at least one payment channel before launching this region."
          action={
            <Button onClick={onAdd} className="gap-2">
              <Plus className="h-4 w-4" /> Add First Channel
            </Button>
          }
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {channels.map((ch) => (
            <Card key={ch.channel_key} className={!ch.is_active ? "opacity-60" : ""}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-bos-purple/10">
                      {ch.channel_type === "MOBILE_MONEY" ? (
                        <Phone className="h-4 w-4 text-bos-purple" />
                      ) : ch.channel_type === "CARD" ? (
                        <CreditCard className="h-4 w-4 text-bos-purple" />
                      ) : ch.channel_type === "BANK_TRANSFER" ? (
                        <Landmark className="h-4 w-4 text-bos-purple" />
                      ) : (
                        <Wallet className="h-4 w-4 text-bos-purple" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-sm">{ch.display_name}</p>
                      <p className="text-xs text-bos-silver-dark">{ch.provider.replace(/_/g, " ")}</p>
                    </div>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => onRemove(ch.channel_key)} className="text-red-500 hover:text-red-700 h-7 w-7 p-0">
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <Separator className="my-3" />
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-bos-silver-dark">Type</span>
                    <Badge variant="outline" className="text-[10px]">{ch.channel_type.replace(/_/g, " ")}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-bos-silver-dark">Status</span>
                    <span>{ch.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="secondary">Inactive</Badge>}</span>
                  </div>
                  {ch.min_amount != null && ch.min_amount > 0 && (
                    <div className="flex justify-between">
                      <span className="text-bos-silver-dark">Min Amount</span>
                      <span className="font-mono">{ch.min_amount.toLocaleString()}</span>
                    </div>
                  )}
                  {ch.max_amount != null && ch.max_amount > 0 && (
                    <div className="flex justify-between">
                      <span className="text-bos-silver-dark">Max Amount</span>
                      <span className="font-mono">{ch.max_amount.toLocaleString()}</span>
                    </div>
                  )}
                  {ch.settlement_delay_days != null && (
                    <div className="flex justify-between">
                      <span className="text-bos-silver-dark">Settlement</span>
                      <span>{ch.settlement_delay_days} day{ch.settlement_delay_days !== 1 ? "s" : ""}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Settlement Accounts Tab ──────────────────────────────── */

interface SettlementAccount {
  bank_name: string;
  account_name: string;
  account_number: string;
  branch_code?: string;
  swift_code?: string;
  currency: string;
  is_primary: boolean;
}

function SettlementsTab({
  code, accounts, loading, onAdd,
}: {
  code: string;
  accounts: SettlementAccount[];
  loading: boolean;
  onAdd: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-bos-silver-dark">
          {accounts.length} settlement account{accounts.length !== 1 ? "s" : ""} configured
        </p>
        <Button onClick={onAdd} className="gap-2" size="sm">
          <Plus className="h-4 w-4" /> Add Account
        </Button>
      </div>

      {loading ? (
        <Card className="p-8 text-center text-bos-silver-dark">Loading settlement accounts...</Card>
      ) : accounts.length === 0 ? (
        <EmptyState
          title="No Settlement Accounts"
          description="Add a bank account where collected funds from this region will be deposited."
          action={
            <Button onClick={onAdd} className="gap-2">
              <Plus className="h-4 w-4" /> Add Account
            </Button>
          }
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {accounts.map((acc, i) => (
            <Card key={i} className={acc.is_primary ? "ring-2 ring-bos-purple/30" : ""}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
                      <Landmark className="h-4 w-4 text-green-600" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{acc.bank_name}</p>
                      <p className="text-xs text-bos-silver-dark">{acc.account_name}</p>
                    </div>
                  </div>
                  {acc.is_primary && <Badge variant="purple">Primary</Badge>}
                </div>
                <Separator className="my-3" />
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-bos-silver-dark">Account Number</span>
                    <span className="font-mono">{acc.account_number}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-bos-silver-dark">Currency</span>
                    <Badge variant="outline">{acc.currency}</Badge>
                  </div>
                  {acc.branch_code && (
                    <div className="flex justify-between">
                      <span className="text-bos-silver-dark">Branch Code</span>
                      <span className="font-mono">{acc.branch_code}</span>
                    </div>
                  )}
                  {acc.swift_code && (
                    <div className="flex justify-between">
                      <span className="text-bos-silver-dark">SWIFT</span>
                      <span className="font-mono">{acc.swift_code}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Dashboard Tab ────────────────────────────────────────── */

function DashboardTab({ data, loading }: { data: any; loading: boolean }) {
  if (loading) return <Card className="p-8 text-center text-bos-silver-dark">Loading dashboard...</Card>;
  if (!data) return <EmptyState title="No dashboard data available" description="Dashboard data will appear once the region has active tenants." />;

  const pricing = data.pricing || {};
  const reseller = data.reseller || {};
  const financial = data.financial || {};

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard title="Active Combos" value={pricing.active_combos ?? 0} icon={Activity} />
        <StatCard title="Resellers" value={reseller.total_resellers ?? 0} icon={Users} />
        <StatCard title="Paying Tenants" value={reseller.paying_tenants ?? 0} icon={TrendingUp} />
        <StatCard title="Payment Channels" value={financial.payment_channels ?? 0} icon={CreditCard} />
      </div>

      {/* Pricing Info */}
      {pricing.rates && pricing.rates.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Combo Pricing in this Region</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-bos-silver-light/50 dark:bg-neutral-900 hover:bg-bos-silver-light/50">
                  <TableHead>Combo</TableHead>
                  <TableHead className="text-right">Monthly Rate</TableHead>
                  <TableHead>Currency</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pricing.rates.map((r: any, i: number) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{r.combo_id || r.combo_name || "—"}</TableCell>
                    <TableCell className="text-right font-mono">{(r.monthly_amount ?? 0).toLocaleString()}</TableCell>
                    <TableCell><Badge variant="outline">{r.currency}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Reseller Performance */}
      {reseller.resellers && reseller.resellers.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Resellers in this Region</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-bos-silver-light/50 dark:bg-neutral-900 hover:bg-bos-silver-light/50">
                  <TableHead>Name</TableHead>
                  <TableHead className="text-center">Tier</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Tenants</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reseller.resellers.map((r: any, i: number) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{r.name || r.reseller_id}</TableCell>
                    <TableCell className="text-center"><StatusBadge status={r.tier || "BRONZE"} /></TableCell>
                    <TableCell className="text-center"><StatusBadge status={r.status || "ACTIVE"} /></TableCell>
                    <TableCell className="text-right font-mono">{r.active_tenants ?? 0}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Financial Summary */}
      {financial.settlement_accounts && financial.settlement_accounts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Settlement Accounts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {financial.settlement_accounts.map((acc: any, i: number) => (
                <div key={i} className="flex items-center justify-between rounded-lg border border-bos-silver/30 p-3 dark:border-bos-silver/20">
                  <div className="flex items-center gap-2">
                    <Landmark className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium">{acc.bank_name}</span>
                    <span className="text-xs text-bos-silver-dark">{acc.account_number}</span>
                  </div>
                  {acc.is_primary && <Badge variant="purple">Primary</Badge>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ── Resellers & Territories Tab ──────────────────────────── */

function ResellersTab({
  resellers, territories, loading,
}: {
  resellers: any[];
  territories: any[];
  loading: boolean;
}) {
  if (loading) return <Card className="p-8 text-center text-bos-silver-dark">Loading resellers...</Card>;

  return (
    <div className="space-y-6">
      {/* Resellers List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Resellers ({resellers.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {resellers.length === 0 ? (
            <div className="p-8 text-center text-bos-silver-dark">No resellers assigned to this region</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-bos-silver-light/50 dark:bg-neutral-900 hover:bg-bos-silver-light/50">
                  <TableHead>Reseller</TableHead>
                  <TableHead className="text-center">Tier</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-right">Active Tenants</TableHead>
                  <TableHead className="text-right">Commission Earned</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {resellers.map((r: any, i: number) => (
                  <TableRow key={i}>
                    <TableCell>
                      <div>
                        <p className="font-medium text-sm">{r.name || r.reseller_id}</p>
                        {r.contact_email && <p className="text-xs text-bos-silver-dark">{r.contact_email}</p>}
                      </div>
                    </TableCell>
                    <TableCell className="text-center"><StatusBadge status={r.tier || "BRONZE"} /></TableCell>
                    <TableCell className="text-center"><StatusBadge status={r.status || "ACTIVE"} /></TableCell>
                    <TableCell className="text-right font-mono">{r.active_tenants ?? 0}</TableCell>
                    <TableCell className="text-right font-mono">{(r.total_commission ?? 0).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Territories */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Territories ({territories.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {territories.length === 0 ? (
            <div className="p-8 text-center text-bos-silver-dark">No territories defined for this region</div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {territories.map((t: any, i: number) => (
                <div key={i} className="flex items-center justify-between rounded-lg border border-bos-silver/30 p-3 dark:border-bos-silver/20">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-bos-purple" />
                    <div>
                      <p className="text-sm font-medium">{t.territory_name || t.territory_id}</p>
                      {t.reseller_name && <p className="text-xs text-bos-silver-dark">Assigned: {t.reseller_name}</p>}
                    </div>
                  </div>
                  <Badge variant={t.is_active ? "success" : "secondary"}>{t.is_active ? "Active" : "Inactive"}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
