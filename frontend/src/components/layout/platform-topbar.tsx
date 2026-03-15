"use client";

import { useAuthStore } from "@/stores/auth-store";
import { useUIStore } from "@/stores/ui-store";
import { Button } from "@/components/ui";
import { Menu, LogOut, Crown } from "lucide-react";

export function PlatformTopbar() {
  const { logout } = useAuthStore();
  const { toggleSidebar } = useUIStore();

  return (
    <header className="flex h-14 items-center justify-between border-b border-bos-silver/30 bg-white px-4 dark:border-bos-silver/20 dark:bg-neutral-950">
      {/* Gold accent line at bottom */}
      <div className="absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-r from-bos-gold/60 via-bos-gold/20 to-transparent" />

      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={toggleSidebar} aria-label="Toggle sidebar">
          <Menu className="h-5 w-5" />
        </Button>
        <div className="flex items-center gap-2">
          <Crown className="h-4 w-4 text-bos-gold" />
          <span className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">
            Platform Administration
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={logout} className="gap-2 text-bos-silver-dark hover:text-neutral-900">
          <LogOut className="h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </header>
  );
}
