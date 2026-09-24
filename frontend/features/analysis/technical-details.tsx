"use client";

import * as Collapsible from "@radix-ui/react-collapsible";
import { ChevronDown, Cpu } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";
import type { AnalysisResult } from "@/types/api";

export function TechnicalDetails({ result }: { result: AnalysisResult }) {
  const [open, setOpen] = useState(false);
  const b = result.breakdown;
  return (
    <Collapsible.Root open={open} onOpenChange={setOpen} className="overflow-hidden rounded-md border border-line bg-surface">
      <Collapsible.Trigger className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left hover:bg-surface-2">
        <span className="flex items-center gap-2.5">
          <Cpu className="size-4 text-muted" aria-hidden />
          <span className="font-medium text-ink">View technical details</span>
          <span className="hidden text-sm text-muted sm:inline">— score breakdown, model outputs, agent trace</span>
        </span>
        <ChevronDown className={cn("size-4 text-muted transition-transform", open && "rotate-180")} aria-hidden />
      </Collapsible.Trigger>
      <Collapsible.Content className="border-t border-line data-[state=open]:animate-fade">
        <div className="space-y-8 p-5">
          {/* Score breakdown */}
          <section>
            <h3 className="eyebrow mb-3">Risk engine breakdown</h3>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[34rem] text-left text-sm">
                <thead className="font-mono text-[0.68rem] uppercase tracking-wider text-faint">
                  <tr className="border-b border-line">
                    <th className="py-2 pr-3 font-normal">Component</th>
                    <th className="py-2 pr-3 font-normal">Subject</th>
                    <th className="py-2 pr-3 text-right font-normal">Model pts</th>
                    <th className="py-2 pr-3 text-right font-normal">Rule pts</th>
                    <th className="py-2 text-right font-normal">Score</th>
                  </tr>
                </thead>
                <tbody className="font-mono text-xs">
                  {b.components.map((c, i) => (
                    <tr key={i} className="border-b border-line align-top">
                      <td className="py-2 pr-3 uppercase text-ink">{c.component}</td>
                      <td className="max-w-[16rem] break-all py-2 pr-3 text-ink-2">
                        {c.subject}
                        {c.overrides.map((o) => <span key={o} className="mt-1 block text-warn">override: {o}</span>)}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{c.model_points.toFixed(1)}</td>
                      <td className="py-2 pr-3 text-right tabular-nums">{c.rule_points > 0 ? `+${c.rule_points}` : c.rule_points}</td>
                      <td className="py-2 text-right font-semibold tabular-nums text-ink">{c.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 font-mono text-xs text-ink-2">
              final = max({b.base_score}) + corroboration({b.corroboration_bonus}) = <span className="font-semibold text-ink">{b.final_score}</span>
            </p>
            <p className="mt-1 font-mono text-[0.68rem] leading-relaxed text-faint">{b.formula}</p>
          </section>

          {/* Model outputs */}
          <section>
            <h3 className="eyebrow mb-3">Model outputs</h3>
            <div className="grid gap-3 md:grid-cols-2">
              {b.components.filter((c) => c.model).map((c, i) => (
                <div key={i} className="rounded-sm border border-line p-3">
                  <p className="font-mono text-xs text-ink">{c.model!.name} <span className="text-faint">v{c.model!.version}</span></p>
                  <p className="mt-2 text-sm text-ink-2">
                    P({c.model!.target === "text" ? "scam" : "phishing"}) ={" "}
                    <span className="font-mono font-semibold text-ink">{c.model!.probability.toFixed(3)}</span>
                    <span className="text-muted"> → {c.model!.label}</span>
                  </p>
                  {c.model!.target === "text" && c.model!.top_features.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-muted">Terms that pushed toward “scam”:</p>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {c.model!.top_features.map((f) => (
                          <code key={f.feature} className="rounded-xs bg-high-bg px-1.5 py-0.5 font-mono text-[0.68rem] text-high">
                            {f.feature} <span className="opacity-70">+{f.weight.toFixed(2)}</span>
                          </code>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {b.components.every((c) => !c.model) && <p className="text-sm text-muted">This result used deterministic analyzers only.</p>}
            </div>
          </section>

          {/* Agent trace */}
          <section>
            <h3 className="eyebrow mb-3">Agent trace</h3>
            <ol className="relative space-y-0 border-l border-line pl-5">
              {result.trace.map((s, i) => (
                <li key={i} className="relative pb-3 last:pb-0">
                  <span className={cn(
                    "absolute -left-[1.4rem] top-1.5 size-2.5 rounded-full border-2 border-surface",
                    s.status === "done" ? "bg-ink" : s.status === "failed" ? "bg-critical" : "bg-line-strong",
                  )} aria-hidden />
                  <p className="font-mono text-xs">
                    <span className="text-faint">{s.stage.padEnd(8)}</span>{" "}
                    <span className="font-medium text-ink">{s.tool}</span>{" "}
                    <span className="text-muted">{s.status !== "done" && `(${s.status}) `}{s.note}</span>{" "}
                    <span className="text-faint">{s.duration_ms}ms</span>
                  </p>
                </li>
              ))}
            </ol>
            <p className="mt-3 text-xs text-muted">Explanation: {result.explanation.generated_by} · analysis id <span className="font-mono">{result.id}</span></p>
          </section>
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  );
}
