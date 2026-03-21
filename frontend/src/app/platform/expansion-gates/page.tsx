"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import {
  Card, CardContent, CardHeader, CardTitle, Badge,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui";
import { getRegions } from "@/lib/api/saas";
import { REGIONS, COUNTRY_TAX_RULES, EXPANSION_GATES } from "@/lib/constants";
import { CheckCircle2, XCircle, AlertCircle, Globe, ShieldCheck, ShieldAlert } from "lucide-react";

interface RegionData {
  code: string;
  name: string;
  currency: string;
  tax_name?: string;
  vat_rate?: number;
  digital_tax_rate?: number;
  b2b_reverse_charge?: boolean;
  registration_required?: boolean;
  is_active?: boolean;
}

function evaluateGates(region: RegionData) {
  const hasTax = region.vat_rate != null && region.vat_rate > 0;
  const hasCurrency = !!region.currency;

  return {
    country_logic: {
      pass: hasCurrency && hasTax,
      detail: hasCurrency && hasTax
        ? `${region.currency} configured, ${region.tax_name ?? "VAT"} ${Math.round((region.vat_rate ?? 0) * 100)}%`
        : "Currency or tax not configured",
    },
    b2b_b2c_qualification: {
      pass: hasTax,
      detail: hasTax
        ? `${region.tax_name ?? "VAT"} ${Math.round((region.vat_rate ?? 0) * 100)}%, Reverse charge: ${region.b2b_reverse_charge ? "Yes" : "No"}`
        : "Tax rules not configured",
    },
    registration_path: {
      pass: hasTax && region.registration_required != null,
      detail: hasTax
        ? "Tax registration pathway documented"
        : "Registration pathway not documented",
    },
    reporting_correction: {
      pass: hasTax,
      detail: hasTax
        ? "Credit note and adjustment invoice workflows available"
        : "Correction workflows not configured",
    },
  };
}

export default function ExpansionGatesPage() {
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);

  // Try loading dynamic regions, fall back to hardcoded
  const regionsQuery = useQuery({ queryKey: ["saas", "regions"], queryFn: getRegions });
  const serverRegions: RegionData[] = regionsQuery.data?.data?.regions ?? [];

  const allRegions: RegionData[] = serverRegions.length > 0
    ? serverRegions
    : REGIONS.map((r) => {
        const tax = COUNTRY_TAX_RULES[r.code];
        return {
          code: r.code,
          name: r.name,
          currency: r.currency,
          tax_name: tax?.tax_name,
          vat_rate: tax?.vat_rate,
          digital_tax_rate: tax?.digital_tax_rate,
          b2b_reverse_charge: tax?.b2b_reverse_charge,
          registration_required: tax?.registration_required,
          is_active: true,
        };
      });

  const liveCount = allRegions.filter((r) => {
    const gates = evaluateGates(r);
    return Object.values(gates).every((g) => g.pass);
  }).length;

  const partialCount = allRegions.filter((r) => {
    const gates = evaluateGates(r);
    const passes = Object.values(gates).filter((g) => g.pass).length;
    return passes > 0 && passes < 4;
  }).length;

  return (
    <div>
      <PageHeader
        title="Region Expansion Gates"
        description="4-gate readiness check before a country goes live for billing"
      />

      {/* Summary */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-green-100 dark:bg-green-900/30">
              <ShieldCheck className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600">{liveCount}</p>
              <p className="text-xs text-bos-silver-dark">Live Markets</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-100 dark:bg-orange-900/30">
              <ShieldAlert className="h-5 w-5 text-orange-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-orange-600">{partialCount}</p>
              <p className="text-xs text-bos-silver-dark">Partial Readiness</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bos-purple/10">
              <Globe className="h-5 w-5 text-bos-purple" />
            </div>
            <div>
              <p className="text-2xl font-bold">{allRegions.length}</p>
              <p className="text-xs text-bos-silver-dark">Total Countries</p>
            </div>
          </CardContent>
        </Card>
      </div>

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
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Country Readiness</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-bos-silver-light/50 dark:bg-neutral-900 hover:bg-bos-silver-light/50">
                <TableHead className="h-10">Country</TableHead>
                <TableHead className="h-10 w-20">Currency</TableHead>
                {EXPANSION_GATES.map((gate) => (
                  <TableHead key={gate.key} className="text-center h-10 text-xs">
                    {gate.label.replace(" Locked", "").replace(" Exists", "").replace(" Path", "")}
                  </TableHead>
                ))}
                <TableHead className="text-center h-10 w-24">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {allRegions.map((region) => {
                const gates = evaluateGates(region);
                const allPass = Object.values(gates).every((g) => g.pass);
                const somePass = Object.values(gates).some((g) => g.pass);
                const isSelected = selectedCountry === region.code;
                return (
                  <TableRow
                    key={region.code}
                    className={`cursor-pointer ${isSelected ? "bg-bos-purple-light/50 hover:bg-bos-purple-light/50" : ""}`}
                    onClick={() => setSelectedCountry(isSelected ? null : region.code)}
                  >
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center justify-center rounded-md bg-bos-purple/10 px-1.5 py-0.5 text-[10px] font-bold text-bos-purple">
                          {region.code}
                        </span>
                        {region.name}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{region.currency}</Badge>
                    </TableCell>
                    {Object.entries(gates).map(([key, gate]) => (
                      <TableCell key={key} className="text-center">
                        {gate.pass ? (
                          <CheckCircle2 className="inline h-5 w-5 text-green-500" />
                        ) : (
                          <XCircle className="inline h-5 w-5 text-red-400" />
                        )}
                      </TableCell>
                    ))}
                    <TableCell className="text-center">
                      <Badge variant={allPass ? "success" : somePass ? "warning" : "outline"}>
                        {allPass ? "LIVE" : somePass ? "PARTIAL" : "BLOCKED"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Selected Country Detail */}
      {selectedCountry && (() => {
        const region = allRegions.find((r) => r.code === selectedCountry);
        if (!region) return null;
        const gates = evaluateGates(region);
        return (
          <Card className="mt-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                {region.name} — Gate Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {EXPANSION_GATES.map((gate) => {
                  const status = gates[gate.key as keyof typeof gates];
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
        );
      })()}
    </div>
  );
}
