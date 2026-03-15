import { PlatformShell } from "@/components/layout/platform-shell";

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  return <PlatformShell>{children}</PlatformShell>;
}
