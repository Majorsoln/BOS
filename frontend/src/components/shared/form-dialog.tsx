"use client";

import { Button } from "@/components/ui";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface FormDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  onSubmit: (e: React.FormEvent) => void;
  submitLabel?: string;
  loading?: boolean;
  wide?: boolean;
}

export function FormDialog({
  open,
  onClose,
  title,
  description,
  children,
  onSubmit,
  submitLabel = "Save",
  loading = false,
  wide = false,
}: FormDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto py-10">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />

      {/* Dialog */}
      <div className={cn(
        "relative w-full rounded-lg bg-white p-6 shadow-xl dark:bg-neutral-950",
        wide ? "max-w-2xl" : "max-w-lg",
      )}>
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-bos-silver-dark hover:text-neutral-900 dark:hover:text-neutral-50"
        >
          <X className="h-4 w-4" />
        </button>

        <h2 className="text-lg font-semibold">{title}</h2>
        {description && (
          <p className="mt-1 text-sm text-bos-silver-dark">{description}</p>
        )}

        <form onSubmit={onSubmit} className="mt-4">
          <div className="space-y-4">
            {children}
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Saving..." : submitLabel}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
