import * as React from "react";
import { cn } from "@/lib/utils";

/* ── Button ─────────────────────────────────────────────── */

type ButtonVariant = "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
type ButtonSize = "default" | "sm" | "lg" | "icon";

const buttonVariants: Record<ButtonVariant, string> = {
  default: "bg-bos-purple text-white hover:bg-bos-purple-hover dark:bg-bos-purple dark:text-white dark:hover:bg-bos-purple-hover",
  destructive: "bg-red-600 text-white hover:bg-red-700",
  outline: "border border-bos-silver bg-white hover:bg-bos-silver-light dark:border-bos-silver dark:bg-neutral-950 dark:hover:bg-neutral-900",
  secondary: "bg-bos-silver-light text-neutral-900 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-50 dark:hover:bg-neutral-700",
  ghost: "hover:bg-neutral-100 dark:hover:bg-neutral-800",
  link: "text-bos-purple underline-offset-4 hover:underline dark:text-bos-purple",
};

const buttonSizes: Record<ButtonSize, string> = {
  default: "h-10 px-4 py-2",
  sm: "h-8 px-3 text-sm",
  lg: "h-12 px-6 text-lg",
  icon: "h-10 w-10",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bos-purple/50 disabled:pointer-events-none disabled:opacity-50",
        buttonVariants[variant],
        buttonSizes[size],
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";

/* ── Input ──────────────────────────────────────────────── */

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border border-bos-silver/60 bg-white px-3 py-2 text-sm placeholder:text-neutral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bos-purple/40 focus-visible:border-bos-purple disabled:cursor-not-allowed disabled:opacity-50 dark:border-bos-silver dark:bg-neutral-950 dark:placeholder:text-neutral-500",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

/* ── Textarea ──────────────────────────────────────────── */

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[80px] w-full rounded-md border border-bos-silver/60 bg-white px-3 py-2 text-sm placeholder:text-neutral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bos-purple/40 focus-visible:border-bos-purple disabled:cursor-not-allowed disabled:opacity-50 dark:border-bos-silver dark:bg-neutral-950 dark:placeholder:text-neutral-500",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";

/* ── Select ──────────────────────────────────────────────── */

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border border-bos-silver/60 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bos-purple/40 focus-visible:border-bos-purple disabled:cursor-not-allowed disabled:opacity-50 dark:border-bos-silver dark:bg-neutral-950",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  ),
);
Select.displayName = "Select";

/* ── Label ──────────────────────────────────────────────── */

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {}

export const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
  ({ className, ...props }, ref) => (
    <label
      ref={ref}
      className={cn("text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70", className)}
      {...props}
    />
  ),
);
Label.displayName = "Label";

/* ── Card ───────────────────────────────────────────────── */

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("rounded-lg border border-bos-silver/30 bg-white shadow-sm dark:border-bos-silver/20 dark:bg-neutral-950", className)} {...props} />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-lg font-semibold leading-none tracking-tight", className)} {...props} />;
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-bos-silver-dark dark:text-neutral-400", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-6 pt-0", className)} {...props} />;
}

/* ── Badge ──────────────────────────────────────────────── */

type BadgeVariant = "default" | "secondary" | "destructive" | "outline" | "success" | "purple" | "gold" | "warning";

const badgeVariants: Record<BadgeVariant, string> = {
  default: "bg-neutral-900 text-white dark:bg-neutral-50 dark:text-neutral-900",
  secondary: "bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-neutral-50",
  destructive: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-100",
  outline: "border border-bos-silver/60 text-neutral-700 dark:border-bos-silver dark:text-neutral-300",
  success: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-100",
  purple: "bg-bos-purple-light text-bos-purple dark:bg-bos-purple-light dark:text-bos-purple",
  gold: "bg-bos-gold-light text-bos-gold-dark dark:bg-bos-gold-light dark:text-bos-gold",
  warning: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-100",
};

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { variant?: BadgeVariant }) {
  return (
    <div
      className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors", badgeVariants[variant], className)}
      {...props}
    />
  );
}

/* ── Separator ──────────────────────────────────────────── */

export function Separator({ className, orientation = "horizontal", ...props }: React.HTMLAttributes<HTMLDivElement> & { orientation?: "horizontal" | "vertical" }) {
  return (
    <div
      role="separator"
      className={cn(
        "shrink-0 bg-bos-silver/30 dark:bg-neutral-800",
        orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
        className,
      )}
      {...props}
    />
  );
}

/* ── Skeleton ───────────────────────────────────────────── */

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-md bg-neutral-200 dark:bg-neutral-800", className)} {...props} />;
}

/* ── Table ──────────────────────────────────────────────── */

export function Table({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="relative w-full overflow-auto">
      <table className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  );
}

export function TableHeader({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn("[&_tr]:border-b", className)} {...props} />;
}

export function TableBody({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn("[&_tr:last-child]:border-0", className)} {...props} />;
}

export function TableRow({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("border-b border-bos-silver/30 transition-colors hover:bg-bos-purple-light/30 dark:border-bos-silver/20 dark:hover:bg-bos-purple-light/30", className)} {...props} />;
}

export function TableHead({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={cn("h-12 px-4 text-left align-middle font-medium text-bos-silver-dark dark:text-neutral-400", className)} {...props} />;
}

export function TableCell({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("p-4 align-middle", className)} {...props} />;
}

/* ── Dialog ────────────────────────────────────────────── */

export function Dialog({
  open,
  onOpenChange,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={() => onOpenChange(false)} />
      <div className="relative z-50">{children}</div>
    </div>
  );
}

export function DialogContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "w-full max-w-lg rounded-lg border border-bos-silver/30 bg-white p-6 shadow-lg dark:border-bos-silver/20 dark:bg-neutral-950",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function DialogHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mb-4 flex flex-col space-y-1.5", className)} {...props} />;
}

export function DialogTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("text-lg font-semibold leading-none tracking-tight", className)} {...props} />;
}

export function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mt-4 flex justify-end gap-2", className)} {...props} />;
}

/* ── Toast (simple) ─────────────────────────────────────── */

export function Toast({
  message,
  variant = "default",
  onClose,
}: {
  message: string;
  variant?: "default" | "success" | "error";
  onClose: () => void;
}) {
  const bg = variant === "error" ? "bg-red-600" : variant === "success" ? "bg-green-600" : "bg-bos-purple";
  return (
    <div className={cn("fixed bottom-4 right-4 z-50 rounded-lg px-4 py-3 text-sm text-white shadow-lg", bg)}>
      <div className="flex items-center gap-3">
        <span>{message}</span>
        <button onClick={onClose} className="ml-2 font-bold hover:opacity-70">&times;</button>
      </div>
    </div>
  );
}
