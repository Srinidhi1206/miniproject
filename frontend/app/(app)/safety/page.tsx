import { ArrowUpRight, Phone } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { SectionHeading } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/empty-state";
import { serverApi } from "@/lib/server-api";
import type { GuideSummary } from "@/types/api";

export const metadata: Metadata = { title: "Safety Center" };
export const dynamic = "force-dynamic";

const CATEGORY_ORDER = ["UPI safety", "Phishing", "Job scams", "QR scams", "Fake websites", "Social engineering", "Deepfake scams", "Account security"];

export default async function SafetyPage() {
  const guides = await serverApi.guides();
  const groups = new Map<string, GuideSummary[]>();
  (guides ?? []).forEach((g) => groups.set(g.category, [...(groups.get(g.category) ?? []), g]));
  const categories = [...groups.keys()].sort((a, b) => CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b));

  return (
    <div className="space-y-10">
      <SectionHeading
        as="h1"
        eyebrow="Safety Center"
        title="Know the tricks before they reach you"
        description="Short, practical guides. Each takes about two minutes. The same guidance powers SENTINEL's explanations."
      />

      <div className="flex flex-col gap-4 rounded-md bg-console p-5 text-console-text sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-medium text-white">Already lost money or shared an OTP?</p>
          <p className="mt-1 text-sm text-console-muted">Every hour matters. Call the national cybercrime helpline, then your bank.</p>
        </div>
        <div className="flex gap-2">
          <a href="tel:1930" className="inline-flex h-10 items-center gap-2 rounded-sm bg-signal px-4 text-sm font-semibold text-ink"><Phone className="size-4" aria-hidden />Call 1930</a>
          <Link href="/safety/if-scammed" className="inline-flex h-10 items-center rounded-sm border border-console-line px-4 text-sm text-white hover:border-console-muted">What to do</Link>
        </div>
      </div>

      {!guides && <ErrorState message="The Safety Center couldn't be loaded right now. Please try again shortly." />}

      {categories.length > 1 && (
        <nav aria-label="Guide categories" className="flex flex-wrap gap-2">
          {categories.map((c) => (
            <a key={c} href={`#${c.toLowerCase().replace(/\s+/g, "-")}`} className="rounded-full border border-line-strong bg-surface px-3 py-1 text-sm text-ink-2 hover:border-ink">{c}</a>
          ))}
        </nav>
      )}

      <div className="space-y-10">
        {categories.map((cat) => (
          <section key={cat} id={cat.toLowerCase().replace(/\s+/g, "-")} className="scroll-mt-20">
            <h2 className="eyebrow mb-3">{cat}</h2>
            <ul className="grid gap-px overflow-hidden rounded-md border border-line bg-line md:grid-cols-2">
              {groups.get(cat)!.map((g) => (
                <li key={g.slug} className="bg-surface">
                  <Link href={`/safety/${g.slug}`} className="group flex h-full flex-col p-5 hover:bg-surface-2">
                    <span className="flex items-start justify-between gap-3">
                      <span className="text-[1.05rem] font-semibold tracking-[-0.01em] text-ink">{g.title}</span>
                      <ArrowUpRight className="size-4 shrink-0 text-faint transition-colors group-hover:text-ink" aria-hidden />
                    </span>
                    <span className="mt-2 flex-1 text-sm leading-relaxed text-muted">{g.summary}</span>
                    <span className="mt-4 font-mono text-[0.68rem] uppercase tracking-wider text-faint">{g.read_minutes} min read</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
