"use client";

import { AlertCircle } from "lucide-react";
import Link from "next/link";
import { use, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { AnalysisReport, ReportSkeleton } from "@/features/analysis/analysis-report";
import { api, ApiError } from "@/lib/api";
import { recallResult } from "@/lib/result-cache";
import type { AnalysisResult } from "@/types/api";

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [result, setResult] = useState<AnalysisResult | null>(() => recallResult(id) ?? null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (result?.id === id) return;
    let cancelled = false;
    api.analysis(id).then((r) => !cancelled && setResult(r)).catch((e: ApiError) => !cancelled && setError(e));
    return () => { cancelled = true; };
  }, [id, result?.id]);

  useEffect(() => {
    if (result) document.title = `${result.verdict} (${result.risk_score}/100) · SENTINEL`;
  }, [result]);

  if (error) {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        <AlertCircle className="mx-auto size-8 text-muted" aria-hidden />
        <h1 className="mt-4 text-xl font-semibold">
          {error.status === 404 ? "We couldn't find that report" : "The report couldn't be loaded"}
        </h1>
        <p className="mt-2 text-sm text-muted">
          {error.status === 404 ? "It may have been deleted from this device's history." : error.message}
        </p>
        <Button asChild className="mt-6"><Link href="/analyze">Analyze something</Link></Button>
      </div>
    );
  }
  return result ? <AnalysisReport result={result} /> : <ReportSkeleton />;
}
