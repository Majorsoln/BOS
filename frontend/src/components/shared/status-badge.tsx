"use client";

import { Badge } from "@/components/ui";

type StatusType =
  | "ACTIVE"
  | "TRIAL"
  | "SUSPENDED"
  | "CANCELLED"
  | "DEACTIVATED"
  | "PENDING"
  | "CONVERTED"
  | "EXPIRED"
  | "EXHAUSTED"
  | "QUALIFIED"
  | "REWARDED"
  | "REJECTED"
  | "COMPLETED"
  | "FAILED"
  | "TERMINATED"
  | "FREE"
  | "PAID"
  | "B2B"
  | "B2C"
  | "BOTH"
  | "BRONZE"
  | "SILVER"
  | "GOLD"
  | "STANDARD"
  | "ELEVATED"
  | "DRAFT"
  | "PILOT"
  | "SUNSET";

const STATUS_CONFIG: Record<StatusType, { variant: "success" | "purple" | "warning" | "destructive" | "secondary" | "gold" | "outline" | "default"; label?: string }> = {
  ACTIVE: { variant: "success" },
  TRIAL: { variant: "purple" },
  SUSPENDED: { variant: "warning" },
  CANCELLED: { variant: "destructive" },
  DEACTIVATED: { variant: "secondary" },
  PENDING: { variant: "outline" },
  CONVERTED: { variant: "success" },
  EXPIRED: { variant: "secondary" },
  EXHAUSTED: { variant: "gold" },
  QUALIFIED: { variant: "success" },
  REWARDED: { variant: "gold" },
  REJECTED: { variant: "destructive" },
  COMPLETED: { variant: "success" },
  FAILED: { variant: "destructive" },
  TERMINATED: { variant: "destructive" },
  FREE: { variant: "gold" },
  PAID: { variant: "purple" },
  B2B: { variant: "outline" },
  B2C: { variant: "purple" },
  BOTH: { variant: "gold" },
  BRONZE: { variant: "outline" },
  SILVER: { variant: "secondary" },
  GOLD: { variant: "gold" },
  STANDARD: { variant: "outline" },
  ELEVATED: { variant: "warning" },
  DRAFT: { variant: "secondary" },
  PILOT: { variant: "purple" },
  SUNSET: { variant: "destructive" },
};

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const config = STATUS_CONFIG[status as StatusType] || { variant: "secondary" as const };
  return (
    <Badge variant={config.variant}>
      {label || config.label || status}
    </Badge>
  );
}
