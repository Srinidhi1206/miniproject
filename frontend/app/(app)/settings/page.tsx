"use client";

import { CircleCheck, CircleDashed, CircleX, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, SectionHeading } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/empty-state";
import { api } from "@/lib/api";
import { getClientId, resetClientId } from "@/lib/client-id";
import type { Health } from "@/types/api";

const CAP_LABEL: Record<string, string> = {
  text_model: "Text scam classifier",
  url_model: "URL risk model",
  ocr: "Screenshot text recognition (OCR)",
  qr_decoder: "QR code decoder",
  rag: "Safety knowledge retrieval (RAG)",
  llm_explanations: "LLM plain-language rewriting",
  url_reputation: "Live URL reputation lookup",
  audio: "Voice analysis",
  voice_authenticity: "Deepfake voice detection",
};

function detail(key: string, c: Record<string, unknown>): string {
  if (key === "text_model" && c.status === "ready") return `${c.name} v${c.version} · hold-out F1 ${c.holdout_f1} · ROC-AUC ${c.holdout_roc_auc}`;
  if (key === "url_model" && c.status === "ready") return `${c.name} v${c.version} · hold-out ROC-AUC ${c.holdout_roc_auc} · realistic-set ROC-AUC ${c.sanity_roc_auc}`;
  if (key === "ocr" && c.status === "ready") return String(c.engine);
  if (key === "rag" && c.status === "ready") return `${c.chunks} passages · ${c.embedder} · ${c.backend}`;
  if (key === "llm_explanations") return c.status === "ready" ? String(c.provider) : String(c.note ?? "Disabled");
  if (key === "url_reputation") return c.status === "ready" ? "Google Safe Browsing" : "No API key configured — links are judged on structure only";
  return String(c.note ?? c.engine ?? "");
}

export default function SettingsPage() {
  const [deviceId, setDeviceId] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => { setError(null); api.health().then(setHealth).catch((e: Error) => setError(e.message)); };
  useEffect(() => { setDeviceId(getClientId()); load(); }, []);

  return (
    <div className="space-y-8">
      <SectionHeading as="h1" eyebrow="Settings" title="Privacy & system status" />

      <Card className="p-5 sm:p-6">
        <h2 className="font-semibold text-ink">Your device</h2>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted">
          SENTINEL works without an account. A random ID stored in this browser groups your scans into a history.
          It isn&apos;t linked to your name, phone number or email.
        </p>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-[10rem_1fr]">
          <dt className="text-muted">Anonymous device ID</dt>
          <dd className="break-all font-mono text-xs text-ink">{deviceId || "—"}</dd>
          <dt className="text-muted">What is stored</dt>
          <dd className="text-ink-2">The risk result and a short preview with long numbers masked. Full message text and uploaded images are not stored.</dd>
        </dl>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setDeviceId(resetClientId())}><RefreshCw aria-hidden />Start a new anonymous ID</Button>
        </div>
        <p className="mt-2 text-xs text-muted">A new ID hides your previous history on this device. To delete it permanently, use “Clear history” first.</p>
      </Card>

      <Card className="p-5 sm:p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold text-ink">System capabilities</h2>
            <p className="mt-1 text-sm text-muted">Live status from the analysis service. Unavailable features are never simulated.</p>
          </div>
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw aria-hidden />Refresh</Button>
        </div>
        {error && <div className="mt-4"><ErrorState message={error} onRetry={load} /></div>}
        {health && (
          <ul className="mt-4 divide-y divide-line">
            {Object.entries(health.capabilities).map(([key, c]) => {
              const ready = c.status === "ready";
              const off = c.status === "unavailable" || c.status === "error";
              const Icon = ready ? CircleCheck : off ? CircleX : CircleDashed;
              return (
                <li key={key} className="flex items-start gap-3 py-3">
                  <Icon className={`mt-0.5 size-4 shrink-0 ${ready ? "text-safe" : off ? "text-muted" : "text-warn"}`} aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-ink">{CAP_LABEL[key] ?? key}</p>
                    <p className="mt-0.5 break-words text-xs text-muted">{detail(key, c)}</p>
                  </div>
                  <span className="shrink-0 font-mono text-[0.68rem] uppercase tracking-wider text-muted">{c.status.replace("_", " ")}</span>
                </li>
              );
            })}
            <li className="flex items-start gap-3 py-3">
              <CircleCheck className={`mt-0.5 size-4 ${health.database.status === "ready" ? "text-safe" : "text-critical"}`} aria-hidden />
              <div className="flex-1">
                <p className="text-sm font-medium text-ink">Database</p>
                <p className="mt-0.5 text-xs text-muted">{health.database.dialect}</p>
              </div>
              <span className="font-mono text-[0.68rem] uppercase tracking-wider text-muted">{health.database.status}</span>
            </li>
          </ul>
        )}
      </Card>
    </div>
  );
}
