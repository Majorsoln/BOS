"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";

interface NavItem {
  label: string;
  href: string;
  icon: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: "Overview",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: "grid" },
    ],
  },
  {
    title: "Documents",
    items: [
      { label: "All Documents", href: "/documents", icon: "file-text" },
    ],
  },
  {
    title: "People",
    items: [
      { label: "Customers", href: "/customers", icon: "users" },
    ],
  },
  {
    title: "Settings",
    items: [
      { label: "Business", href: "/settings/business", icon: "building" },
      { label: "Branches", href: "/settings/branches", icon: "map-pin" },
      { label: "Users & Roles", href: "/settings/users", icon: "shield" },
      { label: "API Keys", href: "/settings/api-keys", icon: "key" },
      { label: "Tax Rules", href: "/settings/tax-rules", icon: "percent" },
      { label: "Feature Flags", href: "/settings/feature-flags", icon: "toggle-left" },
    ],
  },
  {
    title: "Data",
    items: [
      { label: "Migration", href: "/migration", icon: "upload" },
    ],
  },
];

// Simple icon component using text characters (no external dep needed)
function NavIcon({ name }: { name: string }) {
  const icons: Record<string, string> = {
    "grid": "\u25A6",
    "file-text": "\u2630",
    "users": "\u263A",
    "building": "\u2302",
    "map-pin": "\u2316",
    "shield": "\u26E8",
    "key": "\u26BF",
    "percent": "%",
    "toggle-left": "\u2261",
    "upload": "\u21E7",
  };
  return <span className="w-5 text-center text-base leading-none">{icons[name] || "\u2022"}</span>;
}

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen } = useUIStore();

  if (!sidebarOpen) return null;

  return (
    <aside className="flex h-full w-60 flex-col border-r border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-950">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-neutral-200 px-4 dark:border-neutral-800">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-neutral-900 text-sm font-bold text-white dark:bg-neutral-100 dark:text-neutral-900">
          B
        </div>
        <span className="text-lg font-bold tracking-tight">BOS</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="mb-4">
            <div className="mb-1 px-2 text-xs font-semibold uppercase tracking-wider text-neutral-400">
              {group.title}
            </div>
            {group.items.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "mb-0.5 flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                    isActive
                      ? "bg-neutral-100 font-medium text-neutral-900 dark:bg-neutral-800 dark:text-neutral-50"
                      : "text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-900 dark:hover:text-neutral-50",
                  )}
                >
                  <NavIcon name={item.icon} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
