import { create } from "zustand";

export type PlatformAdminRole =
  | "SUPER_ADMIN"
  | "FINANCE_ADMIN"
  | "AGENT_MANAGER"
  | "COMPLIANCE_OFFICER"
  | "VIEWER";

// What each role can see/access (mirrors backend PLATFORM_ROLE_PERMISSIONS)
export const ROLE_PERMISSIONS: Record<PlatformAdminRole, ReadonlySet<string>> = {
  SUPER_ADMIN: new Set([
    "dashboard", "agents", "finance", "pricing", "rates",
    "subscriptions", "trials", "promotions", "regions", "compliance",
    "audit", "health", "tenants", "admins", "governance",
  ]),
  FINANCE_ADMIN: new Set([
    "dashboard", "finance", "rates", "subscriptions", "trials",
    "audit", "health",
  ]),
  AGENT_MANAGER: new Set([
    "dashboard", "agents", "tenants", "promotions", "subscriptions",
    "trials", "audit",
  ]),
  COMPLIANCE_OFFICER: new Set([
    "dashboard", "compliance", "regions", "governance", "audit", "health",
  ]),
  VIEWER: new Set(["dashboard", "audit"]),
};

export const ROLE_LABELS: Record<PlatformAdminRole, string> = {
  SUPER_ADMIN: "Super Admin",
  FINANCE_ADMIN: "Finance Admin",
  AGENT_MANAGER: "Agent Manager",
  COMPLIANCE_OFFICER: "Compliance Officer",
  VIEWER: "Viewer",
};

interface PlatformAuthState {
  adminId: string;
  name: string;
  email: string;
  role: PlatformAdminRole;
  isLoaded: boolean;

  setAdmin: (data: {
    adminId: string;
    name: string;
    email: string;
    role: PlatformAdminRole;
  }) => void;
  can: (permission: string) => boolean;
  hydrate: () => void;
}

const DEFAULT_ROLE: PlatformAdminRole = "SUPER_ADMIN";

export const usePlatformAuthStore = create<PlatformAuthState>((set, get) => ({
  adminId: "",
  name: "",
  email: "",
  role: DEFAULT_ROLE,
  isLoaded: false,

  setAdmin: ({ adminId, name, email, role }) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("bos_platform_admin_id", adminId);
      localStorage.setItem("bos_platform_admin_name", name);
      localStorage.setItem("bos_platform_admin_email", email);
      localStorage.setItem("bos_platform_admin_role", role);
    }
    set({ adminId, name, email, role, isLoaded: true });
  },

  can: (permission: string) => {
    const { role } = get();
    return ROLE_PERMISSIONS[role]?.has(permission) ?? false;
  },

  hydrate: () => {
    if (typeof window === "undefined") return;
    const adminId = localStorage.getItem("bos_platform_admin_id") || "";
    const name = localStorage.getItem("bos_platform_admin_name") || "Platform Admin";
    const email = localStorage.getItem("bos_platform_admin_email") || "";
    const raw = localStorage.getItem("bos_platform_admin_role") || DEFAULT_ROLE;
    const role = (Object.keys(ROLE_PERMISSIONS).includes(raw)
      ? raw
      : DEFAULT_ROLE) as PlatformAdminRole;
    set({ adminId, name, email, role, isLoaded: true });
  },
}));
