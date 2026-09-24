"use client";

import { useCallback, useRef, useState } from "react";

import { analyzeStream, ApiError, type AnalyzeInput } from "@/lib/api";
import { rememberResult } from "@/lib/result-cache";
import type { AgentStep, AnalysisResult, Stage, StreamEvent } from "@/types/api";

export type StageStatus = "pending" | "active" | "done" | "skipped";

export interface RunState {
  phase: "idle" | "running" | "done" | "error";
  stages: Record<Stage, StageStatus>;
  steps: AgentStep[];
  result: AnalysisResult | null;
  error: { message: string; hint?: string; code: string } | null;
}

const ORDER: Stage[] = ["validate", "extract", "analyze", "risk", "explain"];
const initialStages = (): Record<Stage, StageStatus> =>
  ({ validate: "pending", extract: "pending", analyze: "pending", risk: "pending", explain: "pending" });

// Events arrive in real time (a text scan takes ~20 ms). Each one is revealed
// with a short minimum spacing so people can actually read what happened.
// This only paces the display of real events — nothing is invented.
const REVEAL_MS = 260;

export function useAnalysisRun() {
  const [state, setState] = useState<RunState>({
    phase: "idle", stages: initialStages(), steps: [], result: null, error: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const apply = useCallback((e: StreamEvent) => {
    setState((s) => {
      if (e.type === "stage") {
        const stages = { ...s.stages };
        const idx = ORDER.indexOf(e.stage);
        // Stages can legitimately run out of order (a message is classified, THEN its links
        // are extracted), so earlier pending stages stay pending; only unused stages are
        // marked "not needed" once the whole run has finished.
        ORDER.forEach((st, i) => {
          if (i !== idx && stages[st] === "active") stages[st] = "done";
        });
        stages[e.stage] = "active";
        return { ...s, stages };
      }
      if (e.type === "step") return { ...s, steps: [...s.steps, e.step] };
      return s;
    });
  }, []);

  const run = useCallback(async (input: AnalyzeInput): Promise<AnalysisResult | null> => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ phase: "running", stages: { ...initialStages(), validate: "active" }, steps: [], result: null, error: null });

    const queue: StreamEvent[] = [];
    let streamDone = false;
    let failure: unknown = null;
    let result: AnalysisResult | null = null;

    const stream = analyzeStream(input, (e) => queue.push(e), controller.signal)
      .then((r) => { result = r; })
      .catch((err) => { failure = err; })
      .finally(() => { streamDone = true; });

    // Drain the queue at a readable pace while the stream is running.
    while (!streamDone || queue.length) {
      if (controller.signal.aborted) return null;
      const next = queue.shift();
      if (next) {
        if (next.type !== "result") apply(next);
        await sleep(next.type === "stage" ? REVEAL_MS : REVEAL_MS / 2);
      } else {
        await sleep(40);
      }
      if (failure) break;
    }
    await stream;

    if (failure) {
      if ((failure as Error).name === "AbortError") return null;
      const err = failure instanceof ApiError ? failure
        : new ApiError(0, { code: "UNKNOWN", message: "Something went wrong. Please try again." });
      setState((s) => ({ ...s, phase: "error", error: { message: err.message, hint: err.hint, code: err.code } }));
      return null;
    }
    const final = result as AnalysisResult | null;
    if (!final) return null;
    rememberResult(final);
    setState((s) => {
      const stages = { ...s.stages };
      ORDER.forEach((st) => { stages[st] = stages[st] === "pending" ? "skipped" : "done"; });
      return { ...s, phase: "done", stages, result: final };
    });
    await sleep(REVEAL_MS * 1.5);
    return final;
  }, [apply]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState({ phase: "idle", stages: initialStages(), steps: [], result: null, error: null });
  }, []);

  return { state, run, reset };
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
