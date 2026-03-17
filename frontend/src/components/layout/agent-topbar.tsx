"use client";

import { useUIStore } from "@/stores/ui-store";
import { Menu, LogOut } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { UserCheck } from "lucide-react";

export function AgentTopbar() {
  const { toggleSidebar } = useUIStore();
  const { logout } = useAuthStore();

  return (
    <header className="flex h-14 items-center justify-between border-b border-bos-silver/30 bg-white px-4 dark:border-bos-silver/20 dark:bg-neutral-950">
      {/* Purple accent line */}
      <div className="absolute left-0 top-0 h-0.5 w-full bg-bos-purple" />

      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="rounded-md p-1.5 text-bos-silver-dark hover:bg-neutral-100 dark:hover:bg-neutral-800"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2">
          <UserCheck className="h-4 w-4 text-bos-purple" />
          <span className="text-sm font-semibold text-bos-purple">Agent Portal</span>
        </div>
      </div>

      <button
        onClick={logout}
        className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-bos-silver-dark hover:bg-neutral-100 dark:hover:bg-neutral-800"
      >
        <LogOut className="h-4 w-4" />
        Logout
      </button>
    </header>
  );
}
