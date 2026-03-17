"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast,
} from "@/components/ui";
import { onboardTenant } from "@/lib/api/agents";
import {
  REGIONS, BUSINESS_TYPES, AI_USAGE_TIERS, DOCUMENT_VOLUME_TIERS,
  PAYER_MODELS, BUYER_TYPES,
} from "@/lib/constants";
import { UserPlus, Building2, Settings, Check } from "lucide-react";

type Step = 1 | 2 | 3;

export default function OnboardTenantPage() {
  const [step, setStep] = useState<Step>(1);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);
  const [form, setForm] = useState({
    business_name: "",
    business_type: "",
    country: "",
    city: "",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    service_category: "",
    estimated_doc_volume: "tier1",
    ai_tier: "none",
    branch_count: 1,
    billing_model: "HQ_PAYS",
    buyer_type: "B2C",
    tax_number: "",
  });

  const update = (partial: Partial<typeof form>) => setForm((prev) => ({ ...prev, ...partial }));

  const onboardMut = useMutation({
    mutationFn: onboardTenant,
    onSuccess: () => {
      setToast({ message: "Tenant onboarded successfully!", variant: "success" });
      setStep(1);
      setForm({
        business_name: "", business_type: "", country: "", city: "",
        contact_name: "", contact_email: "", contact_phone: "",
        service_category: "", estimated_doc_volume: "tier1", ai_tier: "none",
        branch_count: 1, billing_model: "HQ_PAYS", buyer_type: "B2C", tax_number: "",
      });
    },
    onError: () => setToast({ message: "Failed to onboard tenant", variant: "error" }),
  });

  function handleSubmit() {
    onboardMut.mutate(form);
  }

  return (
    <div>
      <PageHeader
        title="Onboard New Tenant"
        description="Sign up a new tenant under your attribution"
      />

      {/* Step Indicator */}
      <div className="mb-6 flex items-center gap-4">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
              step >= s ? "bg-bos-purple text-white" : "bg-bos-silver-light text-bos-silver-dark"
            }`}>
              {step > s ? <Check className="h-4 w-4" /> : s}
            </div>
            <span className="text-sm font-medium">
              {s === 1 ? "Business Info" : s === 2 ? "Plan Selection" : "Review"}
            </span>
            {s < 3 && <div className="h-px w-8 bg-bos-silver/30" />}
          </div>
        ))}
      </div>

      {/* Step 1: Business Information */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Business Information</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="business_name">Business Name</Label>
              <Input id="business_name" value={form.business_name} onChange={(e) => update({ business_name: e.target.value })} required className="mt-1" />
            </div>
            <div>
              <Label htmlFor="business_type">Business Type</Label>
              <Select id="business_type" value={form.business_type} onChange={(e) => update({ business_type: e.target.value, service_category: e.target.value })} className="mt-1" required>
                <option value="">Select type...</option>
                {BUSINESS_TYPES.map((bt) => <option key={bt.key} value={bt.key}>{bt.label}</option>)}
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="country">Country</Label>
                <Select id="country" value={form.country} onChange={(e) => update({ country: e.target.value })} className="mt-1" required>
                  <option value="">Select...</option>
                  {REGIONS.map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
                </Select>
              </div>
              <div>
                <Label htmlFor="city">City</Label>
                <Input id="city" value={form.city} onChange={(e) => update({ city: e.target.value })} required className="mt-1" />
              </div>
            </div>
            <div>
              <Label htmlFor="contact_name">Contact Name</Label>
              <Input id="contact_name" value={form.contact_name} onChange={(e) => update({ contact_name: e.target.value })} required className="mt-1" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="contact_email">Email</Label>
                <Input id="contact_email" type="email" value={form.contact_email} onChange={(e) => update({ contact_email: e.target.value })} required className="mt-1" />
              </div>
              <div>
                <Label htmlFor="contact_phone">Phone</Label>
                <Input id="contact_phone" value={form.contact_phone} onChange={(e) => update({ contact_phone: e.target.value })} required className="mt-1" placeholder="+254..." />
              </div>
            </div>
            <Button onClick={() => setStep(2)} disabled={!form.business_name || !form.business_type || !form.country || !form.contact_name || !form.contact_email}>
              Next: Plan Selection
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Plan Selection */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Settings className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Plan Selection</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="doc_volume">Estimated Document Volume</Label>
              <Select id="doc_volume" value={form.estimated_doc_volume} onChange={(e) => update({ estimated_doc_volume: e.target.value })} className="mt-1">
                {DOCUMENT_VOLUME_TIERS.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
              </Select>
            </div>
            <div>
              <Label htmlFor="ai_tier">AI Usage</Label>
              <Select id="ai_tier" value={form.ai_tier} onChange={(e) => update({ ai_tier: e.target.value })} className="mt-1">
                {AI_USAGE_TIERS.map((t) => <option key={t.key} value={t.key}>{t.label} — {t.description}</option>)}
              </Select>
            </div>
            <div>
              <Label htmlFor="branch_count">Number of Branches</Label>
              <Input id="branch_count" type="number" min={1} max={50} value={form.branch_count} onChange={(e) => update({ branch_count: Number(e.target.value) })} className="mt-1" />
            </div>
            <div>
              <Label htmlFor="billing_model">Billing Model</Label>
              <Select id="billing_model" value={form.billing_model} onChange={(e) => update({ billing_model: e.target.value })} className="mt-1">
                {PAYER_MODELS.map((p) => <option key={p.value} value={p.value}>{p.label} — {p.description}</option>)}
              </Select>
            </div>
            <div>
              <Label htmlFor="buyer_type">Buyer Type</Label>
              <Select id="buyer_type" value={form.buyer_type} onChange={(e) => update({ buyer_type: e.target.value })} className="mt-1">
                {BUYER_TYPES.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}
              </Select>
            </div>
            {(form.buyer_type === "B2B" || form.buyer_type === "PENDING") && (
              <div>
                <Label htmlFor="tax_number">Tax Registration Number</Label>
                <Input id="tax_number" value={form.tax_number} onChange={(e) => update({ tax_number: e.target.value })} className="mt-1" />
              </div>
            )}
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
              <Button onClick={() => setStep(3)}>Next: Review</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Review & Confirm */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <UserPlus className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Review & Confirm</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <InfoRow label="Business Name" value={form.business_name} />
              <InfoRow label="Business Type" value={BUSINESS_TYPES.find((b) => b.key === form.business_type)?.label ?? form.business_type} />
              <InfoRow label="Country" value={REGIONS.find((r) => r.code === form.country)?.name ?? form.country} />
              <InfoRow label="City" value={form.city} />
              <InfoRow label="Contact" value={form.contact_name} />
              <InfoRow label="Email" value={form.contact_email} />
              <InfoRow label="Document Volume" value={DOCUMENT_VOLUME_TIERS.find((t) => t.key === form.estimated_doc_volume)?.label ?? ""} />
              <InfoRow label="AI Tier" value={AI_USAGE_TIERS.find((t) => t.key === form.ai_tier)?.label ?? ""} />
              <InfoRow label="Branches" value={String(form.branch_count)} />
              <InfoRow label="Billing Model" value={PAYER_MODELS.find((p) => p.value === form.billing_model)?.label ?? ""} />
              <InfoRow label="Buyer Type" value={BUYER_TYPES.find((b) => b.value === form.buyer_type)?.label ?? ""} />
              {form.tax_number && <InfoRow label="Tax Number" value={form.tax_number} />}
            </div>
            <div className="mt-6 flex gap-3">
              <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
              <Button onClick={handleSubmit} disabled={onboardMut.isPending}>
                {onboardMut.isPending ? "Onboarding..." : "Confirm & Onboard"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-bos-silver-dark">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}
