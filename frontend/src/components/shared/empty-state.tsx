"use client";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-neutral-300 py-16 dark:border-neutral-700">
      <p className="text-lg font-medium text-neutral-600 dark:text-neutral-400">{title}</p>
      {description && (
        <p className="mt-1 text-sm text-neutral-400 dark:text-neutral-500">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
