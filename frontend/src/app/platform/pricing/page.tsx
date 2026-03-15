"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, Select, Badge } from "@/components/ui";
import { getPricing } from "@/lib/api/saas";
import { REGIONS } from "@/lib/constants";
import { formatCurrency } from "@/lib/utils";
import { Check } from "lucide-react";

const FREE_ENGINES = ["cash", "documents", "reporting", "customer"];

export default function PricingPage() {
  const [regionCode, setRegionCode] = useState("KE");
  const [businessModel, setBusinessModel] = useState("");

  const region = REGIONS.find((r) => r.code === regionCode);

  const pricing = useQuery({
    queryKey: ["saas", "pricing", regionCode, businessModel],
    queryFn: () => getPricing({ region_code: regionCode, business_model: businessModel || undefined }),
  });

  const plans = pricing.data?.data ?? [];

  return (
    <div>
      <PageHeader
        title="Pricing Catalog"
        description="Bei za combos kwa kila region — mtazamo wa customer"
      />

      {/* Filters */}
      <div className="mb-6 flex items-center gap-4">
        <div className="w-48">
          <Select value={regionCode} onChange={(e) => setRegionCode(e.target.value)}>
            {REGIONS.map((r) => (
              <option key={r.code} value={r.code}>{r.name} ({r.currency})</option>
            ))}
          </Select>
        </div>
        <div className="w-48">
          <Select value={businessModel} onChange={(e) => setBusinessModel(e.target.value)}>
            <option value="">All Models</option>
            <option value="B2C">B2C</option>
            <option value="B2B">B2B</option>
          </Select>
        </div>
      </div>

      {pricing.isLoading ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse p-6">
              <div className="h-6 w-32 rounded bg-neutral-200" />
              <div className="mt-4 h-10 w-24 rounded bg-neutral-200" />
            </Card>
          ))}
        </div>
      ) : plans.length === 0 ? (
        <Card className="p-8 text-center text-bos-silver-dark">
          No pricing set for {region?.name ?? regionCode} yet. Set rates on the Combos page.
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {plans.map((plan: {
            combo_id: string; name: string; description?: string; business_model: string;
            paid_engines: string[]; monthly_amount: number; currency: string;
            quota?: { max_branches?: number; max_users?: number };
          }) => (
            <Card key={plan.combo_id} className="flex flex-col overflow-hidden transition-shadow hover:shadow-lg">
              <CardContent className="flex flex-1 flex-col p-6">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <h3 className="text-lg font-bold">{plan.name}</h3>
                  <StatusBadge status={plan.business_model} />
                </div>
                {plan.description && (
                  <p className="mt-1 text-sm text-bos-silver-dark">{plan.description}</p>
                )}

                {/* Price */}
                <div className="my-5 text-center">
                  <span className="text-3xl font-bold text-bos-gold-dark">
                    {formatCurrency(plan.monthly_amount * 100, plan.currency)}
                  </span>
                  <span className="text-sm text-bos-silver-dark"> /month</span>
                </div>

                {/* Paid Engines */}
                <div className="flex-1 space-y-2">
                  {plan.paid_engines?.map((eng) => (
                    <div key={eng} className="flex items-center gap-2 text-sm">
                      <Check className="h-4 w-4 text-bos-purple" />
                      <span>{eng}</span>
                    </div>
                  ))}

                  {/* Free Engines */}
                  <div className="my-3 border-t border-bos-silver/20 pt-3">
                    <p className="mb-2 text-xs font-medium text-bos-silver-dark">Plus Free Engines</p>
                    {FREE_ENGINES.map((eng) => (
                      <div key={eng} className="flex items-center gap-2 text-sm text-bos-silver-dark">
                        <Check className="h-3 w-3" />
                        <span>{eng}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Quotas */}
                {plan.quota && (
                  <div className="mt-3 border-t border-bos-silver/20 pt-3">
                    <div className="flex gap-2 text-xs text-bos-silver-dark">
                      {plan.quota.max_branches && (
                        <Badge variant="outline">{plan.quota.max_branches} branches</Badge>
                      )}
                      {plan.quota.max_users && (
                        <Badge variant="outline">{plan.quota.max_users} users</Badge>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
