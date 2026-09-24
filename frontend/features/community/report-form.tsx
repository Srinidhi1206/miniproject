"use client";

import { CheckCircle2, ExternalLink, Phone } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/empty-state";
import { FieldError, FieldHint, Input, Label, Select, Textarea } from "@/components/ui/form";
import { Dropzone } from "@/features/scanner/dropzone";
import { api, ApiError } from "@/lib/api";
import type { ReportOptions, ReportReceipt, ScamType } from "@/types/api";

export function ReportForm() {
  const params = useSearchParams();
  const analysisId = params.get("analysis") ?? "";
  const [options, setOptions] = useState<ReportOptions | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [scamType, setScamType] = useState<ScamType | "">((params.get("type") as ScamType) ?? "");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [location, setLocation] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [receipt, setReceipt] = useState<ReportReceipt | null>(null);
  const ids = { type: useId(), desc: useId(), amount: useId(), loc: useId() };

  useEffect(() => {
    api.reportOptions().then(setOptions).catch((e: Error) => setLoadError(e.message));
  }, []);

  const maxDesc = options?.max_description ?? 2000;

  const validate = () => {
    const e: Record<string, string> = {};
    if (!scamType) e.type = "Choose the type of scam.";
    if (description.trim().length < 10) e.desc = "Describe what happened in at least a sentence.";
    if (description.length > maxDesc) e.desc = `Keep the description under ${maxDesc} characters.`;
    if (amount && (!/^\d+(\.\d{1,2})?$/.test(amount) || Number(amount) > 1e9)) e.amount = "Enter an amount in rupees, numbers only.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setSubmitError(null);
    if (!validate()) return;
    const fd = new FormData();
    fd.append("scam_type", scamType);
    fd.append("description", description.trim());
    if (amount) fd.append("amount_lost", amount);
    if (location) fd.append("location", location);
    if (analysisId) fd.append("analysis_id", analysisId);
    if (file) fd.append("evidence", file);
    setBusy(true);
    try {
      setReceipt(await api.submitReport(fd));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setSubmitError(e instanceof ApiError ? `${e.message}${e.hint ? ` ${e.hint}` : ""}` : "The report couldn't be sent. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  if (receipt) {
    return (
      <Card className="mx-auto max-w-2xl overflow-hidden animate-rise" role="status">
        <div className="border-b border-safe-line bg-safe-bg px-6 py-5">
          <p className="flex items-center gap-2 text-sm font-semibold text-safe"><CheckCircle2 className="size-4" aria-hidden />Report received</p>
          <p className="mt-3 text-sm text-muted">Your report ID</p>
          <p className="font-mono text-3xl font-semibold tracking-tight text-ink">{receipt.report_id}</p>
        </div>
        <div className="space-y-5 p-6">
          <p className="text-sm leading-relaxed text-ink-2">
            Your report has been recorded in SENTINEL. {receipt.location ? `It now counts toward ${receipt.location} on the ` : "It is included in the "}
            <Link href="/map" className="underline underline-offset-4">community scam map</Link>
            {" "}— only the city and scam type are shown publicly{receipt.evidence_attached ? "; your screenshot is kept private" : ""}.
          </p>
          <div>
            <p className="eyebrow mb-2">Important next steps</p>
            <ol className="space-y-2 text-sm text-ink-2">
              {receipt.next_steps.map((s, i) => <li key={i} className="flex gap-2"><span className="font-mono text-faint">{i + 1}.</span>{s}</li>)}
            </ol>
          </div>
          <p className="rounded-sm bg-paper-2 p-3 text-xs leading-relaxed text-muted">
            SENTINEL is a community tool — this report is <strong className="text-ink">not</strong> an official police complaint.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button asChild><a href="https://cybercrime.gov.in" target="_blank" rel="noopener noreferrer">File official complaint <ExternalLink aria-hidden /></a></Button>
            <Button asChild variant="secondary"><a href="tel:1930"><Phone aria-hidden />Call 1930</a></Button>
            <Button asChild variant="ghost"><Link href="/analyze">Analyze something else</Link></Button>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <form onSubmit={submit} noValidate className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <Card className="space-y-6 p-5 sm:p-6">
        {loadError && <ErrorState message={loadError} />}
        {analysisId && (
          <p className="rounded-sm border border-line bg-surface-2 px-3 py-2 text-sm text-ink-2">
            Linked to your analysis <Link href={`/analysis/${analysisId}`} className="font-mono text-xs underline underline-offset-4">{analysisId.slice(0, 8)}…</Link>
          </p>
        )}
        <div>
          <Label htmlFor={ids.type}>Type of scam <span className="text-critical" aria-hidden>*</span></Label>
          <Select id={ids.type} value={scamType} onChange={(e) => setScamType(e.target.value as ScamType)} aria-invalid={!!errors.type} required>
            <option value="" disabled>Select…</option>
            {options?.scam_types.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </Select>
          <FieldError>{errors.type}</FieldError>
        </div>
        <div>
          <Label htmlFor={ids.desc}>What happened? <span className="text-critical" aria-hidden>*</span></Label>
          <Textarea id={ids.desc} value={description} onChange={(e) => setDescription(e.target.value)} rows={6}
            placeholder="e.g. I got a WhatsApp message offering a part-time job. After two small payouts they asked me to deposit ₹5,000…"
            aria-invalid={!!errors.desc} required />
          <FieldHint className="flex justify-between gap-4">
            <span>Don&apos;t include your own phone number, account number or passwords.</span>
            <span className="font-mono tabular-nums">{description.length}/{maxDesc}</span>
          </FieldHint>
          <FieldError>{errors.desc}</FieldError>
        </div>
        <div className="grid gap-6 sm:grid-cols-2">
          <div>
            <Label htmlFor={ids.amount}>Amount lost (optional)</Label>
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted">₹</span>
              <Input id={ids.amount} value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^\d.]/g, ""))}
                inputMode="decimal" placeholder="0" className="pl-7" aria-invalid={!!errors.amount} />
            </div>
            <FieldError>{errors.amount}</FieldError>
          </div>
          <div>
            <Label htmlFor={ids.loc}>Approximate location (optional)</Label>
            <Select id={ids.loc} value={location} onChange={(e) => setLocation(e.target.value)}>
              <option value="">Prefer not to say</option>
              {options?.locations.map((l) => <option key={l.slug} value={l.slug}>{l.city}, {l.region}</option>)}
            </Select>
            <FieldHint>City level only — used for the map.</FieldHint>
          </div>
        </div>
        <div>
          <p className="mb-1.5 text-sm font-medium text-ink">Evidence screenshot (optional)</p>
          <Dropzone file={file} onFile={setFile} label="Add a screenshot" hint="PNG · JPG · WEBP · up to 8 MB"
            error={fileError} onError={setFileError} />
          <FieldHint>Stored privately with location metadata removed. Never shown publicly.</FieldHint>
          <FieldError>{fileError}</FieldError>
        </div>
        {submitError && <ErrorState message={submitError} />}
        <div className="flex justify-end border-t border-line pt-5">
          <Button type="submit" size="lg" disabled={busy || !options}>{busy ? "Sending…" : "Submit report"}</Button>
        </div>
      </Card>

      <aside className="space-y-4 text-sm">
        <Card className="p-5">
          <p className="font-medium text-ink">Lost money? Act now.</p>
          <p className="mt-2 leading-relaxed text-muted">
            Call <a href="tel:1930" className="font-semibold text-ink underline underline-offset-2">1930</a> within the first
            hours — banks can freeze funds only if reported quickly.
          </p>
        </Card>
        <Card className="p-5">
          <p className="font-medium text-ink">What happens to your report</p>
          <ul className="mt-2 space-y-1.5 leading-relaxed text-muted">
            <li>• Stored securely, with a report ID for your records</li>
            <li>• Counted on the public map by city and type only</li>
            <li>• Your description and screenshot stay private</li>
          </ul>
        </Card>
      </aside>
    </form>
  );
}
