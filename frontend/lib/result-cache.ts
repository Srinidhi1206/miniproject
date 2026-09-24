import type { AnalysisResult } from "@/types/api";

// Keeps the just-finished result in memory so the report page renders
// instantly after navigation instead of refetching it.
const cache = new Map<string, AnalysisResult>();

export function rememberResult(r: AnalysisResult) {
  cache.set(r.id, r);
  if (cache.size > 20) cache.delete(cache.keys().next().value as string);
}

export function recallResult(id: string): AnalysisResult | undefined {
  return cache.get(id);
}
