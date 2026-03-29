"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";
import {
  LayoutDashboard,
  UserPlus,
  Users,
  DollarSign,
  Tag,
  LifeBuoy,
  FileCheck,
  GraduationCap,
  FileText,
  BarChart3,
  ArrowLeft,
  Shield,
  UserCheck,
  BookOpen,
  PiggyBank,
  Send,
  Briefcase,
  Clock,
  Settings,
  Building2,
  Eye,
  Scale,
  UsersRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  rlaOnly?: boolean;
}

interface NavGroup {
  title: string;
  items: NavItem[];
  rlaOnly?: boolean;
}

const AGENT_NAV: NavGroup[] = [
  {
    title: "Overview",
    items: [
      { label: "Dashboard", href: "/agent/dashboard", icon: LayoutDashboard },
    ],
  },
  {
    title: "Tenants — Wapangaji",
    items: [
      { label: "Onboard Tenant", href: "/agent/onboard", icon: UserPlus },
      { label: "My Tenants", href: "/agent/tenants", icon: Users },
      { label: "Trials & Subs", href: "/agent/trials", icon: Clock, rlaOnly: true },
    ],
  },
  {
    title: "Remote Agents — Mawakala",
    rlaOnly: true,
    items: [
      { label: "My Agents", href: "/agent/remote-agents", icon: UserCheck },
      { label: "Agent Performance", href: "/agent/remote-agents/performance", icon: BarChart3 },
    ],
  },
  {
    title: "Revenue — Mapato",
    items: [
      { label: "Revenue Overview", href: "/agent/revenue", icon: PiggyBank, rlaOnly: true },
      { label: "Revenue Ledger", href: "/agent/revenue/ledger", icon: BookOpen, rlaOnly: true },
      { label: "Remittance", href: "/agent/revenue/remittance", icon: Send, rlaOnly: true },
      { label: "Commission History", href: "/agent/commissions", icon: DollarSign },
    ],
  },
  {
    title: "Promotions — Matangazo",
    items: [
      { label: "My Promotions", href: "/agent/promotions", icon: Tag },
    ],
  },
  {
    title: "Operations — Shughuli",
    items: [
      { label: "Support Tickets", href: "/agent/support", icon: LifeBuoy },
      { label: "Compliance", href: "/agent/compliance", icon: FileCheck, rlaOnly: true },
      { label: "Training", href: "/agent/training", icon: GraduationCap },
    ],
  },
  {
    title: "Staff — Wafanyakazi",
    rlaOnly: true,
    items: [
      { label: "My Staff", href: "/agent/staff", icon: UsersRound },
    ],
  },
  {
    title: "Account — Akaunti",
    items: [
      { label: "My Agreement", href: "/agent/agreement", icon: FileText },
      { label: "Profile & License", href: "/agent/profile", icon: Building2, rlaOnly: true },
      { label: "Market Intelligence", href: "/agent/market", icon: BarChart3 },
    ],
  },
];

export function AgentSidebar() {
  const pathname = usePathname();
  const { sidebarOpen } = useUIStore();

  // TODO: Get from auth context. For now, default to RLA to show all sections.
  const isRLA = true;

  if (!sidebarOpen) return null;

  return (
    <aside className="flex h-full w-60 flex-col border-r border-bos-silver/30 bg-white dark:border-bos-silver/20 dark:bg-neutral-950">
      {/* Agent Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-bos-silver/30 px-4 dark:border-bos-silver/20">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-bos-purple text-sm font-bold text-white">
          B
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-bold leading-tight tracking-tight">BOS</span>
          <span className="text-[10px] font-medium uppercase tracking-widest text-bos-gold">
            {isRLA ? "RLA Portal" : "Agent Portal"}
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {AGENT_NAV.map((group) => {
          // Skip RLA-only groups for remote agents
          if (group.rlaOnly && !isRLA) return null;

          // Filter RLA-only items for remote agents
          const items = isRLA ? group.items : group.items.filter((i) => !i.rlaOnly);
          if (items.length === 0) return null;

          return (
            <div key={group.title} className="mb-4">
              <div className="mb-1 px-2 text-xs font-semibold uppercase tracking-wider text-bos-silver-dark">
                {group.title}
              </div>
              {items.map((item) => {
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
          );
        })}
      </nav>

      {/* Back Link */}
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
