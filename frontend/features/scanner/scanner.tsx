"use client";

import * as Tabs from "@radix-ui/react-tabs";
import { AlertCircle, ArrowRight, Link2, Lock, MessageSquareText, Mic, QrCode, ScanText } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { FieldError, FieldHint, Input, Label, Textarea } from "@/components/ui/form";
import { useAnalysisRun } from "@/hooks/use-analysis-run";
import type { AnalyzeInput } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Channel } from "@/types/api";

import { Dropzone, MAX_MB } from "./dropzone";
import { EXAMPLES } from "./examples";
import { ProgressConsole } from "./progress-console";

export type ScanMode = "message" | "url" | "image" | "qr" | "voice";

const MODES: { id: ScanMode; label: string; icon: typeof MessageSquareText; disabled?: boolean }[] = [
  { id: "message", label: "Message", icon: MessageSquareText },
  { id: "url", label: "Link", icon: Link2 },
  { id: "image", label: "Screenshot", icon: ScanText },
  { id: "qr", label: "QR code", icon: QrCode },
  { id: "voice", label: "Voice", icon: Mic, disabled: true },
];

const CHANNELS: { id: Channel; label: string }[] = [
  { id: "sms", label: "SMS" },
  { id: "whatsapp", label: "WhatsApp" },
  { id: "email", label: "Email" },
  { id: "job_offer", label: "Job offer" },
  { id: "other", label: "Other" },
];

const MAX_TEXT = 10_000;

export function Scanner({ initialMode = "message", className, compact = false }: {
  initialMode?: ScanMode;
  className?: string;
  compact?: boolean;
}) {
  const router = useRouter();
  const { state, run, reset } = useAnalysisRun();
  const [mode, setMode] = useState<ScanMode>(initialMode);
  const [channel, setChannel] = useState<Channel>("sms");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [qrFile, setQrFile] = useState<File | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const textId = useId();
  const urlId = useId();
  const errId = useId();

  useEffect(() => setMode(initialMode), [initialMode]);
  useEffect(() => setFieldError(null), [mode]);

  const buildInput = (): AnalyzeInput | string => {
    if (mode === "message") {
      const t = text.trim();
      if (t.length < 3) return "Paste the message you received first.";
      if (t.length > MAX_TEXT) return `That's longer than ${MAX_TEXT.toLocaleString()} characters. Paste the most relevant part.`;
      return { kind: "text", text: t, channel };
    }
    if (mode === "url") {
      const u = url.trim();
      if (!u) return "Enter the link you want to check.";
      if (/\s/.test(u)) return "Links can't contain spaces. Paste just the address.";
      return { kind: "url", url: u };
    }
    if (mode === "image") return imageFile ? { kind: "image", file: imageFile, channel: "other" } : "Choose a screenshot to analyse.";
    if (mode === "qr") return qrFile ? { kind: "qr", file: qrFile } : "Choose an image of the QR code.";
    return "Voice analysis isn't available yet.";
  };

  const submit = async () => {
    const input = buildInput();
    if (typeof input === "string") {
      setFieldError(input);
      return;
    }
    setFieldError(null);
    const result = await run(input);
    if (result) router.push(`/analysis/${result.id}`);
  };

  const subject =
    mode === "message" ? `${CHANNELS.find((c) => c.id === channel)?.label} message · ${text.trim().length} chars`
      : mode === "url" ? url.trim()
        : mode === "image" ? `screenshot · ${imageFile?.name ?? "pasted image"}`
          : `QR image · ${qrFile?.name ?? "pasted image"}`;

  if (state.phase === "running" || state.phase === "done") {
    return (
      <div className={className}>
        <ProgressConsole state={state} subject={subject} />
      </div>
    );
  }

  return (
    <div className={cn("overflow-hidden rounded-lg border border-line-strong bg-surface shadow-[0_1px_0_rgba(0,0,0,0.03),0_12px_40px_-24px_rgba(20,20,20,0.25)]", className)}>
      <Tabs.Root value={mode} onValueChange={(v) => setMode(v as ScanMode)}>
        <div className="border-b border-line bg-surface-2 px-4 pt-4 sm:px-6">
          <p className="eyebrow mb-3">What would you like to check?</p>
          <Tabs.List aria-label="Type of content to check" className="-mb-px flex gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {MODES.map((m) => (
              <Tabs.Trigger
                key={m.id}
                value={m.id}
                className={cn(
                  "group relative flex shrink-0 items-center gap-2 border-b-2 border-transparent px-3 pb-3 pt-1 text-sm font-medium text-muted transition-colors hover:text-ink",
                  "data-[state=active]:border-ink data-[state=active]:text-ink",
                )}
              >
                <m.icon className="size-4" aria-hidden />
                {m.label}
                {m.disabled && (
                  <span className="rounded-xs bg-paper-2 px-1 py-px font-mono text-[0.6rem] uppercase tracking-wider text-faint">Soon</span>
                )}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
        </div>

        <form
          onSubmit={(e) => { e.preventDefault(); submit(); }}
          className={cn("p-4 sm:p-6", compact ? "space-y-4" : "space-y-5")}
          noValidate
        >
          <Tabs.Content value="message" className="space-y-4 focus-visible:outline-none">
            <fieldset>
              <legend className="mb-2 text-sm font-medium text-ink">Where did you receive it?</legend>
              <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Message source">
                {CHANNELS.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    role="radio"
                    aria-checked={channel === c.id}
                    onClick={() => setChannel(c.id)}
                    className={cn(
                      "rounded-full border px-3 py-1 text-sm transition-colors",
                      channel === c.id ? "border-ink bg-ink text-white" : "border-line-strong bg-surface text-ink-2 hover:border-ink",
                    )}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </fieldset>
            <div>
              <div className="flex items-baseline justify-between">
                <Label htmlFor={textId}>Paste the message</Label>
                <ExamplePicker onPick={(t, ch) => { setText(t); setChannel(ch); setFieldError(null); }} />
              </div>
              <Textarea
                id={textId}
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit(); }}
                placeholder="e.g. Dear customer, your account will be blocked today. Update your KYC at…"
                rows={compact ? 5 : 6}
                maxLength={MAX_TEXT + 500}
                aria-invalid={!!fieldError}
                aria-describedby={fieldError ? errId : undefined}
              />
              <FieldHint className="flex justify-between gap-4">
                <span>Include links and phone numbers exactly as received. Ctrl+Enter to analyse.</span>
                <span className={cn("font-mono tabular-nums", text.length > MAX_TEXT && "text-critical")}>
                  {text.length.toLocaleString()}/{MAX_TEXT.toLocaleString()}
                </span>
              </FieldHint>
            </div>
          </Tabs.Content>

          <Tabs.Content value="url" className="focus-visible:outline-none">
            <Label htmlFor={urlId}>Paste the link</Label>
            <Input
              id={urlId}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/login"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              className="font-mono text-sm"
              aria-invalid={!!fieldError}
              aria-describedby={fieldError ? errId : undefined}
            />
            <FieldHint className="flex items-start gap-1.5">
              <Lock className="mt-px size-3 shrink-0" aria-hidden />
              SENTINEL never opens the link. It inspects the address itself, so checking is always safe.
            </FieldHint>
          </Tabs.Content>

          <Tabs.Content value="image" className="focus-visible:outline-none">
            <Dropzone
              file={imageFile}
              onFile={setImageFile}
              label="Upload a screenshot"
              hint={`PNG · JPG · WEBP · up to ${MAX_MB} MB`}
              error={fieldError}
              onError={setFieldError}
            />
            <FieldHint>WhatsApp or SMS screenshots, job posters, payment requests. SENTINEL reads the text, finds links and QR codes, then analyses them.</FieldHint>
          </Tabs.Content>

          <Tabs.Content value="qr" className="focus-visible:outline-none">
            <Dropzone
              file={qrFile}
              onFile={setQrFile}
              label="Upload a QR code image"
              hint={`Photo or screenshot · up to ${MAX_MB} MB`}
              error={fieldError}
              onError={setFieldError}
            />
            <FieldHint>SENTINEL decodes the QR code and checks where it leads — a website, or a UPI payment request.</FieldHint>
          </Tabs.Content>

          <Tabs.Content value="voice" className="focus-visible:outline-none">
            <div className="rounded-sm border border-dashed border-line-strong bg-surface-2 p-5">
              <p className="font-medium text-ink">Voice analysis isn&apos;t available in the current version.</p>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">
                Speech-to-text and voice-authenticity (deepfake) detection are planned for a later phase. SENTINEL won&apos;t
                show a result it can&apos;t genuinely produce. If you have a transcript or remember what the caller said,
                paste it as a message instead.
              </p>
              <Button type="button" variant="secondary" size="sm" className="mt-4" onClick={() => setMode("message")}>
                Check a call transcript as a message
              </Button>
            </div>
          </Tabs.Content>

          {state.phase === "error" && state.error && (
            <div role="alert" className="flex gap-3 rounded-sm border border-critical-line bg-critical-bg p-3 text-sm">
              <AlertCircle className="mt-0.5 size-4 shrink-0 text-critical" aria-hidden />
              <div>
                <p className="font-medium text-critical">{state.error.message}</p>
                {state.error.hint && <p className="mt-0.5 text-ink-2">{state.error.hint}</p>}
              </div>
            </div>
          )}
          <FieldError id={errId}>{fieldError}</FieldError>

          {mode !== "voice" && (
            <div className="flex flex-col-reverse items-stretch gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="flex items-center gap-1.5 text-xs text-muted">
                <Lock className="size-3" aria-hidden /> No sign-up. Full message text isn&apos;t stored.
              </p>
              <Button type="submit" size="lg" onClick={() => state.phase === "error" && reset()}>
                Analyse {mode === "message" ? "message" : mode === "url" ? "link" : mode === "image" ? "screenshot" : "QR code"}
                <ArrowRight aria-hidden />
              </Button>
            </div>
          )}
        </form>
      </Tabs.Root>
    </div>
  );
}

function ExamplePicker({ onPick }: { onPick: (text: string, channel: Channel) => void }) {
  return (
    <div className="relative">
      <select
        aria-label="Insert an example message"
        className="cursor-pointer appearance-none bg-transparent pr-1 text-right text-xs text-muted underline decoration-line-strong underline-offset-4 hover:text-ink"
        value=""
        onChange={(e) => {
          const ex = EXAMPLES[Number(e.target.value)];
          if (ex) onPick(ex.text, ex.channel);
        }}
      >
        <option value="" disabled>Try an example…</option>
        {EXAMPLES.map((ex, i) => (
          <option key={i} value={i}>{ex.label}</option>
        ))}
      </select>
    </div>
  );
}
