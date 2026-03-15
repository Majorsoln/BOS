"use client";

import { cn } from "@/lib/utils";
import { Card } from "@/components/ui";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  description?: string;
  trend?: { value: string; positive: boolean };
  className?: string;
}

export function StatCard({ title, value, icon: Icon, description, trend, className }: StatCardProps) {
  return (
    <Card className={cn("p-5", className)}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-bos-silver-dark">{title}</p>
          <p className="mt-1 text-2xl font-bold tracking-tight">{value}</p>
          {description && (
            <p className="mt-1 text-xs text-bos-silver-dark">{description}</p>
          )}
          {trend && (
            <p className={cn("mt-1 text-xs font-medium", trend.positive ? "text-green-600" : "text-red-600")}>
              {trend.value}
            </p>
          )}
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-bos-purple-light">
          <Icon className="h-5 w-5 text-bos-purple" />
        </div>
      </div>
    </Card>
  );
}
