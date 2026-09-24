"use client";

import {
  ArrowRight, Flag, History as HistoryIcon, Link2, MessageSquareText, QrCode, ScanSearch, ScanText,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { RiskBadge } from "@/components/risk/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, DemoTag, SectionHeading } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { CategoryBars } from "@/features/community/category-bars";
import { api } from "@/lib/api";
import { INPUT_LABEL } from "@/lib/risk";
import { timeAgo } from "@/lib/utils";
import type { ClientStats, HistoryItem, ScamMapData } from "@/types/api";

const QUICK = [
  { href: "/analyze?mode=message", label: "Analyze message", icon: MessageSquareText },
  { href: "/analyze?mode=url", label: "Check a link", icon: Link2 },
  { href: "/analyze?mode=qr", label: "Scan QR code", icon: QrCode },
  { href: "/analyze?mode=image", label: "Upload screenshot", icon: ScanText },
  { href: "/report", label: "Report a scam", icon: Flag },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<ClientStats | null>(null);
  const [recent, setRecent] = useState<HistoryItem[] | null>(null);
  const [community, setCommunity] = useState<ScamMapData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    Promise.all([api.stats(), api.history({ limit: 6 }), api.scamMap({ days: 30 })])
      .then(([s, h, m]) => { setStats(s); setRecent(h.items); setCommunity(m); })
      .catch((e: Error) => setError(e.message));
  };
  useEffect(load, []);

  return (
    <div className="space-y-8">
      <SectionHeading
        as="h1"
        eyebrow="Home"
        title="Overview"
        description="Your numbers come from scans made on this device only. There's no account, so clearing browser data starts fresh."
        action={<Button asChild><Link href="/analyze"><ScanSearch aria-hidden />New analysis</Link></Button>}
      />

      {error && <ErrorState message={error} onRetry={load} />}

      <section aria-label="Your statistics" className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line lg:grid-cols-4">
        <Stat label="Scans on this device" value={stats?.total_scans} sub={stats ? `${stats.scans_today} today` : undefined} />
        <Stat label="Flagged as scams" value={stats?.threats_detected} sub="High or critical risk" tone="text-critical" />
        <Stat label="Suspicious" value={stats?.suspicious} sub="Medium risk — verify first" tone="text-warn" />
        <Stat label="Likely safe" value={stats?.safe} sub={stats?.last_scan_at ? `Last scan ${timeAgo(stats.last_scan_at)}` : "No scans yet"} tone="text-safe" />
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-ink">Recent analyses</h2>
            <Link href="/history" className="text-sm text-muted hover:text-ink">View all</Link>
          </div>
          {recent === null && !error ? (
            <div className="mt-4 space-y-2">{[0, 1, 2].map((i) => <div key={i} className="h-14 animate-pulse rounded-sm bg-paper-2" />)}</div>
          ) : recent && recent.length === 0 ? (
            <EmptyState
              className="mt-4"
              icon={HistoryIcon}
              title="Nothing checked yet."
              body="Analyze a message, link, screenshot or QR code and your recent checks will appear here."
              action={
                <div className="flex gap-2">
                  <Button asChild><Link href="/analyze">Analyze something</Link></Button>
                  <Button asChild variant="secondary"><Link href="/#how-it-works">How SENTINEL works</Link></Button>
                </div>
              }
            />
          ) : (
            <ul className="mt-3 divide-y divide-line">
              {recent?.map((item) => (
                <li key={item.id}>
                  <Link href={`/analysis/${item.id}`} className="-mx-2 flex items-center gap-4 rounded-sm px-2 py-3 hover:bg-surface-2">
                    <span className="w-20 shrink-0 font-mono text-[0.7rem] uppercase tracking-wider text-muted">{INPUT_LABEL[item.input_type]}</span>
                    <span className="min-w-0 flex-1 truncate text-sm text-ink-2">{item.input_preview || "—"}</span>
                    <RiskBadge level={item.risk_level} score={item.risk_score} />
                    <span className="hidden w-20 shrink-0 text-right text-xs text-muted sm:block">{timeAgo(item.created_at)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-5">
          <h2 className="font-semibold text-ink">Quick actions</h2>
          <ul className="mt-3 space-y-1">
            {QUICK.map((q) => (
              <li key={q.href}>
                <Link href={q.href} className="group flex items-center gap-3 rounded-sm px-2 py-2.5 text-sm text-ink-2 hover:bg-surface-2 hover:text-ink">
                  <q.icon className="size-4 text-muted" aria-hidden />
                  <span className="flex-1">{q.label}</span>
                  <ArrowRight className="size-3.5 opacity-0 transition-opacity group-hover:opacity-100" aria-hidden />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 font-semibold text-ink">
              Community reports · last 30 days
              {community && community.demo_reports > 0 && <DemoTag />}
            </h2>
            <p className="mt-1 text-sm text-muted">
              {community
                ? community.demo_reports > 0
                  ? `${community.total_reports} reports, of which ${community.demo_reports} are fictional demo data and ${community.community_reports} were submitted by users.`
                  : `${community.total_reports} reports submitted by users.`
                : "Loading…"}
            </p>
          </div>
          <Link href="/map" className="text-sm text-muted hover:text-ink">Open scam map</Link>
        </div>
        <div className="mt-5 max-w-2xl">
          {community && <CategoryBars totals={community.totals_by_type} />}
        </div>
      </Card>
    </div>
  );
}

function Stat({ label, value, sub, tone = "text-ink" }: { label: string; value?: number; sub?: string; tone?: string }) {
  return (
    <div className="bg-surface p-4 sm:p-5">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-2 font-mono text-3xl font-semibold tabular-nums ${value === undefined ? "text-faint" : tone}`}>
        {value ?? "—"}
      </p>
      {sub && <p className="mt-1 text-xs text-muted">{sub}</p>}
    </div>
  );
}
