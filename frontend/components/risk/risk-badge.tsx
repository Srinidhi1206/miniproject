import { AlertOctagon, AlertTriangle, ShieldAlert, ShieldCheck } from "lucide-react";

import { RISK } from "@/lib/risk";
import { cn } from "@/lib/utils";
import type { RiskLevel } from "@/types/api";

const ICON = { LOW: ShieldCheck, MEDIUM: AlertTriangle, HIGH: ShieldAlert, CRITICAL: AlertOctagon };

export function RiskBadge({ level, score, className, size = "sm" }: {
  level: RiskLevel;
  score?: number;
  className?: string;
  size?: "sm" | "md";
}) {
  const r = RISK[level];
  const Icon = ICON[level];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-xs border font-semibold uppercase tracking-wide",
        r.bg, r.text, r.line,
        size === "sm" ? "px-1.5 py-0.5 text-[0.68rem]" : "px-2 py-1 text-xs",
        className,
      )}
    >
      <Icon aria-hidden className={size === "sm" ? "size-3" : "size-3.5"} />
      {r.short}
      {score !== undefined && <span className="font-mono tabular-nums opacity-80">· {score}</span>}
    </span>
  );
}

/** Horizontal meter showing the four bands with a marker at the score. */
export function ScoreMeter({ score, className }: { score: number; className?: string }) {
  const bands = [
    { to: 30, cls: "bg-safe" },
    { to: 60, cls: "bg-warn" },
    { to: 80, cls: "bg-high" },
    { to: 100, cls: "bg-critical" },
  ];
  let from = 0;
  return (
    <div className={cn("w-full", className)}>
      <div
        className="relative h-2.5 w-full"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score}
        aria-label="Risk score"
      >
        <div className="flex h-full w-full gap-0.5 overflow-hidden rounded-xs">
          {bands.map((b) => {
            const w = b.to - from;
            const el = <div key={b.to} className={cn(b.cls, "h-full opacity-80")} style={{ width: `${w}%` }} />;
            from = b.to;
            return el;
          })}
        </div>
        <div
          className="absolute -top-1.5 h-5.5 w-1 -translate-x-1/2 rounded-full bg-ink ring-2 ring-surface animate-fade"
          style={{ left: `${Math.min(99.5, Math.max(0.5, score))}%` }}
        />
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[0.65rem] uppercase tracking-wider text-faint">
        <span>0 Low</span>
        <span className="hidden sm:inline">30 Medium</span>
        <span className="hidden sm:inline">60 High</span>
        <span>80 Critical · 100</span>
      </div>
    </div>
  );
}
