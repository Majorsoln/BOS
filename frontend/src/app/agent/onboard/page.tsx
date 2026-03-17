"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
} from "@/components/ui";
import { onboardTenant } from "@/lib/api/agents";
import {
  REGIONS, BOS_SERVICES, CAPACITY_DIMENSIONS, PAYER_MODELS, BUYER_TYPES,
} from "@/lib/constants";
import { UserPlus, Building2, Settings, Check, Package } from "lucide-react";

type Step = 1 | 2 | 3 | 4;

const DEFAULT_CAPACITY = {
  branches: "BRANCH_1",
  documents: "DOC_500",
  users: "USER_3",
  ai_tokens: "AI_NONE",
};

export default function OnboardTenantPage() {
  const [step, setStep] = useState<Step>(1);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);
  const [form, setForm] = useState({
    business_name: "",
    country: "",
    city: "",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    services: [] as string[],
    capacity: { ...DEFAULT_CAPACITY },
    billing_model: "HQ_PAYS",
    buyer_type: "B2C",
    tax_number: "",
    trial_days: 30,
  });

  const update = (partial: Partial<typeof form>) => setForm((prev) => ({ ...prev, ...partial }));

  const toggleService = (key: string) => {
    setForm((prev) => ({
      ...prev,
      services: prev.services.includes(key)
        ? prev.services.filter((s) => s !== key)
        : [...prev.services, key],
    }));
  };

  const updateCapacity = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, capacity: { ...prev.capacity, [key]: value } }));
  };

  const onboardMut = useMutation({
    mutationFn: onboardTenant,
    onSuccess: () => {
      setToast({ message: "Tenant onboarded successfully!", variant: "success" });
      setStep(1);
      setForm({
        business_name: "", country: "", city: "",
        contact_name: "", contact_email: "", contact_phone: "",
        services: [], capacity: { ...DEFAULT_CAPACITY },
        billing_model: "HQ_PAYS", buyer_type: "B2C", tax_number: "", trial_days: 30,
      });
    },
    onError: () => setToast({ message: "Failed to onboard tenant", variant: "error" }),
  });

  function handleSubmit() {
    onboardMut.mutate({
      business_name: form.business_name,
      business_type: form.services[0] ?? "",
      country: form.country,
      city: form.city,
      contact_name: form.contact_name,
      contact_email: form.contact_email,
      contact_phone: form.contact_phone,
      service_category: form.services.join(","),
      estimated_doc_volume: form.capacity.documents,
      ai_tier: form.capacity.ai_tokens,
      branch_count: Number(CAPACITY_DIMENSIONS[0].tiers.find((t) => t.key === form.capacity.branches)?.limit ?? 1),
      billing_model: form.billing_model,
      buyer_type: form.buyer_type,
      tax_number: form.tax_number || undefined,
    });
  }

  const steps = ["Business Info", "Services", "Capacity", "Review"];

  return (
    <div>
      <PageHeader
        title="Onboard New Tenant"
        description="Sign up a new tenant under your attribution"
      />

      {/* Step Indicator */}
      <div className="mb-6 flex items-center gap-3">
        {steps.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
              step > i + 1 ? "bg-bos-purple text-white" : step === i + 1 ? "bg-bos-purple text-white" : "bg-bos-silver-light text-bos-silver-dark"
            }`}>
              {step > i + 1 ? <Check className="h-4 w-4" /> : i + 1}
            </div>
            <span className="text-sm font-medium">{label}</span>
            {i < 3 && <div className="h-px w-6 bg-bos-silver/30" />}
          </div>
        ))}
      </div>

      {/* Step 1: Business Info */}
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
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="billing_model">Billing Model</Label>
                <Select id="billing_model" value={form.billing_model} onChange={(e) => update({ billing_model: e.target.value })} className="mt-1">
                  {PAYER_MODELS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
                </Select>
              </div>
              <div>
                <Label htmlFor="buyer_type">Buyer Type</Label>
                <Select id="buyer_type" value={form.buyer_type} onChange={(e) => update({ buyer_type: e.target.value })} className="mt-1">
                  {BUYER_TYPES.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}
                </Select>
              </div>
            </div>
            {(form.buyer_type === "B2B") && (
              <div>
                <Label htmlFor="tax_number">Tax Registration Number</Label>
                <Input id="tax_number" value={form.tax_number} onChange={(e) => update({ tax_number: e.target.value })} className="mt-1" />
              </div>
            )}
            <div>
              <Label htmlFor="trial_days">Trial Days</Label>
              <Input id="trial_days" type="number" min={7} max={90} value={form.trial_days} onChange={(e) => update({ trial_days: Number(e.target.value) })} className="mt-1" />
              <p className="mt-1 text-xs text-bos-silver-dark">First onboarding is FREE. Set trial period within policy limits.</p>
            </div>
            <Button onClick={() => setStep(2)} disabled={!form.business_name || !form.country || !form.contact_name || !form.contact_email}>
              Next: Select Services
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Services */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Package className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Select Services</CardTitle>
            </div>
            <p className="text-xs text-bos-silver-dark mt-1">
              Choose one or more services. Each gives the tenant full features for that business type.
              Multi-service plans get a reduction rate.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {BOS_SERVICES.map((svc) => {
              const selected = form.services.includes(svc.key);
              return (
                <div
                  key={svc.key}
                  onClick={() => toggleService(svc.key)}
                  className={`cursor-pointer rounded-lg border-2 p-4 transition-colors ${
                    selected
                      ? "border-bos-purple bg-bos-purple/5"
                      : "border-bos-silver/20 hover:border-bos-silver/40"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold">{svc.name}</h3>
                        {selected && <Badge variant="purple">Selected</Badge>}
                      </div>
                      <p className="mt-1 text-xs text-bos-silver-dark">{svc.description}</p>
                    </div>
                    <div className={`flex h-6 w-6 items-center justify-center rounded-full border-2 ${
                      selected ? "border-bos-purple bg-bos-purple text-white" : "border-bos-silver/30"
                    }`}>
                      {selected && <Check className="h-3 w-3" />}
                    </div>
                  </div>
                </div>
              );
            })}

            {form.services.length > 1 && (
              <div className="rounded-md bg-bos-purple/5 p-3 text-xs text-bos-purple">
                {form.services.length} services selected — multi-service reduction rate applies
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
              <Button onClick={() => setStep(3)} disabled={form.services.length === 0}>
                Next: Capacity
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Capacity */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Settings className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Capacity & Consumption</CardTitle>
            </div>
            <p className="text-xs text-bos-silver-dark mt-1">
              Select capacity tiers. These are charged on top of the service fees.
            </p>
          </CardHeader>
          <CardContent className="space-y-5">
            {CAPACITY_DIMENSIONS.map((dim) => {
              const dimKey = dim.key.toLowerCase() as keyof typeof form.capacity;
              return (
                <div key={dim.key}>
                  <Label>{dim.label}</Label>
                  <p className="text-xs text-bos-silver-dark mb-1">{dim.description}</p>
                  <Select
                    value={form.capacity[dimKey] ?? dim.tiers[0].key}
                    onChange={(e) => updateCapacity(dimKey, e.target.value)}
                    className="mt-1"
                  >
                    {dim.tiers.map((tier) => (
                      <option key={tier.key} value={tier.key}>{tier.label}</option>
                    ))}
                  </Select>
                </div>
              );
            })}
            <div className="flex gap-3 pt-2">
              <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
              <Button onClick={() => setStep(4)}>Next: Review</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Review */}
      {step === 4 && (
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
              <InfoRow label="Country" value={REGIONS.find((r) => r.code === form.country)?.name ?? form.country} />
              <InfoRow label="City" value={form.city} />
              <InfoRow label="Contact" value={form.contact_name} />
              <InfoRow label="Email" value={form.contact_email} />
              <InfoRow label="Phone" value={form.contact_phone} />
              <InfoRow label="Billing Model" value={PAYER_MODELS.find((p) => p.value === form.billing_model)?.label ?? ""} />
              <InfoRow label="Buyer Type" value={BUYER_TYPES.find((b) => b.value === form.buyer_type)?.label ?? ""} />
              {form.tax_number && <InfoRow label="Tax Number" value={form.tax_number} />}
              <InfoRow label="Trial Days" value={`${form.trial_days} days (FREE)`} />
            </div>

            <h3 className="mt-4 mb-2 text-sm font-semibold">Selected Services</h3>
            <div className="flex flex-wrap gap-2">
              {form.services.map((key) => {
                const svc = BOS_SERVICES.find((s) => s.key === key);
                return <Badge key={key} variant="purple">{svc?.name ?? key}</Badge>;
              })}
            </div>

            <h3 className="mt-4 mb-2 text-sm font-semibold">Capacity</h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {CAPACITY_DIMENSIONS.map((dim) => {
                const dimKey = dim.key.toLowerCase() as keyof typeof form.capacity;
                const tier = dim.tiers.find((t) => t.key === form.capacity[dimKey]);
                return <InfoRow key={dim.key} label={dim.label} value={tier?.label ?? "—"} />;
              })}
            </div>

            <div className="mt-6 flex gap-3">
              <Button variant="outline" onClick={() => setStep(3)}>Back</Button>
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
