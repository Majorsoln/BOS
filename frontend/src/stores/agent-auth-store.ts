/**
 * Agent Auth Store
 * ================
 * Tracks the logged-in agent's identity and type.
 *
 * Agent types:
 *   REGION_LICENSE_AGENT (RLA) — franchisee, manages a region
 *   REMOTE_AGENT             — sub-agent under an RLA
 *
 * isRLA drives sidebar visibility, feature access, and UI labels.
 * This replaces the `const isRLA = true` hardcode in agent-sidebar.tsx.
 */

import { create } from "zustand";

export type AgentType = "REGION_LICENSE_AGENT" | "REMOTE_AGENT";

export type ContractStatus =
  | "DRAFT"
  | "ACTIVE"
  | "SUSPENDED"
  | "TERMINATED_REVERSIBLE"
  | "TERMINATED_PERMANENT"
  | "REDUCED_COMMISSION"
  | "EXPIRED"
  | null;

interface AgentAuthState {
  agentId: string;
  agentName: string;
  agentType: AgentType;
  regionCode: string;
  licenseNumber: string;
  contractStatus: ContractStatus;
  isLoaded: boolean;

  /** True when agentType is REGION_LICENSE_AGENT */
  isRLA: boolean;

  setAgent: (data: {
    agentId: string;
    agentName: string;
    agentType: AgentType;
    regionCode?: string;
    licenseNumber?: string;
    contractStatus?: ContractStatus;
  }) => void;

  hydrate: () => void;
  clear: () => void;
}

const STORAGE_KEY = "bos_agent_auth";

const DEFAULT_TYPE: AgentType = "REGION_LICENSE_AGENT";

function isAgentType(v: unknown): v is AgentType {
  return v === "REGION_LICENSE_AGENT" || v === "REMOTE_AGENT";
}

export const useAgentAuthStore = create<AgentAuthState>((set) => ({
  agentId: "",
  agentName: "",
  agentType: DEFAULT_TYPE,
  regionCode: "",
  licenseNumber: "",
  contractStatus: null,
  isLoaded: false,
  isRLA: true, // default true until hydrated — prevents flicker for RLAs

  setAgent: ({ agentId, agentName, agentType, regionCode = "", licenseNumber = "", contractStatus = null }) => {
    const payload = { agentId, agentName, agentType, regionCode, licenseNumber, contractStatus };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch {
      // localStorage may be unavailable in SSR
    }
    set({
      ...payload,
      isRLA: agentType === "REGION_LICENSE_AGENT",
      isLoaded: true,
    });
  },

  hydrate: () => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        set({ isLoaded: true });
        return;
      }
      const parsed = JSON.parse(raw);
      const agentType: AgentType = isAgentType(parsed.agentType) ? parsed.agentType : DEFAULT_TYPE;
      set({
        agentId: parsed.agentId ?? "",
        agentName: parsed.agentName ?? "",
        agentType,
        regionCode: parsed.regionCode ?? "",
        licenseNumber: parsed.licenseNumber ?? "",
        contractStatus: parsed.contractStatus ?? null,
        isRLA: agentType === "REGION_LICENSE_AGENT",
        isLoaded: true,
      });
    } catch {
      set({ isLoaded: true });
    }
  },

  clear: () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
    set({
      agentId: "",
      agentName: "",
      agentType: DEFAULT_TYPE,
      regionCode: "",
      licenseNumber: "",
      contractStatus: null,
      isRLA: true,
      isLoaded: false,
    });
  },
}));
