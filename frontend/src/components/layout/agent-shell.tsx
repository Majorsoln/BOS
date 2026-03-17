"use client";

import { AgentSidebar } from "./agent-sidebar";
import { AgentTopbar } from "./agent-topbar";

export function AgentShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <AgentSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <AgentTopbar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
