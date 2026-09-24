import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export function EmptyState({ icon: Icon, title, body, action, className }: {
  icon: LucideIcon;
  title: string;
  body: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center rounded-md border border-dashed border-line-strong px-6 py-12 text-center", className)}>
      <span className="grid size-11 place-items-center rounded-full border border-line bg-surface">
        <Icon className="size-5 text-ink-2" aria-hidden />
      </span>
      <p className="mt-4 font-medium text-ink">{title}</p>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-muted">{body}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-critical-line bg-critical-bg px-4 py-3 text-sm">
      <span className="text-critical">{message}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="font-medium text-ink underline underline-offset-4">
          Try again
        </button>
      )}
    </div>
  );
}
