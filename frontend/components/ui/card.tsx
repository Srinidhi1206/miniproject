import * as React from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-md border border-line bg-surface", className)} {...props} />;
}

export function SectionHeading({
  eyebrow, title, description, action, className, as: Tag = "h2",
}: {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  as?: "h1" | "h2" | "h3";
}) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4", className)}>
      <div className="max-w-2xl">
        {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
        <Tag className={cn("font-semibold tracking-[-0.02em] text-ink", Tag === "h1" ? "text-3xl sm:text-4xl" : "text-xl sm:text-2xl")}>
          {title}
        </Tag>
        {description && <p className="mt-2 text-[0.95rem] leading-relaxed text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function Pill({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-2 px-2.5 py-0.5 text-xs font-medium text-ink-2", className)}
      {...props}
    />
  );
}

export function DemoTag({ className }: { className?: string }) {
  return (
    <span
      className={cn("inline-flex items-center rounded-xs border border-dashed border-warn-line bg-warn-bg px-1.5 py-px font-mono text-[0.65rem] font-semibold uppercase tracking-wider text-warn", className)}
      title="Fictional demonstration data — not real reports"
    >
      Demo data
    </span>
  );
}
