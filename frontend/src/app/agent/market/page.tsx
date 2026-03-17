"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Card, CardContent, CardHeader, CardTitle, Badge } from "@/components/ui";
import { getMarketIntelligence } from "@/lib/api/agents";
import { BarChart3, TrendingUp, Users, MapPin, Building2, Zap } from "lucide-react";

export default function AgentMarketPage() {
  const market = useQuery({ queryKey: ["agent", "market"], queryFn: getMarketIntelligence });
  const d = market.data?.data ?? {};

  const topCombos = d.top_combos ?? [];
  const topRegions = d.top_regions ?? [];
  const topIndustries = d.top_industries ?? [];

  return (
    <div>
      <PageHeader
        title="Market Intelligence"
        description="Anonymized regional data to help you target the right prospects"
      />

      {/* Key Metrics */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Platform Tenants"
          value={d.total_tenants ?? "—"}
          icon={Users}
          description="Across all agents"
        />
        <StatCard
          title="Your Market Share"
          value={d.market_share ? `${d.market_share}%` : "—"}
          icon={BarChart3}
          description="Your tenants vs total"
        />
        <StatCard
          title="Avg Revenue/Tenant"
          value={d.avg_revenue_per_tenant ?? "—"}
          icon={TrendingUp}
          description="Platform average"
        />
        <StatCard
          title="Growth Rate"
          value={d.growth_rate ? `${d.growth_rate}%` : "—"}
          icon={Zap}
          description="New tenants this month"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Top Engine Combos */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Popular Engine Combos</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {topCombos.length === 0 && (
              <p className="py-4 text-center text-sm text-bos-silver-dark">No data available</p>
            )}
            <div className="space-y-3">
              {topCombos.map((c: { name: string; tenant_count: number; share_pct: number }, i: number) => (
                <div key={i} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{c.name}</p>
                    <p className="text-xs text-bos-silver-dark">{c.tenant_count} tenants</p>
                  </div>
                  <Badge variant="outline">{c.share_pct}%</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Regions */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Top Regions</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {topRegions.length === 0 && (
              <p className="py-4 text-center text-sm text-bos-silver-dark">No data available</p>
            )}
            <div className="space-y-3">
              {topRegions.map((r: { region: string; tenant_count: number; growth_pct: number }, i: number) => (
                <div key={i} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{r.region}</p>
                    <p className="text-xs text-bos-silver-dark">{r.tenant_count} tenants</p>
                  </div>
                  <span className={`text-xs font-medium ${r.growth_pct >= 0 ? "text-green-600" : "text-red-500"}`}>
                    {r.growth_pct >= 0 ? "+" : ""}{r.growth_pct}%
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Industries */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Top Industries</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {topIndustries.length === 0 && (
              <p className="py-4 text-center text-sm text-bos-silver-dark">No data available</p>
            )}
            <div className="space-y-3">
              {topIndustries.map((ind: { industry: string; tenant_count: number; avg_revenue: string }, i: number) => (
                <div key={i} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{ind.industry}</p>
                    <p className="text-xs text-bos-silver-dark">{ind.tenant_count} tenants</p>
                  </div>
                  <span className="text-xs font-mono text-bos-silver-dark">{ind.avg_revenue}/mo</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Insights */}
      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">Market Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg bg-bos-silver-light p-4 text-sm text-bos-silver-dark dark:bg-neutral-900">
            <ul className="list-inside list-disc space-y-2">
              <li>All data is anonymized — no individual tenant details are shared.</li>
              <li>Focus on industries with high tenant count and average revenue for best commission returns.</li>
              <li>Growing regions present opportunities for early market capture.</li>
              <li>Popular engine combos indicate proven demand — prioritize these during onboarding.</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
