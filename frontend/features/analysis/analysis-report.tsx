"use client";

import * as Collapsible from "@radix-ui/react-collapsible";
import {
  ArrowRight, BookOpen, Check, ChevronDown, Copy, Flag, Info, Link2, QrCode, RotateCcw, ShieldCheck, TriangleAlert,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { RiskBadge, ScoreMeter } from "@/components/risk/risk-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { INPUT_LABEL, RISK, SEVERITY } from "@/lib/risk";
import { cn, formatDateTime } from "@/lib/utils";
import type { AnalysisResult, Evidence } from "@/types/api";

import { TechnicalDetails } from "./technical-details";

const REPORT_TYPE: Record<string, string> = {
  PIN_REQUEST: "upi", RECEIVE_MONEY_TRICK: "upi", MISDIRECTED_MONEY: "upi", UPI_BAIT_NOTE: "qr", UPI_PAYMENT_QR: "qr",
  TASK_JOB: "job", UPFRONT_FEE: "job", DIGITAL_ARREST: "call", AUTHORITY_CLAIM: "call", UNREALISTIC_RETURNS: "investment",
  CRYPTO_INVEST: "investment", BRAND_IMPERSONATION: "fake_website", TYPOSQUAT: "fake_website",
};

export function AnalysisReport({ result }: { result: AnalysisResult }) {
  const r = RISK[result.risk_level];
  const risky = result.risk_level === "HIGH" || result.risk_level === "CRITICAL";
  const reportType = result.findings.map((f) => REPORT_TYPE[f.code]).find(Boolean)
    ?? (result.input_type === "QR" ? "qr" : result.input_type === "URL" ? "phishing" : "phishing");

  return (
    <article className="space-y-6 animate-rise" aria-labelledby="verdict-heading">
      {/* --------------------------------------------------------- verdict */}
      <header className={cn("overflow-hidden rounded-lg border", r.line, "bg-surface")}>
        <div className={cn("flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3 sm:px-7", r.line, r.bg)}>
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-ink-2">Analysis complete</p>
          <p className="font-mono text-xs text-muted">
            {INPUT_LABEL[result.input_type]}
            {result.channel && result.channel !== "other" ? ` · ${result.channel.replace("_", " ")}` : ""} · {formatDateTime(result.created_at)}
          </p>
        </div>
        <div className="grid gap-8 px-5 py-7 sm:px-7 md:grid-cols-[1fr_auto] md:items-end">
          <div>
            <p className={cn("text-sm font-semibold uppercase tracking-[0.16em]", r.text)}>{r.label}</p>
            <h1 id="verdict-heading" className="mt-2 text-4xl font-semibold tracking-[-0.03em] text-ink sm:text-5xl">
              {result.verdict}
            </h1>
            <p className="mt-4 max-w-2xl text-[0.98rem] leading-relaxed text-ink-2">{result.explanation.summary}</p>
          </div>
          <div className="md:text-right">
            <p className="font-mono text-6xl font-semibold tabular-nums tracking-tight text-ink sm:text-7xl">
              {result.risk_score}
              <span className="text-2xl text-faint">/100</span>
            </p>
            <p className="mt-1 text-xs text-muted">
              Model confidence {Math.round(result.confidence * 100)}% · analyzed in {result.duration_ms} ms
            </p>
          </div>
        </div>
        <div className="px-5 pb-6 sm:px-7">
          <ScoreMeter score={result.risk_score} />
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="min-w-0 space-y-6">
          {/* -------------------------------------------------- findings */}
          <Card className="p-5 sm:p-6">
            <SectionTitle eyebrow="Evidence" title="What SENTINEL found" />
            {result.findings.length === 0 ? (
              <p className="mt-4 flex items-center gap-2 text-sm text-muted">
                <ShieldCheck className="size-4 text-safe" aria-hidden />
                No scam tactics were detected by the rules.
              </p>
            ) : (
              <ul className="mt-4 divide-y divide-line">
                {result.findings.map((f) => <FindingRow key={f.code + f.source} f={f} />)}
              </ul>
            )}
            {result.reassurances.length > 0 && (
              <div className="mt-5 border-t border-line pt-4">
                <p className="eyebrow mb-2">Reassuring signals</p>
                <ul className="space-y-2">
                  {result.reassurances.map((e) => (
                    <li key={e.code} className="flex gap-2 text-sm text-ink-2">
                      <Check className="mt-0.5 size-4 shrink-0 text-safe" aria-hidden />
                      <span>{e.label}{e.detail && <span className="text-muted"> — {e.detail}</span>}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          {/* ---------------------------------------------- why it matters */}
          <Card className="p-5 sm:p-6">
            <SectionTitle eyebrow="Explanation" title="Why this matters" />
            <ul className="mt-4 space-y-3">
              {result.explanation.why_it_matters.map((w, i) => (
                <li key={i} className="flex gap-3 text-[0.95rem] leading-relaxed text-ink-2">
                  <span className="mt-2.5 size-1.5 shrink-0 bg-ink" aria-hidden />
                  <span>{w}</span>
                </li>
              ))}
            </ul>
            {result.explanation.sources.length > 0 && (
              <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-line pt-4">
                <span className="text-xs text-muted">Guidance from:</span>
                {Array.from(new Map(result.explanation.sources.map((s) => [s.slug, s])).values()).map((s) => (
                  <Link key={s.slug} href={`/safety/${s.slug}`}
                    className="inline-flex items-center gap-1 rounded-full border border-line px-2.5 py-0.5 text-xs text-ink-2 hover:border-ink hover:text-ink">
                    <BookOpen className="size-3" aria-hidden />{s.title}
                  </Link>
                ))}
              </div>
            )}
          </Card>

          <SubmittedContent result={result} />
        </div>

        {/* ------------------------------------------------------ actions */}
        <aside className="space-y-4 lg:sticky lg:top-6 lg:self-start" aria-label="Recommended actions">
          <Card className={cn("p-5", risky && "border-ink")}>
            <SectionTitle eyebrow="Next steps" title="What you should do" />
            <ol className="mt-4 space-y-4">
              {result.recommendations.map((rec, i) => (
                <li key={rec.id} className="flex gap-3">
                  <span className={cn(
                    "grid size-6 shrink-0 place-items-center rounded-full font-mono text-xs font-semibold",
                    rec.priority === "critical" ? "bg-ink text-white" : "border border-line-strong text-ink-2",
                  )}>{i + 1}</span>
                  <div>
                    <p className="text-sm font-semibold leading-snug text-ink">{rec.title}</p>
                    <p className="mt-1 text-[0.8rem] leading-relaxed text-muted">{rec.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Card>
          <div className="grid gap-2">
            {result.classification !== "SAFE" && (
              <Button asChild size="lg" variant={risky ? "primary" : "secondary"}>
                <Link href={`/report?analysis=${result.id}&type=${reportType}`}><Flag aria-hidden />Report this scam</Link>
              </Button>
            )}
            <Button asChild size="lg" variant="secondary">
              <Link href="/analyze"><RotateCcw aria-hidden />Analyze another</Link>
            </Button>
            <CopyLink />
          </div>
        </aside>
      </div>

      {result.limitations.length > 0 && (
        <div className="flex gap-3 rounded-md border border-warn-line bg-warn-bg/60 p-4 text-sm" role="note">
          <Info className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden />
          <div>
            <p className="font-medium text-ink">Limits of this analysis</p>
            <ul className="mt-1 list-disc space-y-0.5 pl-4 text-ink-2">
              {result.limitations.map((l) => <li key={l}>{l}</li>)}
            </ul>
          </div>
        </div>
      )}

      <TechnicalDetails result={result} />

      <p className="text-center text-xs leading-relaxed text-faint">
        Automated assessment · it can be wrong. When money or accounts are involved, verify through official channels.
      </p>
    </article>
  );
}

function SectionTitle({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div>
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="mt-1 text-lg font-semibold tracking-[-0.01em] text-ink">{title}</h2>
    </div>
  );
}

function FindingRow({ f }: { f: Evidence }) {
  const s = SEVERITY[f.severity];
  const [open, setOpen] = useState(false);
  return (
    <li className="py-3.5">
      <Collapsible.Root open={open} onOpenChange={setOpen}>
        <div className="flex items-start gap-3">
          <span className={cn("mt-0.5 shrink-0 rounded-xs px-1.5 py-0.5 font-mono text-[0.62rem] font-semibold uppercase tracking-wider", s.bg, s.text)}>
            {s.label}
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-medium leading-snug text-ink">{f.label}</p>
            {f.excerpt && (
              <p className="mt-1.5 break-words rounded-xs border-l-2 border-line-strong bg-surface-2 px-2 py-1 font-mono text-xs text-ink-2">
                “{f.excerpt}”
              </p>
            )}
            <Collapsible.Content className="mt-2 text-sm leading-relaxed text-muted data-[state=open]:animate-fade">
              {f.detail}
              <span className="mt-1 block font-mono text-[0.68rem] text-faint">
                {f.code} · {f.source} · {f.weight > 0 ? `+${f.weight}` : f.weight} pts
              </span>
            </Collapsible.Content>
          </div>
          {f.detail && (
            <Collapsible.Trigger asChild>
              <button type="button" className="shrink-0 rounded-sm p-1 text-muted hover:bg-paper-2 hover:text-ink"
                aria-label={open ? `Hide details for ${f.label}` : `Why does “${f.label}” matter?`}>
                <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} aria-hidden />
              </button>
            </Collapsible.Trigger>
          )}
        </div>
      </Collapsible.Root>
    </li>
  );
}

function SubmittedContent({ result }: { result: AnalysisResult }) {
  const x = result.extracted;
  return (
    <Card className="p-5 sm:p-6">
      <SectionTitle eyebrow="Input" title="What you submitted" />
      <p className="mt-3 break-words rounded-sm bg-surface-2 p-3 font-mono text-xs leading-relaxed text-ink-2">
        {result.input_preview || "—"}
      </p>
      <p className="mt-2 text-xs text-muted">Long numbers are masked. The full text isn&apos;t stored.</p>
      {(x.qr_payload || x.urls.length > 0 || x.ocr_confidence != null) && (
        <dl className="mt-4 grid gap-3 border-t border-line pt-4 text-sm sm:grid-cols-2">
          {x.ocr_confidence != null && (
            <div>
              <dt className="eyebrow">Text read from image</dt>
              <dd className="mt-1 text-ink-2">OCR confidence {Math.round(x.ocr_confidence * 100)}%</dd>
            </div>
          )}
          {x.qr_payload && (
            <div className="sm:col-span-2">
              <dt className="eyebrow flex items-center gap-1.5"><QrCode className="size-3" aria-hidden />QR code contains</dt>
              <dd className="mt-1 break-all font-mono text-xs text-ink-2">{x.qr_payload}</dd>
            </div>
          )}
          {x.upi && (
            <div className="sm:col-span-2">
              <dt className="eyebrow">UPI payment request</dt>
              <dd className="mt-1 text-ink-2">
                Pays <span className="font-mono">{x.upi.payee_vpa ?? "unknown"}</span>
                {x.upi.payee_name && <> ({x.upi.payee_name})</>}
                {x.upi.amount != null && <> · <span className="font-semibold">₹{x.upi.amount.toLocaleString("en-IN")}</span></>}
                {x.upi.note && <> · note “{x.upi.note}”</>}
              </dd>
            </div>
          )}
          {x.urls.length > 0 && (
            <div className="sm:col-span-2">
              <dt className="eyebrow flex items-center gap-1.5"><Link2 className="size-3" aria-hidden />Links found ({x.urls.length})</dt>
              <dd className="mt-1 space-y-1">
                {x.urls.map((u) => {
                  const comp = result.breakdown.components.find((c) => c.component === "url" && c.subject.startsWith(u.slice(0, 40)));
                  return (
                    <p key={u} className="flex items-center justify-between gap-3 font-mono text-xs">
                      <span className="break-all text-ink-2">{u}</span>
                      {comp && <RiskBadge level={comp.score >= 80 ? "CRITICAL" : comp.score >= 60 ? "HIGH" : comp.score >= 30 ? "MEDIUM" : "LOW"} score={comp.score} />}
                    </p>
                  );
                })}
              </dd>
              <p className="mt-2 flex items-center gap-1.5 text-xs text-muted">
                <TriangleAlert className="size-3" aria-hidden />Links were analyzed without being opened.
              </p>
            </div>
          )}
        </dl>
      )}
    </Card>
  );
}

function CopyLink() {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="ghost"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(window.location.href);
          setCopied(true);
          setTimeout(() => setCopied(false), 1800);
        } catch {
          /* clipboard blocked: ignore */
        }
      }}
    >
      {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
      {copied ? "Link copied" : "Copy link to this report"}
    </Button>
  );
}

export function ReportSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading report">
      <div className="h-64 animate-pulse rounded-lg border border-line bg-surface" />
      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="h-72 animate-pulse rounded-md border border-line bg-surface" />
        <div className="h-72 animate-pulse rounded-md border border-line bg-surface" />
      </div>
    </div>
  );
}

export { ArrowRight };
