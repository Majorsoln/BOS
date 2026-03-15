"use client";

import { useState, useMemo } from "react";
import { PageHeader } from "@/components/shared/page-header";
import {
  Card, CardContent, CardHeader, CardTitle, Select, Label, Input, Badge,
} from "@/components/ui";
import {
  REGIONS, BACKEND_ENGINES, ENGINE_REFERENCE_PRICES, REGION_AFFORDABILITY_WEIGHTS,
  COUNTRY_TAX_RULES, BUSINESS_TYPES, ADDON_ENGINES, PAYER_MODELS, BUYER_TYPES,
  AI_USAGE_TIERS,
} from "@/lib/constants";
import { Check, ChevronRight, Building2, MapPin, Calculator, Shield } from "lucide-react";

interface PlanConfig {
  billingCountry: string;
  businessCount: number;
  branchesPerBusiness: number;
  businessTypes: string[];
  addons: string[];
  aiTier: string;
  payerModel: string;
  buyerType: string;
  taxNumber: string;
}

const DEFAULT_CONFIG: PlanConfig = {
  billingCountry: "KE",
  businessCount: 1,
  branchesPerBusiness: 1,
  businessTypes: [],
  addons: [],
  aiTier: "none",
  payerModel: "HQ_PAYS",
  buyerType: "B2C",
  taxNumber: "",
};

/** Calculate local price for an engine in a given country */
function engineLocalPrice(engineKey: string, countryCode: string): number {
  const refUsd = ENGINE_REFERENCE_PRICES[engineKey] ?? 0;
  if (refUsd === 0) return 0;
  const regionWeights = REGION_AFFORDABILITY_WEIGHTS[countryCode];
  if (!regionWeights) return refUsd; // fallback to USD
  return Math.round(refUsd * regionWeights.weight * regionWeights.usdToLocal);
}

export default function PricingPage() {
  const [config, setConfig] = useState<PlanConfig>(DEFAULT_CONFIG);

  const update = (partial: Partial<PlanConfig>) =>
    setConfig((prev) => ({ ...prev, ...partial }));

  const region = REGIONS.find((r) => r.code === config.billingCountry);
  const currency = region?.currency ?? "USD";
  const taxRules = COUNTRY_TAX_RULES[config.billingCountry];

  // Collect all selected engines (from business types + addons, deduplicated)
  const selectedEngines = useMemo(() => {
    const engines = new Set<string>();
    config.businessTypes.forEach((bt) => {
      const bType = BUSINESS_TYPES.find((b) => b.key === bt);
      bType?.engines.forEach((e) => engines.add(e));
    });
    config.addons.forEach((a) => engines.add(a));
    return Array.from(engines);
  }, [config.businessTypes, config.addons]);

  // Calculate pricing
  const pricing = useMemo(() => {
    const perBranchEngineTotal = selectedEngines.reduce(
      (sum, key) => sum + engineLocalPrice(key, config.billingCountry), 0
    );
    const aiTier = AI_USAGE_TIERS.find((t) => t.key === config.aiTier);
    const aiPriceLocal = aiTier
      ? Math.round(aiTier.price_usd * (REGION_AFFORDABILITY_WEIGHTS[config.billingCountry]?.weight ?? 1) * (REGION_AFFORDABILITY_WEIGHTS[config.billingCountry]?.usdToLocal ?? 1))
      : 0;

    const perBranch = perBranchEngineTotal + aiPriceLocal;
    const totalBranches = config.businessCount * config.branchesPerBusiness;
    const subtotal = perBranch * totalBranches;

    // Tax calculation
    let vatRate = 0;
    let vatLabel = "VAT";
    if (taxRules) {
      vatRate = taxRules.vat_rate;
      vatLabel = taxRules.tax_name;
      // B2B with reverse charge = 0% VAT
      if (config.buyerType === "B2B" && taxRules.b2b_reverse_charge) {
        vatRate = 0;
      }
    }
    const taxAmount = Math.round(subtotal * vatRate);
    const total = subtotal + taxAmount;
    const isProvisional = config.buyerType === "PENDING";

    return { perBranch, totalBranches, subtotal, vatRate, vatLabel, taxAmount, total, isProvisional };
  }, [selectedEngines, config.billingCountry, config.aiTier, config.businessCount, config.branchesPerBusiness, config.buyerType, taxRules]);

  function toggleBusinessType(key: string) {
    update({
      businessTypes: config.businessTypes.includes(key)
        ? config.businessTypes.filter((t) => t !== key)
        : [...config.businessTypes, key],
    });
  }

  function toggleAddon(key: string) {
    // Don't add as addon if already included via business type
    const businessTypeEngines = new Set<string>();
    config.businessTypes.forEach((bt) => {
      const bType = BUSINESS_TYPES.find((b) => b.key === bt);
      bType?.engines.forEach((e) => businessTypeEngines.add(e));
    });
    if (businessTypeEngines.has(key)) return; // already included
    update({
      addons: config.addons.includes(key)
        ? config.addons.filter((a) => a !== key)
        : [...config.addons, key],
    });
  }

  // Filter addons to exclude those already in business type
  const businessTypeEngines = useMemo(() => {
    const s = new Set<string>();
    config.businessTypes.forEach((bt) => {
      const bType = BUSINESS_TYPES.find((b) => b.key === bt);
      bType?.engines.forEach((e) => s.add(e));
    });
    return s;
  }, [config.businessTypes]);

  const formatLocal = (amount: number) =>
    `${currency} ${amount.toLocaleString()}`;

  return (
    <div>
      <PageHeader
        title="Plan Builder"
        description="Configure your plan — choose engines, set scale, and see pricing with tax"
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Column: Configuration Steps */}
        <div className="lg:col-span-2 space-y-6">

          {/* Step 1: Billing Country */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <StepBadge step={1} />
                <CardTitle className="text-base">Billing Country</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-bos-silver-dark mb-3">
                Determines currency, tax rules, and pricing. This is where the invoice is sent.
              </p>
              <Select
                value={config.billingCountry}
                onChange={(e) => update({ billingCountry: e.target.value })}
              >
                {REGIONS.map((r) => (
                  <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>
                ))}
              </Select>
            </CardContent>
          </Card>

          {/* Step 2: Scale */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <StepBadge step={2} />
                <CardTitle className="text-base">Scale</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="biz_count">Number of Businesses</Label>
                  <Input
                    id="biz_count"
                    type="number"
                    min={1}
                    max={100}
                    value={config.businessCount}
                    onChange={(e) => update({ businessCount: Math.max(1, Number(e.target.value)) })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="branch_count">Branches per Business</Label>
                  <Input
                    id="branch_count"
                    type="number"
                    min={1}
                    max={50}
                    value={config.branchesPerBusiness}
                    onChange={(e) => update({ branchesPerBusiness: Math.max(1, Number(e.target.value)) })}
                    className="mt-1"
                  />
                </div>
              </div>
              <p className="mt-2 text-xs text-bos-silver-dark">
                Total: {pricing.totalBranches} branch{pricing.totalBranches > 1 ? "es" : ""}
              </p>
            </CardContent>
          </Card>

          {/* Step 3: Business Types */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <StepBadge step={3} />
                <CardTitle className="text-base">Business Types</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-bos-silver-dark mb-3">
                Select the types of business you run. Each includes recommended engines.
              </p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {BUSINESS_TYPES.map((bt) => {
                  const isSelected = config.businessTypes.includes(bt.key);
                  const typePrice = bt.engines.reduce(
                    (sum, e) => sum + engineLocalPrice(e, config.billingCountry), 0
                  );
                  return (
                    <button
                      key={bt.key}
                      type="button"
                      onClick={() => toggleBusinessType(bt.key)}
                      className={`rounded-lg border p-3 text-left transition-colors ${
                        isSelected
                          ? "border-bos-purple bg-bos-purple-light"
                          : "border-bos-silver/30 hover:border-bos-purple/50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{bt.label}</span>
                        {isSelected && <Check className="h-4 w-4 text-bos-purple" />}
                      </div>
                      <p className="mt-1 text-xs text-bos-silver-dark">
                        {bt.engines.length} engines — {formatLocal(typePrice)}/branch/mo
                      </p>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {bt.engines.map((e) => (
                          <Badge key={e} variant="outline" className="text-[10px]">
                            {BACKEND_ENGINES.find((be) => be.key === e)?.displayName ?? e}
                          </Badge>
                        ))}
                      </div>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Step 4: Add-ons */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <StepBadge step={4} />
                <CardTitle className="text-base">Add-on Engines</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-bos-silver-dark mb-3">
                Optional engines beyond your business type defaults.
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {ADDON_ENGINES.map((addon) => {
                  const includedInBT = businessTypeEngines.has(addon.key);
                  const isSelected = config.addons.includes(addon.key);
                  const price = engineLocalPrice(addon.key, config.billingCountry);
                  return (
                    <button
                      key={addon.key}
                      type="button"
                      onClick={() => toggleAddon(addon.key)}
                      disabled={includedInBT}
                      className={`rounded-lg border p-2.5 text-left text-sm transition-colors ${
                        includedInBT
                          ? "border-green-200 bg-green-50 cursor-default opacity-60"
                          : isSelected
                          ? "border-bos-purple bg-bos-purple-light"
                          : "border-bos-silver/30 hover:border-bos-purple/50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-xs">{addon.label}</span>
                        {(includedInBT || isSelected) && <Check className="h-3.5 w-3.5 text-bos-purple" />}
                      </div>
                      <p className="text-[10px] text-bos-silver-dark mt-0.5">
                        {includedInBT ? "Included" : `+${formatLocal(price)}/branch/mo`}
                      </p>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Step 5: AI Usage */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <StepBadge step={5} />
                <CardTitle className="text-base">AI Usage</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {AI_USAGE_TIERS.map((tier) => {
                  const isSelected = config.aiTier === tier.key;
                  const localPrice = tier.price_usd > 0
                    ? Math.round(tier.price_usd * (REGION_AFFORDABILITY_WEIGHTS[config.billingCountry]?.weight ?? 1) * (REGION_AFFORDABILITY_WEIGHTS[config.billingCountry]?.usdToLocal ?? 1))
                    : 0;
                  return (
                    <button
                      key={tier.key}
                      type="button"
                      onClick={() => update({ aiTier: tier.key })}
                      className={`rounded-lg border p-3 text-left transition-colors ${
                        isSelected
                          ? "border-bos-purple bg-bos-purple-light"
                          : "border-bos-silver/30 hover:border-bos-purple/50"
                      }`}
                    >
                      <span className="text-sm font-medium">{tier.label}</span>
                      <p className="text-xs text-bos-silver-dark mt-0.5">{tier.description}</p>
                      <p className="text-xs font-medium mt-1">
                        {localPrice > 0 ? `+${formatLocal(localPrice)}/branch/mo` : "Free"}
                      </p>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Step 6: Billing Setup */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <StepBadge step={6} />
                <CardTitle className="text-base">Billing & Tax Setup</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Payer Model */}
              <div>
                <Label>Who Pays?</Label>
                <div className="mt-1 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {PAYER_MODELS.map((pm) => {
                    const isSelected = config.payerModel === pm.value;
                    return (
                      <button
                        key={pm.value}
                        type="button"
                        onClick={() => update({ payerModel: pm.value })}
                        className={`rounded-lg border p-3 text-left transition-colors ${
                          isSelected
                            ? "border-bos-purple bg-bos-purple-light"
                            : "border-bos-silver/30 hover:border-bos-purple/50"
                        }`}
                      >
                        <span className="text-sm font-medium">{pm.label}</span>
                        <p className="text-xs text-bos-silver-dark mt-0.5">{pm.description}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Buyer Type */}
              <div>
                <Label>Buyer Type</Label>
                <div className="mt-1 grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {BUYER_TYPES.map((bt) => {
                    const isSelected = config.buyerType === bt.value;
                    return (
                      <button
                        key={bt.value}
                        type="button"
                        onClick={() => update({ buyerType: bt.value })}
                        className={`rounded-lg border p-3 text-left transition-colors ${
                          isSelected
                            ? "border-bos-purple bg-bos-purple-light"
                            : "border-bos-silver/30 hover:border-bos-purple/50"
                        }`}
                      >
                        <span className="text-sm font-medium">{bt.label}</span>
                        <p className="text-xs text-bos-silver-dark mt-0.5">{bt.description}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Tax Number (for B2B) */}
              {(config.buyerType === "B2B" || config.buyerType === "PENDING") && (
                <div>
                  <Label htmlFor="tax_number">Tax Registration Number</Label>
                  <Input
                    id="tax_number"
                    value={config.taxNumber}
                    onChange={(e) => update({ taxNumber: e.target.value })}
                    placeholder="e.g. P051234567Z"
                    className="mt-1"
                  />
                  <p className="text-[10px] text-bos-silver-dark mt-1">
                    {config.buyerType === "PENDING"
                      ? "VAT will be charged provisionally until verification is complete."
                      : "Verified B2B customers may qualify for reverse charge (0% VAT)."}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Price Summary (sticky) */}
        <div className="lg:col-span-1">
          <div className="sticky top-4 space-y-4">
            <Card className="border-bos-purple/30">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Calculator className="h-5 w-5 text-bos-purple" />
                  <CardTitle className="text-base">Price Summary</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Country & Scale */}
                <div className="flex items-center gap-2 text-sm">
                  <MapPin className="h-4 w-4 text-bos-silver-dark" />
                  <span>{region?.name} ({currency})</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Building2 className="h-4 w-4 text-bos-silver-dark" />
                  <span>{config.businessCount} business{config.businessCount > 1 ? "es" : ""} × {config.branchesPerBusiness} branch{config.branchesPerBusiness > 1 ? "es" : ""} = {pricing.totalBranches} total</span>
                </div>

                {/* Selected Engines */}
                {selectedEngines.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-bos-silver-dark mb-1.5">Selected Engines</p>
                    <div className="space-y-1">
                      {selectedEngines.map((key) => {
                        const eng = BACKEND_ENGINES.find((e) => e.key === key);
                        const price = engineLocalPrice(key, config.billingCountry);
                        return (
                          <div key={key} className="flex justify-between text-xs">
                            <span>{eng?.displayName ?? key}</span>
                            <span className="text-bos-silver-dark">{formatLocal(price)}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Free Engines */}
                <div className="border-t border-bos-silver/20 pt-2">
                  <p className="text-xs font-medium text-bos-silver-dark mb-1">Free Engines (included)</p>
                  <div className="flex flex-wrap gap-1">
                    {BACKEND_ENGINES.filter((e) => e.category === "FREE").map((e) => (
                      <Badge key={e.key} variant="outline" className="text-[10px]">{e.displayName}</Badge>
                    ))}
                  </div>
                </div>

                {/* Price Breakdown */}
                <div className="border-t border-bos-silver/20 pt-3 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Per branch/month</span>
                    <span className="font-medium">{formatLocal(pricing.perBranch)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>× {pricing.totalBranches} branches</span>
                    <span className="font-medium">{formatLocal(pricing.subtotal)}</span>
                  </div>

                  {/* Tax */}
                  <div className="flex justify-between text-sm">
                    <span>
                      {pricing.vatLabel} ({Math.round(pricing.vatRate * 100)}%)
                      {pricing.isProvisional && (
                        <Badge variant="warning" className="ml-1 text-[9px]">Provisional</Badge>
                      )}
                    </span>
                    <span className="font-medium">{formatLocal(pricing.taxAmount)}</span>
                  </div>

                  {/* Total */}
                  <div className="border-t border-bos-purple/30 pt-2 flex justify-between">
                    <span className="text-base font-bold">Total/month</span>
                    <span className="text-xl font-bold text-bos-purple">{formatLocal(pricing.total)}</span>
                  </div>
                </div>

                {/* Safe Default Notice */}
                {pricing.isProvisional && (
                  <div className="rounded-lg bg-orange-50 p-3 dark:bg-orange-950">
                    <div className="flex gap-2">
                      <Shield className="h-4 w-4 text-orange-600 mt-0.5 shrink-0" />
                      <p className="text-xs text-orange-800 dark:text-orange-200">
                        <strong>Safe Default:</strong> VAT is charged provisionally while your tax number is pending verification.
                        Once verified, a credit note will be issued for any overpaid VAT if reverse charge applies.
                      </p>
                    </div>
                  </div>
                )}

                {selectedEngines.length === 0 && (
                  <p className="text-center text-xs text-bos-silver-dark py-4">
                    Select a business type to see pricing
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Billing Country Tax Info */}
            {taxRules && (
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs font-medium mb-2">Tax Rules — {region?.name}</p>
                  <div className="space-y-1 text-xs text-bos-silver-dark">
                    <div className="flex justify-between">
                      <span>{taxRules.tax_name} Rate</span>
                      <span>{Math.round(taxRules.vat_rate * 100)}%</span>
                    </div>
                    {taxRules.digital_tax_rate > 0 && (
                      <div className="flex justify-between">
                        <span>Digital Services Tax</span>
                        <span>{(taxRules.digital_tax_rate * 100).toFixed(1)}%</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span>B2B Reverse Charge</span>
                      <span>{taxRules.b2b_reverse_charge ? "Yes" : "No"}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StepBadge({ step }: { step: number }) {
  return (
    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-bos-purple text-xs font-bold text-white">
      {step}
    </div>
  );
}
