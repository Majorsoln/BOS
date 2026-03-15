"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, Badge } from "@/components/ui";
import { REGIONS, COUNTRY_TAX_RULES, REGION_AFFORDABILITY_WEIGHTS, EXPANSION_GATES } from "@/lib/constants";
import { CheckCircle2, XCircle, AlertCircle, Globe, Shield } from "lucide-react";

/**
 * Evaluate gate status for a country.
 * In production this would come from backend configuration.
 * For now, we derive it from the constants we have.
 */
function evaluateGates(countryCode: string) {
  const hasWeight = !!REGION_AFFORDABILITY_WEIGHTS[countryCode];
  const hasTaxRules = !!COUNTRY_TAX_RULES[countryCode];
  const taxRules = COUNTRY_TAX_RULES[countryCode];

  return {
    country_logic: {
      pass: hasWeight,
      detail: hasWeight
        ? `Weight: ${REGION_AFFORDABILITY_WEIGHTS[countryCode].weight}, USD rate: ${REGION_AFFORDABILITY_WEIGHTS[countryCode].usdToLocal}`
        : "Affordability weight not configured",
    },
    b2b_b2c_qualification: {
      pass: hasTaxRules,
      detail: hasTaxRules
        ? `${taxRules!.tax_name} ${Math.round(taxRules!.vat_rate * 100)}%, Reverse charge: ${taxRules!.b2b_reverse_charge ? "Yes" : "No"}`
        : "Tax rules not configured",
    },
    registration_path: {
      // For configured countries we assume registration path exists
      pass: hasTaxRules && hasWeight,
      detail: hasTaxRules
        ? "Digital services tax registration pathway documented"
        : "Registration pathway not documented",
    },
    reporting_correction: {
      // Assume configured countries have correction paths
      pass: hasTaxRules && hasWeight,
      detail: hasTaxRules
        ? "Credit note and adjustment invoice workflows available"
        : "Correction workflows not configured",
    },
  };
}

export default function ExpansionGatesPage() {
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);

  return (
    <div>
      <PageHeader
        title="Region Expansion Gates"
        description="4-gate readiness check before a country goes live for billing"
      />

      {/* Gate Descriptions */}
      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {EXPANSION_GATES.map((gate, idx) => (
          <Card key={gate.key}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-bos-purple text-xs font-bold text-white">
                  {idx + 1}
                </div>
                <h3 className="text-sm font-semibold">{gate.label}</h3>
              </div>
              <p className="text-xs text-bos-silver-dark leading-relaxed">{gate.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Country Grid */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Country Readiness</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Country</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Currency</th>
                  {EXPANSION_GATES.map((gate) => (
                    <th key={gate.key} className="px-4 py-3 text-center text-xs font-semibold uppercase text-bos-silver-dark">
                      {gate.label.replace(" Locked", "").replace(" Exists", "").replace(" Path", "")}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase text-bos-silver-dark">Status</th>
                </tr>
              </thead>
              <tbody>
                {REGIONS.map((region) => {
                  const gates = evaluateGates(region.code);
                  const allPass = Object.values(gates).every((g) => g.pass);
                  const somePass = Object.values(gates).some((g) => g.pass);
                  return (
                    <tr
                      key={region.code}
                      className={`border-b border-bos-silver/10 cursor-pointer transition-colors ${
                        selectedCountry === region.code ? "bg-bos-purple-light/50" : "hover:bg-bos-silver-light/50 dark:hover:bg-neutral-900/50"
                      }`}
                      onClick={() => setSelectedCountry(selectedCountry === region.code ? null : region.code)}
                    >
                      <td className="px-4 py-3 font-medium">{region.name}</td>
                      <td className="px-4 py-3"><Badge variant="outline">{region.currency}</Badge></td>
                      {Object.entries(gates).map(([key, gate]) => (
                        <td key={key} className="px-4 py-3 text-center">
                          {gate.pass ? (
                            <CheckCircle2 className="inline h-5 w-5 text-green-500" />
                          ) : (
                            <XCircle className="inline h-5 w-5 text-red-400" />
                          )}
                        </td>
                      ))}
                      <td className="px-4 py-3 text-center">
                        <Badge variant={allPass ? "success" : somePass ? "warning" : "outline"}>
                          {allPass ? "LIVE" : somePass ? "PARTIAL" : "BLOCKED"}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Selected Country Detail */}
      {selectedCountry && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle className="text-base">
              {REGIONS.find((r) => r.code === selectedCountry)?.name} — Gate Details
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {EXPANSION_GATES.map((gate) => {
                const status = evaluateGates(selectedCountry)[gate.key as keyof ReturnType<typeof evaluateGates>];
                return (
                  <div
                    key={gate.key}
                    className={`rounded-lg border p-4 ${
                      status.pass
                        ? "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950"
                        : "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {status.pass ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-500" />
                      )}
                      <span className="text-sm font-medium">{gate.label}</span>
                    </div>
                    <p className="text-xs text-bos-silver-dark ml-6">{status.detail}</p>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
