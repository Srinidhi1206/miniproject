"use client";

import { Check, Minus, X } from "lucide-react";

import type { RunState } from "@/hooks/use-analysis-run";
import { STAGES } from "@/lib/risk";
import { cn } from "@/lib/utils";

/** Live view of the agent's real work: stage checklist + tool log from the stream. */
export function ProgressConsole({ state, subject }: { state: RunState; subject: string }) {
  const doneCount = STAGES.filter((s) => state.stages[s.id] === "done" || state.stages[s.id] === "skipped").length;
  return (
    <div className="animate-fade overflow-hidden rounded-md bg-console text-console-text" role="status" aria-live="polite">
      <div className="flex items-center justify-between border-b border-console-line px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2.5">
          <span className="size-2 rounded-full bg-signal animate-pulse-dot" aria-hidden />
          <span className="font-mono text-xs uppercase tracking-[0.14em]">
            {state.phase === "done" ? "Analysis complete" : "Analysing"}
          </span>
        </div>
        <span className="font-mono text-xs text-console-muted">{doneCount}/{STAGES.length}</span>
      </div>

      <div className="grid gap-6 p-4 sm:p-5 md:grid-cols-[minmax(0,15rem)_1fr]">
        <ol className="space-y-3">
          {STAGES.map((s) => {
            const st = state.stages[s.id];
            return (
              <li key={s.id} className="flex items-center gap-3 text-sm">
                <span
                  className={cn(
                    "grid size-5 shrink-0 place-items-center rounded-full border",
                    st === "done" && "border-signal bg-signal text-console",
                    st === "active" && "border-signal",
                    st === "pending" && "border-console-line",
                    st === "skipped" && "border-console-line text-console-muted",
                  )}
                  aria-hidden
                >
                  {st === "done" && <Check className="size-3" strokeWidth={3} />}
                  {st === "active" && <span className="size-1.5 rounded-full bg-signal animate-pulse-dot" />}
                  {st === "skipped" && <Minus className="size-3" />}
                </span>
                <span className={cn(st === "pending" || st === "skipped" ? "text-console-muted" : "text-console-text")}>
                  {s.label}
                  {st === "skipped" && <span className="ml-1.5 text-xs text-console-muted">· not needed</span>}
                  <span className="sr-only"> — {st}</span>
                </span>
              </li>
            );
          })}
        </ol>

        <div className="min-w-0 rounded-sm border border-console-line bg-console-2 p-3 font-mono text-[0.75rem] leading-relaxed">
          <p className="truncate text-console-muted">&gt; input: {subject}</p>
          {state.steps.map((step, i) => (
            <p key={i} className="animate-fade break-words">
              <span className={cn(step.status === "failed" ? "text-[#ff8a8a]" : step.status === "skipped" ? "text-console-muted" : "text-signal")}>
                {step.status === "failed" ? <X className="inline size-3" /> : "✓"}
              </span>{" "}
              <span className="text-console-text">{step.tool}</span>
              {step.note && <span className="text-console-muted"> · {step.note}</span>}
              <span className="text-console-muted"> · {step.duration_ms}ms</span>
            </p>
          ))}
          {state.phase === "running" && <p className="text-console-muted animate-pulse-dot">▍</p>}
        </div>
      </div>
    </div>
  );
}
