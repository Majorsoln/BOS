import { create } from "zustand";

interface AuthState {
  apiKey: string;
  businessId: string;
  branchId: string;
  actorId: string;
  businessName: string;
  isAuthenticated: boolean;

  login: (apiKey: string, businessId: string, branchId: string, actorId: string, businessName: string) => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  apiKey: "",
  businessId: "",
  branchId: "",
  actorId: "",
  businessName: "",
  isAuthenticated: false,

  login: (apiKey, businessId, branchId, actorId, businessName) => {
    localStorage.setItem("bos_api_key", apiKey);
    localStorage.setItem("bos_business_id", businessId);
    localStorage.setItem("bos_branch_id", branchId);
    localStorage.setItem("bos_actor_id", actorId);
    localStorage.setItem("bos_business_name", businessName);
    set({ apiKey, businessId, branchId, actorId, businessName, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("bos_api_key");
    localStorage.removeItem("bos_business_id");
    localStorage.removeItem("bos_branch_id");
    localStorage.removeItem("bos_actor_id");
    localStorage.removeItem("bos_business_name");
    set({ apiKey: "", businessId: "", branchId: "", actorId: "", businessName: "", isAuthenticated: false });
  },

  hydrate: () => {
    if (typeof window === "undefined") return;
    const apiKey = localStorage.getItem("bos_api_key") || "";
    const businessId = localStorage.getItem("bos_business_id") || "";
    const branchId = localStorage.getItem("bos_branch_id") || "";
    const actorId = localStorage.getItem("bos_actor_id") || "";
    const businessName = localStorage.getItem("bos_business_name") || "";
    set({
      apiKey,
      businessId,
      branchId,
      actorId,
      businessName,
      isAuthenticated: !!apiKey && !!businessId,
    });
  },
}));
