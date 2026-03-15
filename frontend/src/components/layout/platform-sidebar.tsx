"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";
import {
  LayoutDashboard,
  Cog,
  Layers,
  CreditCard,
  ClipboardList,
  Clock,
  TrendingUp,
  Tag,
  Gift,
  Handshake,
  Users,
  ArrowLeft,
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
    title: "Engine Catalog",
    items: [
      { label: "Engines", href: "/platform/engines", icon: Cog },
      { label: "Combos (Plans)", href: "/platform/combos", icon: Layers },
      { label: "Pricing", href: "/platform/pricing", icon: CreditCard },
    ],
  },
  {
    title: "Trials & Billing",
    items: [
      { label: "Trial Policy", href: "/platform/trial-policy", icon: ClipboardList },
      { label: "Active Trials", href: "/platform/trials", icon: Clock },
      { label: "Rate Governance", href: "/platform/rates", icon: TrendingUp },
    ],
  },
  {
    title: "Growth",
    items: [
      { label: "Promotions", href: "/platform/promotions", icon: Tag },
      { label: "Referrals", href: "/platform/referrals", icon: Gift },
      { label: "Resellers", href: "/platform/resellers", icon: Handshake },
    ],
  },
  {
    title: "Tenants",
    items: [
      { label: "Subscriptions", href: "/platform/subscriptions", icon: Users },
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
