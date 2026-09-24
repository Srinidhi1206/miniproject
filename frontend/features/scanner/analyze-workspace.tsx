"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { Scanner, type ScanMode } from "./scanner";

const MODES: ScanMode[] = ["message", "url", "image", "qr", "voice"];

function Inner() {
  const q = useSearchParams().get("mode");
  const mode = MODES.includes(q as ScanMode) ? (q as ScanMode) : "message";
  return <Scanner initialMode={mode} />;
}

export function AnalyzeWorkspace() {
  return (
    <Suspense fallback={<div className="h-96 animate-pulse rounded-lg border border-line bg-surface" />}>
      <Inner />
    </Suspense>
  );
}
