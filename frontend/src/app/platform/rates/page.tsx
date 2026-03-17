"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
} from "@/components/ui";
import { getEffectiveRate, publishRateChange } from "@/lib/api/saas";
import { REGIONS, COUNTRY_TAX_RULES, BOS_SERVICES } from "@/lib/constants";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  Search, TrendingUp, AlertTriangle, Shield, FileText, Building2, Scale,
} from "lucide-react";

export default function BillingTaxGovernancePage() {
  const [activeTab, setActiveTab] = useState<"check" | "publish" | "tax" | "doctrine">("doctrine");
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const tabs = [
    { key: "doctrine" as const, label: "Billing Doctrine" },
    { key: "tax" as const, label: "Tax Rules by Country" },
    { key: "check" as const, label: "Check Effective Rate" },
    { key: "publish" as const, label: "Publish Rate Change" },
  ];

  return (
    <div>
      <PageHeader
        title="Billing & Tax Governance"
        description="Pricing doctrine, tax rules, rate changes, and tenant billing management"
      />

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-bos-silver-light p-1 dark:bg-neutral-800 w-fit flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-white text-bos-purple shadow-sm dark:bg-neutral-900"
                : "text-bos-silver-dark hover:text-neutral-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "doctrine" && <BillingDoctrine />}
      {activeTab === "tax" && <TaxRulesTable />}
      {activeTab === "check" && <EffectiveRateChecker />}
      {activeTab === "publish" && (
        <RateChangePublisher
          onSuccess={() => setToast({ message: "Rate change published", variant: "success" })}
          onError={() => setToast({ message: "Failed to publish", variant: "error" })}
        />
      )}

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

function BillingDoctrine() {
  const rules = [
    {
      icon: Building2,
      title: "Billing Country Determines Tax",
      description: "The payer's country determines which tax rules apply.",
      detail: "HQ Pays → HQ country tax. Branch Pays → each branch's country tax.",
    },
    {
      icon: Scale,
      title: "B2B/B2C Qualification",
      description: "B2B customers with verified tax registration may qualify for reverse charge (0% VAT).",
      detail: "Safe default: charge VAT when verification is incomplete.",
    },
    {
      icon: Shield,
      title: "Safe Default Doctrine",
      description: "When in doubt, charge VAT. Never undercharge — always allow correction later.",
      detail: "Provisional VAT → verification → credit note or adjustment invoice.",
    },
    {
      icon: FileText,
      title: "No Silent Edits or Backdating",
      description: "Invoices are immutable once issued. Corrections via credit note + new invoice only.",
      detail: "Record first, decide later. Every correction creates an auditable paper trail.",
    },
    {
      icon: TrendingUp,
      title: "Rate Change Governance",
      description: "Rate changes require minimum 90 days advance notice.",
      detail: "Existing rate guaranteed through current billing cycle. Decreases take effect immediately.",
    },
    {
      icon: AlertTriangle,
      title: "4-Gate Region Expansion",
      description: "New countries require 4 gates: Country Logic, B2B/B2C Rules, Registration Path, Correction Path.",
      detail: "See Region Expansion Gates page for detailed gate status per country.",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {rules.map((rule) => {
        const Icon = rule.icon;
        return (
          <Card key={rule.title}>
            <CardContent className="p-5">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-bos-purple-light">
                  <Icon className="h-4.5 w-4.5 text-bos-purple" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold">{rule.title}</h3>
                  <p className="mt-0.5 text-xs text-bos-silver-dark">{rule.description}</p>
                  <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400 leading-relaxed">{rule.detail}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function TaxRulesTable() {
  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Country</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Currency</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Tax Name</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">VAT Rate</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-bos-silver-dark">Digital Tax</th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase text-bos-silver-dark">B2B Reverse Charge</th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase text-bos-silver-dark">Registration Required</th>
              </tr>
            </thead>
            <tbody>
              {REGIONS.map((region) => {
                const rules = COUNTRY_TAX_RULES[region.code];
                if (!rules) return null;
                return (
                  <tr key={region.code} className="border-b border-bos-silver/10 hover:bg-bos-silver-light/50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-3 font-medium">{region.name}</td>
                    <td className="px-4 py-3"><Badge variant="outline">{region.currency}</Badge></td>
                    <td className="px-4 py-3">{rules.tax_name}</td>
                    <td className="px-4 py-3 text-right font-mono">{Math.round(rules.vat_rate * 100)}%</td>
                    <td className="px-4 py-3 text-right font-mono">
                      {rules.digital_tax_rate > 0 ? `${(rules.digital_tax_rate * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <StatusBadge status={rules.b2b_reverse_charge ? "ACTIVE" : "INACTIVE"} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <StatusBadge status={rules.registration_required ? "ACTIVE" : "INACTIVE"} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function EffectiveRateChecker() {
  const [businessId, setBusinessId] = useState("");
  const [rate, setRate] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCheck(e: React.FormEvent) {
    e.preventDefault();
    if (!businessId.trim()) return;
    setLoading(true);
    setError("");
    setRate(null);
    try {
      const res = await getEffectiveRate(businessId.trim());
      setRate(res.data ?? res);
    } catch {
      setError("Failed to fetch effective rate");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Search className="h-5 w-5 text-bos-purple" />
            <CardTitle>Check Effective Rate</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCheck} className="flex gap-3">
            <Input
              placeholder="Business ID..."
              value={businessId}
              onChange={(e) => setBusinessId(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={loading}>
              {loading ? "Checking..." : "Check"}
            </Button>
          </form>

          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

          {rate && (
            <div className="mt-4 space-y-3 rounded-lg bg-bos-silver-light p-4 dark:bg-neutral-800">
              <div className="flex justify-between">
                <span className="text-sm text-bos-silver-dark">Effective Rate</span>
                <span className="text-lg font-bold text-bos-gold-dark">
                  {rate.monthly_amount != null
                    ? formatCurrency((rate.monthly_amount as number) * 100, (rate.currency as string) ?? "KES")
                    : "Free (Trial)"}
                </span>
              </div>
              {rate.rate_guaranteed_until ? (
                <div className="flex justify-between">
                  <span className="text-sm text-bos-silver-dark">Rate Guaranteed Until</span>
                  <span className="text-sm font-medium">{formatDate(rate.rate_guaranteed_until as string)}</span>
                </div>
              ) : null}
              {rate.is_trial != null ? (
                <div className="flex justify-between">
                  <span className="text-sm text-bos-silver-dark">Status</span>
                  <StatusBadge status={rate.is_trial ? "TRIAL" : "ACTIVE"} />
                </div>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function RateChangePublisher({ onSuccess, onError }: { onSuccess: () => void; onError: () => void }) {
  const publishMut = useMutation({
    mutationFn: publishRateChange,
    onSuccess,
    onError,
  });

  function handlePublish(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const data = new FormData(form);
    const regionCode = data.get("region_code") as string;
    const region = REGIONS.find((r) => r.code === regionCode);
    publishMut.mutate({
      service_key: data.get("service_key") as string,
      region_code: regionCode,
      old_amount: Number(data.get("old_amount")),
      new_amount: Number(data.get("new_amount")),
      currency: region?.currency ?? "KES",
      effective_from: data.get("effective_from") as string,
    });
  }

  const minDate = new Date();
  minDate.setDate(minDate.getDate() + 90);
  const minDateStr = minDate.toISOString().split("T")[0];

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-bos-purple" />
            <CardTitle>Publish Rate Change</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-orange-50 p-3 text-sm text-orange-800 dark:bg-orange-950 dark:text-orange-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>Rate changes require minimum 90 days advance notice.</span>
          </div>

          <form onSubmit={handlePublish} className="space-y-4">
            <div>
              <Label htmlFor="service_key">Service</Label>
              <Select id="service_key" name="service_key" className="mt-1" required>
                <option value="">Select service...</option>
                {BOS_SERVICES.map((s) => (
                  <option key={s.key} value={s.key}>{s.name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="region_code">Region</Label>
              <Select id="region_code" name="region_code" className="mt-1" required>
                {REGIONS.map((r) => (
                  <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>
                ))}
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="old_amount">Old Amount</Label>
                <Input id="old_amount" name="old_amount" type="number" required className="mt-1" />
              </div>
              <div>
                <Label htmlFor="new_amount">New Amount</Label>
                <Input id="new_amount" name="new_amount" type="number" required className="mt-1" />
              </div>
            </div>
            <div>
              <Label htmlFor="effective_from">Effective From</Label>
              <Input id="effective_from" name="effective_from" type="date" min={minDateStr} required className="mt-1" />
            </div>
            <Button type="submit" disabled={publishMut.isPending} className="w-full">
              {publishMut.isPending ? "Publishing..." : "Publish Rate Change"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
