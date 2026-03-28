"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";
import {
  LayoutDashboard,
  Package,
  Tag,
  Users,
  ArrowLeft,
  MapPin,
  Scale,
  UserCheck,
  ShieldCheck,
  FileText,
  Activity,
  Shield,
  AlertTriangle,
  DollarSign,
  Briefcase,
  BarChart3,
  Eye,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const PLATFORM_NAV: NavGroup[] = [
  {
    title: "Overview",
    items: [
      { label: "Dashboard", href: "/platform/dashboard", icon: LayoutDashboard },
    ],
  },
  {
    title: "Regions & Compliance",
    items: [
      { label: "Region Registry", href: "/platform/regions", icon: MapPin },
      { label: "Compliance Packs", href: "/platform/compliance", icon: ShieldCheck },
      { label: "Compliance Audit", href: "/platform/governance/audit", icon: FileText },
    ],
  },
  {
    title: "Agent Management",
    items: [
      { label: "Region License Agents", href: "/platform/agents/rla", icon: Shield },
      { label: "Remote Agents", href: "/platform/agents/remote", icon: UserCheck },
      { label: "Activity & Oversight", href: "/platform/agents/activity", icon: Eye },
      { label: "Commissions & Payouts", href: "/platform/agents/payouts", icon: DollarSign },
      { label: "Performance", href: "/platform/agents/performance", icon: BarChart3 },
      { label: "Escalations", href: "/platform/agents/escalations", icon: AlertTriangle },
    ],
  },
  {
    title: "Oversight & Limits",
    items: [
      { label: "Services & Pricing", href: "/platform/pricing", icon: Package },
      { label: "Rate Governance", href: "/platform/rates", icon: Scale },
      { label: "Trials & Subscriptions", href: "/platform/subscriptions", icon: Briefcase },
      { label: "Promotions", href: "/platform/promotions", icon: Tag },
    ],
  },
  {
    title: "Audit & Monitoring",
    items: [
      { label: "Audit Log", href: "/platform/audit", icon: FileText },
      { label: "System Health", href: "/platform/health", icon: Activity },
    ],
  },
  {
    title: "Tenants",
    items: [
      { label: "All Tenants", href: "/platform/tenants", icon: Users },
    ],
  },
];

export function PlatformSidebar() {
  const pathname = usePathname();
  const { sidebarOpen } = useUIStore();

  if (!sidebarOpen) return null;

  return (
    <aside className="flex h-full w-60 flex-col border-r border-bos-silver/30 bg-white dark:border-bos-silver/20 dark:bg-neutral-950">
      {/* Platform Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-bos-silver/30 px-4 dark:border-bos-silver/20">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-bos-purple text-sm font-bold text-white">
          B
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-bold leading-tight tracking-tight">BOS</span>
          <span className="text-[10px] font-medium uppercase tracking-widest text-bos-gold">Platform</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {PLATFORM_NAV.map((group) => (
          <div key={group.title} className="mb-4">
            <div className="mb-1 px-2 text-xs font-semibold uppercase tracking-wider text-bos-silver-dark">
              {group.title}
            </div>
            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "mb-0.5 flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                    isActive
                      ? "border-l-2 border-bos-purple bg-bos-purple-light font-medium text-bos-purple dark:bg-bos-purple-light dark:text-bos-purple"
                      : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-900 dark:hover:text-neutral-50",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Back to Tenant Admin */}
      <div className="border-t border-bos-silver/30 p-3 dark:border-bos-silver/20">
        <Link
          href="/dashboard"
          className="flex items-center gap-2 rounded-md px-2 py-2 text-sm text-bos-silver-dark transition-colors hover:bg-neutral-50 hover:text-neutral-900 dark:hover:bg-neutral-900 dark:hover:text-neutral-50"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Tenant Admin
        </Link>
      </div>
    </aside>
  );
}
