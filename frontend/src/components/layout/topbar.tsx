"use client";

import { useAuthStore } from "@/stores/auth-store";
import { useUIStore } from "@/stores/ui-store";
import { Button } from "@/components/ui";

export function Topbar() {
  const { businessName, logout } = useAuthStore();
  const { toggleSidebar } = useUIStore();

  return (
    <header className="flex h-14 items-center justify-between border-b border-neutral-200 bg-white px-4 dark:border-neutral-800 dark:bg-neutral-950">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={toggleSidebar} aria-label="Toggle sidebar">
          <span className="text-lg">{"\u2630"}</span>
        </Button>
        <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
          {businessName || "BOS"}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={logout}>
          Sign Out
        </Button>
      </div>
    </header>
  );
}
