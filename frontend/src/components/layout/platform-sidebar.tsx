"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";
import { usePlatformAuthStore, ROLE_LABELS } from "@/stores/platform-auth-store";
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
  BookOpen,
  PiggyBank,
  CheckCircle,
  Settings,
  UserCog,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** permission key that must be in the role's allowed set */
  permission: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
  /** if set, the group only appears when role has this permission */
  permission?: string;
}

const PLATFORM_NAV: NavGroup[] = [
  {
    title: "Overview",
    permission: "dashboard",
    items: [
      { label: "Dashboard", href: "/platform/dashboard", icon: LayoutDashboard, permission: "dashboard" },
    ],
  },
  {
    title: "Agent Management",
    permission: "agents",
    items: [
      { label: "Region License Agents", href: "/platform/agents/rla", icon: Shield, permission: "agents" },
      { label: "Remote Agents", href: "/platform/agents/remote", icon: UserCheck, permission: "agents" },
      { label: "Activity & Oversight", href: "/platform/agents/activity", icon: Eye, permission: "agents" },
      { label: "Performance", href: "/platform/agents/performance", icon: BarChart3, permission: "agents" },
      { label: "Escalations", href: "/platform/agents/escalations", icon: AlertTriangle, permission: "agents" },
    ],
  },
  {
    title: "Finance",
    permission: "finance",
    items: [
      { label: "Revenue & Collections", href: "/platform/finance", icon: PiggyBank, permission: "finance" },
      { label: "Revenue Ledger", href: "/platform/finance/ledger", icon: BookOpen, permission: "finance" },
      { label: "Payout Approvals", href: "/platform/finance/approvals", icon: CheckCircle, permission: "finance" },
      { label: "Payment Rules", href: "/platform/finance/rules", icon: Settings, permission: "finance" },
    ],
  },
  {
    title: "Oversight & Limits",
    permission: "pricing",
    items: [
      { label: "Services & Pricing", href: "/platform/pricing", icon: Package, permission: "pricing" },
      { label: "Rate Governance", href: "/platform/rates", icon: Scale, permission: "rates" },
      { label: "Trials & Subscriptions", href: "/platform/subscriptions", icon: Briefcase, permission: "subscriptions" },
      { label: "Promotions", href: "/platform/promotions", icon: Tag, permission: "promotions" },
    ],
  },
  {
    title: "Regions & Compliance",
    permission: "compliance",
    items: [
      { label: "Region Registry", href: "/platform/regions", icon: MapPin, permission: "regions" },
      { label: "Compliance Packs", href: "/platform/compliance", icon: ShieldCheck, permission: "compliance" },
      { label: "Compliance Audit", href: "/platform/governance/audit", icon: FileText, permission: "governance" },
    ],
  },
  {
    title: "Audit & Monitoring",
    permission: "audit",
    items: [
      { label: "Audit Log", href: "/platform/audit", icon: FileText, permission: "audit" },
      { label: "System Health", href: "/platform/health", icon: Activity, permission: "health" },
    ],
  },
  {
    title: "Tenants",
    permission: "tenants",
    items: [
      { label: "All Tenants", href: "/platform/tenants", icon: Users, permission: "tenants" },
    ],
  },
  {
    title: "Administration",
    permission: "admins",
    items: [
      { label: "Platform Admins", href: "/platform/admins", icon: UserCog, permission: "admins" },
    ],
  },
];

export function PlatformSidebar() {
  const pathname = usePathname();
  const { sidebarOpen } = useUIStore();
  const { role, name, can } = usePlatformAuthStore();

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
          <span className="text-[10px] font-medium uppercase tracking-widest text-bos-gold">Main Admin</span>
        </div>
      </div>

      {/* Current admin role badge */}
      <div className="border-b border-bos-silver/20 px-4 py-2">
        <p className="truncate text-xs font-medium text-neutral-700 dark:text-neutral-300">{name || "Platform Admin"}</p>
        <span className={cn(
          "inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
          role === "SUPER_ADMIN"
            ? "bg-bos-purple-light text-bos-purple"
            : role === "FINANCE_ADMIN"
            ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400"
            : role === "AGENT_MANAGER"
            ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400"
            : role === "COMPLIANCE_OFFICER"
            ? "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-400"
            : "bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400",
        )}>
          {ROLE_LABELS[role]}
        </span>
      </div>

      {/* Navigation — filtered by role permissions */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {PLATFORM_NAV.map((group) => {
          // Hide entire group if role lacks the group's permission
          if (group.permission && !can(group.permission)) return null;

          // Filter individual items
          const items = group.items.filter((item) => can(item.permission));
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
