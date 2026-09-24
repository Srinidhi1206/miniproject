import {
  ArrowRight, ArrowUpRight, Ban, BookOpenCheck, BrainCircuit, CircleDashed, FileSearch, Gauge, Map, MessageSquareText,
  Route, ScanText,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Scanner } from "@/features/scanner/scanner";

const PIPELINE = [
  {
    n: "01", icon: Route, title: "Route the input",
    body: "An orchestration agent identifies what you submitted and picks the right specialist tools.",
    tools: ["input_router"],
  },
  {
    n: "02", icon: ScanText, title: "Extract content",
    body: "Screenshots are read with OCR, QR codes are decoded, and links are pulled out of text.",
    tools: ["ocr_reader", "qr_decoder", "url_extractor"],
  },
  {
    n: "03", icon: FileSearch, title: "Check for scam signals",
    body: "A trained text classifier and a URL model score the content; 40+ transparent rules name the tactics used.",
    tools: ["text_classifier", "url_analyzer", "upi_analyzer"],
  },
  {
    n: "04", icon: Gauge, title: "Score the risk",
    body: "A documented formula combines model probabilities and evidence into one 0–100 score.",
    tools: ["risk_engine"],
  },
  {
    n: "05", icon: BookOpenCheck, title: "Explain in plain language",
    body: "Guidance is retrieved from a curated safety knowledge base to explain why it matters and what to do.",
    tools: ["explanation_service"],
  },
];

const CATCHES = [
  { title: "UPI & QR payment tricks", body: "“Scan to receive money”, fake refunds, collect requests disguised as cashback." },
  { title: "KYC & account-block phishing", body: "Bank, wallet, FASTag or electricity messages threatening suspension with a link." },
  { title: "Job and task scams", body: "Registration fees, “like videos, earn daily”, Telegram task groups." },
  { title: "Fake police & digital arrest", body: "Customs parcels, CBI calls, demands to stay on video and transfer money." },
  { title: "Look-alike websites", body: "Brand names on unofficial domains, typosquats, free-hosting pages, .apk downloads." },
  { title: "Investment & prize bait", body: "Guaranteed returns, crypto doubling, lotteries you never entered." },
];

const BANDS = [
  { range: "0–29", label: "Low", cls: "bg-safe", text: "No strong scam signals found. Still verify anything that asks for money or codes." },
  { range: "30–59", label: "Medium", cls: "bg-warn", text: "Some warning signs. Could be genuine — confirm through an official channel first." },
  { range: "60–79", label: "High", cls: "bg-high", text: "Multiple scam tactics present. Don’t click, pay or share details." },
  { range: "80–100", label: "Critical", cls: "bg-critical", text: "Matches known scam patterns strongly. Treat it as fraud and report it." },
];

export default function HomePage() {
  return (
    <>
      {/* ------------------------------------------------------------ hero */}
      <section className="relative overflow-hidden border-b border-line">
        <div className="bg-grid pointer-events-none absolute inset-0 [mask-image:linear-gradient(to_bottom,black,transparent_85%)]" aria-hidden />
        <div className="relative mx-auto max-w-6xl px-4 pb-10 pt-14 sm:px-6 sm:pt-20">
          <p className="eyebrow animate-rise">AI scam prevention · free · no sign-up</p>
          <h1 className="mt-4 max-w-4xl animate-rise text-[2.35rem] font-semibold leading-[1.04] tracking-[-0.035em] text-ink [animation-delay:60ms] sm:text-6xl lg:text-[4.4rem]">
            Before you click, pay, reply, or trust — <span className="relative whitespace-nowrap">
              check it.
              <span className="absolute inset-x-0 bottom-[0.08em] -z-10 h-[0.28em] bg-signal" aria-hidden />
            </span>
          </h1>
          <p className="mt-6 max-w-2xl animate-rise text-lg leading-relaxed text-ink-2 [animation-delay:120ms]">
            Paste a message, drop a screenshot, check a link or scan a QR code. SENTINEL shows you the risk, the exact
            warning signs it found, and what to do next — in plain language.
          </p>
          <div className="mt-8 flex animate-rise flex-wrap gap-3 [animation-delay:180ms]">
            <Button asChild size="lg">
              <a href="#scan">Analyze something suspicious <ArrowRight aria-hidden /></a>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <a href="#how-it-works">How SENTINEL works</a>
            </Button>
          </div>
        </div>

        {/* ---------------------------------------------------------- scanner */}
        <div id="scan" className="relative mx-auto max-w-6xl scroll-mt-20 px-4 pb-16 sm:px-6">
          <div className="grid gap-8 lg:grid-cols-[1fr_17rem]">
            <Scanner className="animate-rise [animation-delay:240ms]" />
            <aside className="hidden space-y-6 pt-2 lg:block" aria-label="What happens to your content">
              <div>
                <p className="eyebrow mb-2">What you get</p>
                <ul className="space-y-2.5 text-sm text-ink-2">
                  {["A 0–100 risk score and level", "The specific warning signs found", "Why they matter", "Clear next steps", "Technical details, if you want them"].map((t) => (
                    <li key={t} className="flex gap-2"><span className="mt-2 size-1 shrink-0 bg-ink" aria-hidden />{t}</li>
                  ))}
                </ul>
              </div>
              <div className="border-t border-line pt-5">
                <p className="eyebrow mb-2">Privacy</p>
                <p className="text-sm leading-relaxed text-muted">
                  No account. Links are never opened. Only a short, number-masked preview is kept so you can find the
                  result in your history on this device.
                </p>
              </div>
            </aside>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------- how it works */}
      <section id="how-it-works" className="scroll-mt-16 border-b border-line bg-surface">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
          <div className="grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:items-end">
            <div>
              <p className="eyebrow mb-3">How SENTINEL works</p>
              <h2 className="text-3xl font-semibold tracking-[-0.025em] sm:text-4xl">
                Real analysis, not a black box.
              </h2>
            </div>
            <p className="text-[0.95rem] leading-relaxed text-muted">
              Every result is built from evidence you can inspect. Verdicts come from trained models and deterministic
              checks. The language layer only explains that evidence; it never decides whether something is a scam.
            </p>
          </div>

          <ol className="mt-12 grid gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-2 lg:grid-cols-5">
            {PIPELINE.map((step) => (
              <li key={step.n} className="flex flex-col bg-surface p-5">
                <div className="flex items-center justify-between">
                  <step.icon className="size-5 text-ink" aria-hidden />
                  <span className="font-mono text-xs text-faint">{step.n}</span>
                </div>
                <h3 className="mt-6 font-semibold text-ink">{step.title}</h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-muted">{step.body}</p>
                <div className="mt-4 flex flex-wrap gap-1">
                  {step.tools.map((t) => (
                    <code key={t} className="rounded-xs bg-paper-2 px-1.5 py-0.5 font-mono text-[0.68rem] text-ink-2">{t}</code>
                  ))}
                </div>
              </li>
            ))}
          </ol>

          <div className="mt-6 flex flex-col gap-3 rounded-md border border-line bg-console p-5 text-console-text sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <BrainCircuit className="mt-0.5 size-5 shrink-0 text-signal" aria-hidden />
              <p className="text-sm leading-relaxed">
                <span className="font-medium text-white">Example path for a QR code:</span>{" "}
                <span className="font-mono text-[0.8rem] text-console-muted">
                  qr_decoder → upi_analyzer <span className="text-console-line">|</span> url_analyzer → risk_engine → explanation_service
                </span>
              </p>
            </div>
            <Link href="/analyze" className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-signal hover:underline">
              Watch it run <ArrowUpRight className="size-4" aria-hidden />
            </Link>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------ what it catches */}
      <section className="border-b border-line">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:px-6 sm:py-20 lg:grid-cols-[1fr_1.35fr]">
          <div>
            <p className="eyebrow mb-3">What it looks for</p>
            <h2 className="text-3xl font-semibold tracking-[-0.025em]">Built for the scams people actually receive.</h2>
            <p className="mt-4 text-[0.95rem] leading-relaxed text-muted">
              Trained on thousands of real labelled SMS and phishing URLs, and tuned for the patterns common in India —
              UPI, KYC, task jobs and fake officials.
            </p>
          </div>
          <dl className="grid gap-x-10 sm:grid-cols-2">
            {CATCHES.map((c) => (
              <div key={c.title} className="border-t border-line py-5">
                <dt className="font-medium text-ink">{c.title}</dt>
                <dd className="mt-1.5 text-sm leading-relaxed text-muted">{c.body}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ------------------------------------------------------------- scale */}
      <section className="border-b border-line bg-surface">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <p className="eyebrow mb-3">Reading a result</p>
          <h2 className="max-w-xl text-2xl font-semibold tracking-[-0.02em]">Every score comes with words, not just a colour.</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {BANDS.map((b) => (
              <div key={b.label} className="border-t-4 pt-4" style={{ borderColor: `var(--${b.cls.replace("bg-", "")})` }}>
                <p className="flex items-baseline justify-between">
                  <span className="font-semibold uppercase tracking-wide text-ink">{b.label}</span>
                  <span className="font-mono text-xs text-muted">{b.range}</span>
                </p>
                <p className="mt-2 text-sm leading-relaxed text-muted">{b.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------- honesty */}
      <section className="border-b border-line">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-16 sm:px-6 md:grid-cols-2">
          <div className="rounded-md border border-line bg-surface p-6">
            <p className="eyebrow mb-4">Available now</p>
            <ul className="space-y-3 text-sm">
              {[
                [MessageSquareText, "Messages — SMS, WhatsApp, email, job offers"],
                [ArrowUpRight, "Links — analysed without ever being opened"],
                [ScanText, "Screenshots — OCR, then text, link and QR analysis"],
                [CircleDashed, "QR codes — websites and UPI payment requests"],
              ].map(([Icon, t]) => {
                const I = Icon as typeof MessageSquareText;
                return <li key={t as string} className="flex gap-3 text-ink-2"><I className="mt-0.5 size-4 text-safe" aria-hidden />{t as string}</li>;
              })}
            </ul>
          </div>
          <div className="rounded-md border border-dashed border-line-strong p-6">
            <p className="eyebrow mb-4">Not available yet — and we&apos;ll say so</p>
            <ul className="space-y-3 text-sm text-muted">
              <li className="flex gap-3"><Ban className="mt-0.5 size-4" aria-hidden />Voice recordings and call transcription</li>
              <li className="flex gap-3"><Ban className="mt-0.5 size-4" aria-hidden />Deepfake / cloned-voice detection</li>
              <li className="flex gap-3"><Ban className="mt-0.5 size-4" aria-hidden />Live URL reputation (only when an API key is configured)</li>
            </ul>
            <p className="mt-4 text-sm leading-relaxed text-muted">SENTINEL never shows a result it didn&apos;t genuinely compute.</p>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------- community */}
      <section>
        <div className="mx-auto grid max-w-6xl gap-px px-4 py-16 sm:px-6 md:grid-cols-2">
          <Link href="/map" className="group flex flex-col justify-between gap-10 rounded-md border border-line bg-surface p-6 transition-colors hover:border-ink md:rounded-r-none">
            <Map className="size-6 text-ink" aria-hidden />
            <div>
              <h3 className="text-xl font-semibold tracking-[-0.01em]">Community scam map</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">See which scams are being reported where — aggregated by city, never by person.</p>
              <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium">Explore the map <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden /></span>
            </div>
          </Link>
          <Link href="/safety" className="group flex flex-col justify-between gap-10 rounded-md border border-line bg-surface p-6 transition-colors hover:border-ink md:rounded-l-none md:border-l-0">
            <BookOpenCheck className="size-6 text-ink" aria-hidden />
            <div>
              <h3 className="text-xl font-semibold tracking-[-0.01em]">Safety Center</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">Two-minute guides: UPI safety, job scams, QR codes, fake websites, digital arrest and more.</p>
              <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium">Read the guides <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden /></span>
            </div>
          </Link>
        </div>
      </section>
    </>
  );
}
