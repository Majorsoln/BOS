"use client";

import { AgentShell } from "@/components/layout/agent-shell";

export default function AgentLayout({ children }: { children: React.ReactNode }) {
  return <AgentShell>{children}</AgentShell>;
}
