"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { usePlatformAuthStore } from "@/stores/platform-auth-store";
import { getPlatformMe } from "@/lib/api/platform";
import { PlatformSidebar } from "./platform-sidebar";
import { PlatformTopbar } from "./platform-topbar";

export function PlatformShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, hydrate } = useAuthStore();
  const { hydrate: hydratePlatform, setAdmin, isLoaded: platformLoaded } = usePlatformAuthStore();
  const router = useRouter();

  useEffect(() => {
    hydrate();
    hydratePlatform();
  }, [hydrate, hydratePlatform]);

  // Fetch platform admin identity once authenticated
  useEffect(() => {
    if (!isAuthenticated || platformLoaded) return;
    getPlatformMe().then((res) => {
      if (res?.data) {
        setAdmin({
          adminId: res.data.admin_id,
          name: res.data.name,
          email: res.data.email,
          role: res.data.role,
        });
      }
    }).catch(() => {
      // Fallback: keep defaults from hydrate()
    });
  }, [isAuthenticated, platformLoaded, setAdmin]);

  useEffect(() => {
    if (!isAuthenticated && typeof window !== "undefined") {
      const key = localStorage.getItem("bos_api_key");
      if (!key) {
        router.push("/login");
      }
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-bos-silver-dark">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <PlatformSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <PlatformTopbar />
        <main className="flex-1 overflow-y-auto bg-bos-silver-light p-6 dark:bg-neutral-900">
          {children}
        </main>
      </div>
    </div>
  );
}
