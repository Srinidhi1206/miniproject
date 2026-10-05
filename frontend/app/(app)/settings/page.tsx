"use client";

import { CircleAlert, CircleCheck, CircleX, History, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, SectionHeading } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/empty-state";
import { api } from "@/lib/api";
import { getClientId, resetClientId } from "@/lib/client-id";
import type { Health } from "@/types/api";

type Level = "active" | "limited" | "unavailable";

interface Protection {
  label: string;
  description: string;
  level: Level;
}

const ready = (h: Health, key: string) => h.capabilities[key]?.status === "ready";

/**
 * Plain-language protection status, derived from the live /api/health check.
 * Technical details (models, metrics, engines, database) stay in the API —
 * `GET /api/health` — and are deliberately not shown to end users.
 */
function protections(h: Health): Protection[] {
  const list: Protection[] = [
    {
      label: "Scam message detection",
      description: "Checks SMS, WhatsApp, email and job messages for scam tactics.",
      // Rule-based checks still run if the learned model is missing, so that is "limited", not off.
      level: ready(h, "text_model") ? "active" : "limited",
    },
    {
      label: "Suspicious link checking",
      description: "Inspects links for look-alike and risky websites — without opening them.",
      level: ready(h, "url_model") ? "active" : "limited",
    },
    {
      label: "Screenshot & QR scanning",
      description: "Reads text in screenshots and decodes QR codes, then checks what they contain.",
      level: ready(h, "ocr") && ready(h, "qr_decoder") ? "active"
        : ready(h, "ocr") || ready(h, "qr_decoder") ? "limited" : "unavailable",
    },
    {
      label: "Safety guidance",
      description: "Explains each warning sign and what to do next.",
      level: ready(h, "rag") ? "active" : "limited",
    },
  ];
  // Only listed when it is actually configured — never claimed otherwise.
  if (ready(h, "url_reputation")) {
    list.push({
      label: "Live link reputation checking",
      description: "Also checks links against an up-to-date list of known dangerous websites.",
      level: "active",
    });
  }
  list.push({
    label: "Secure anonymous history",
    description: "Keeps your past checks on this device, without an account.",
    level: h.database.status === "ready" ? "active" : "unavailable",
  });
  return list;
}

const LEVEL = {
  active: { text: "Active", icon: CircleCheck, tone: "text-safe" },
  limited: { text: "Limited", icon: CircleAlert, tone: "text-warn" },
  unavailable: { text: "Unavailable", icon: CircleX, tone: "text-muted" },
} as const;

export default function SettingsPage() {
  const [deviceId, setDeviceId] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [renewed, setRenewed] = useState(false);

  const load = () => { setError(null); api.health().then(setHealth).catch((e: Error) => setError(e.message)); };
  useEffect(() => { setDeviceId(getClientId()); load(); }, []);

  return (
    <div className="space-y-8">
      <SectionHeading as="h1" eyebrow="Settings" title="Privacy & protection" />

      <Card className="p-5 sm:p-6">
        <h2 className="font-semibold text-ink">Your privacy</h2>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted">
          SENTINEL works without an account. A random ID created in this browser keeps your past checks together.
          It isn&apos;t linked to your name, phone number or email.
        </p>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-[10rem_1fr]">
          <dt className="text-muted">Anonymous device ID</dt>
          <dd className="break-all font-mono text-xs text-ink">{deviceId || "—"}</dd>
          <dt className="text-muted">What we keep</dt>
          <dd className="text-ink-2">The result of each check and a short preview, with long numbers such as phone or account numbers masked.</dd>
          <dt className="text-muted">What we don&apos;t keep</dt>
          <dd className="text-ink-2">The full text of your messages and the images you upload. Links you check are never opened.</dd>
        </dl>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => { setDeviceId(resetClientId()); setRenewed(true); }}>
            <RefreshCw aria-hidden />Start a new anonymous ID
          </Button>
          <Button asChild variant="ghost">
            <Link href="/history"><History aria-hidden />Manage or clear history</Link>
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted" role={renewed ? "status" : undefined}>
          {renewed
            ? "Done — you have a new anonymous ID. Your earlier checks are no longer shown on this device."
            : "A new ID hides your previous history on this device. To delete it permanently, clear your history first."}
        </p>
      </Card>

      <Card className="p-5 sm:p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold text-ink">Protection status</h2>
            <p className="mt-1 text-sm text-muted">Checked live with SENTINEL&apos;s analysis service.</p>
          </div>
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw aria-hidden />Refresh</Button>
        </div>
        {error && <div className="mt-4"><ErrorState message={error} onRetry={load} /></div>}
        {!health && !error && (
          <div className="mt-4 space-y-2" aria-busy="true">
            {[0, 1, 2, 3].map((i) => <div key={i} className="h-10 animate-pulse rounded-sm bg-paper-2" />)}
          </div>
        )}
        {health && (
          <>
            <ul className="mt-4 divide-y divide-line">
              {protections(health).map((p) => {
                const l = LEVEL[p.level];
                return (
                  <li key={p.label} className="flex items-start gap-3 py-3">
                    <l.icon className={`mt-0.5 size-4 shrink-0 ${l.tone}`} aria-hidden />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-ink">{p.label}</p>
                      <p className="mt-0.5 text-xs text-muted">{p.description}</p>
                    </div>
                    <span className={`shrink-0 text-xs font-medium ${l.tone}`}>{l.text}</span>
                  </li>
                );
              })}
            </ul>
            <p className="mt-4 border-t border-line pt-4 text-xs text-muted">
              More protection features, such as checking voice calls, are coming soon.
            </p>
          </>
        )}
      </Card>
    </div>
  );
}
