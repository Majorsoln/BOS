"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, Badge } from "@/components/ui";
import { GraduationCap, BookOpen, Video, FileText, ExternalLink } from "lucide-react";

const TRAINING_MODULES = [
  {
    title: "BOS Platform Overview",
    description: "Introduction to BOS SaaS platform, engine architecture, and tenant lifecycle.",
    type: "VIDEO",
    duration: "15 min",
    required: true,
  },
  {
    title: "Tenant Onboarding Process",
    description: "Step-by-step guide to onboarding a new tenant — from business info to plan selection.",
    type: "GUIDE",
    duration: "10 min",
    required: true,
  },
  {
    title: "Pricing & Plan Builder",
    description: "Understanding engine combos, document volume tiers, AI tiers, and branch multipliers.",
    type: "GUIDE",
    duration: "12 min",
    required: true,
  },
  {
    title: "Commission Structure",
    description: "How commissions work: volume-based tiers, regional overrides, residual share, first-year bonus.",
    type: "GUIDE",
    duration: "8 min",
    required: true,
  },
  {
    title: "L1 Support Handbook",
    description: "Common tenant issues and how to resolve them before escalating to L2.",
    type: "DOCUMENT",
    duration: "20 min",
    required: true,
  },
  {
    title: "Regional Compliance Guide",
    description: "Understanding tax rules, data residency, and regulatory requirements per country.",
    type: "DOCUMENT",
    duration: "15 min",
    required: false,
  },
  {
    title: "Retail Engine (Duka) Deep Dive",
    description: "POS operations, inventory, receipts, invoices, and refund workflows.",
    type: "VIDEO",
    duration: "25 min",
    required: false,
  },
  {
    title: "Restaurant Engine Deep Dive",
    description: "Table management, kitchen tickets, bill splitting, and F&B workflows.",
    type: "VIDEO",
    duration: "20 min",
    required: false,
  },
  {
    title: "Workshop Engine Deep Dive",
    description: "Quoting, job management, cutting lists, invoicing, and fabrication workflows.",
    type: "VIDEO",
    duration: "20 min",
    required: false,
  },
  {
    title: "Hotel Engine Deep Dive",
    description: "Reservations, check-in/out, folio management, and housekeeping workflows.",
    type: "VIDEO",
    duration: "25 min",
    required: false,
  },
] as const;

function TypeIcon({ type }: { type: string }) {
  switch (type) {
    case "VIDEO": return <Video className="h-4 w-4 text-bos-purple" />;
    case "GUIDE": return <BookOpen className="h-4 w-4 text-bos-gold" />;
    case "DOCUMENT": return <FileText className="h-4 w-4 text-bos-silver-dark" />;
    default: return <FileText className="h-4 w-4" />;
  }
}

export default function AgentTrainingPage() {
  const requiredModules = TRAINING_MODULES.filter((m) => m.required);
  const optionalModules = TRAINING_MODULES.filter((m) => !m.required);

  return (
    <div>
      <PageHeader
        title="Training & Product Knowledge"
        description="Complete required training modules and explore product deep dives"
      />

      <div className="mb-6 rounded-lg border border-bos-purple/20 bg-bos-purple/5 p-4">
        <div className="flex items-center gap-2">
          <GraduationCap className="h-5 w-5 text-bos-purple" />
          <h3 className="text-sm font-semibold text-bos-purple">Training Progress</h3>
        </div>
        <p className="mt-1 text-xs text-bos-silver-dark">
          Complete all required modules during your probation period. Optional engine deep dives
          help you better serve tenants in specific industries.
        </p>
      </div>

      {/* Required Modules */}
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-bos-silver-dark">Required Modules</h2>
      <div className="mb-8 grid grid-cols-1 gap-3 md:grid-cols-2">
        {requiredModules.map((m, i) => (
          <Card key={i} className="hover:border-bos-purple/30 transition-colors cursor-pointer">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-bos-purple/10">
                  <TypeIcon type={m.type} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold">{m.title}</h3>
                    <Badge variant="destructive" className="text-[10px]">Required</Badge>
                  </div>
                  <p className="mt-1 text-xs text-bos-silver-dark">{m.description}</p>
                  <div className="mt-2 flex items-center gap-3 text-xs text-bos-silver-dark">
                    <span className="flex items-center gap-1">
                      <TypeIcon type={m.type} />
                      {m.type}
                    </span>
                    <span>{m.duration}</span>
                  </div>
                </div>
                <ExternalLink className="h-4 w-4 text-bos-silver-dark" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Optional Engine Deep Dives */}
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-bos-silver-dark">Engine Deep Dives (Optional)</h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {optionalModules.map((m, i) => (
          <Card key={i} className="hover:border-bos-purple/30 transition-colors cursor-pointer">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-bos-silver-light dark:bg-neutral-800">
                  <TypeIcon type={m.type} />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold">{m.title}</h3>
                  <p className="mt-1 text-xs text-bos-silver-dark">{m.description}</p>
                  <div className="mt-2 flex items-center gap-3 text-xs text-bos-silver-dark">
                    <span className="flex items-center gap-1">
                      <TypeIcon type={m.type} />
                      {m.type}
                    </span>
                    <span>{m.duration}</span>
                  </div>
                </div>
                <ExternalLink className="h-4 w-4 text-bos-silver-dark" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
