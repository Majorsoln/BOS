"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";
import {
  LayoutGrid,
  FileText,
  Users,
  Building2,
  MapPin,
  Shield,
  KeyRound,
  Percent,
  ToggleLeft,
  Upload,
  Crown,
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

const NAV_GROUPS: NavGroup[] = [
  {
    title: "Overview",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutGrid },
    ],
  },
  {
    title: "Documents",
    items: [
      { label: "All Documents", href: "/documents", icon: FileText },
    ],
  },
  {
    title: "People",
    items: [
      { label: "Customers", href: "/customers", icon: Users },
    ],
  },
  {
    title: "Settings",
    items: [
      { label: "Business", href: "/settings/business", icon: Building2 },
      { label: "Branches", href: "/settings/branches", icon: MapPin },
      { label: "Users & Roles", href: "/settings/users", icon: Shield },
      { label: "API Keys", href: "/settings/api-keys", icon: KeyRound },
      { label: "Tax Rules", href: "/settings/tax-rules", icon: Percent },
      { label: "Feature Flags", href: "/settings/feature-flags", icon: ToggleLeft },
    ],
  },
  {
    title: "Data",
    items: [
      { label: "Migration", href: "/migration", icon: Upload },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen } = useUIStore();

  if (!sidebarOpen) return null;

  return (
    <aside className="flex h-full w-60 flex-col border-r border-bos-silver/30 bg-white dark:border-bos-silver/20 dark:bg-neutral-950">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-bos-silver/30 px-4 dark:border-bos-silver/20">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-bos-purple text-sm font-bold text-white">
          B
        </div>
        <span className="text-lg font-bold tracking-tight">BOS</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="mb-4">
            <div className="mb-1 px-2 text-xs font-semibold uppercase tracking-wider text-bos-silver-dark">
              {group.title}
            </div>
            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
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

      {/* Platform Admin Link */}
      <div className="border-t border-bos-silver/30 p-3 dark:border-bos-silver/20">
        <Link
          href="/platform/dashboard"
          className={cn(
            "flex items-center gap-2 rounded-md px-2 py-2 text-sm font-medium transition-colors",
            pathname.startsWith("/platform")
              ? "bg-bos-gold-light text-bos-gold-dark"
              : "text-bos-silver-dark hover:bg-bos-gold-light hover:text-bos-gold-dark",
          )}
        >
          <Crown className="h-4 w-4" />
          Main Admin
        </Link>
      </div>
    </aside>
  );
}
