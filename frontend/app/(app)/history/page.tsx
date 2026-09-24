"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { ChevronLeft, ChevronRight, History as HistoryIcon, Search, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RiskBadge } from "@/components/risk/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, SectionHeading } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Input, Select } from "@/components/ui/form";
import { api } from "@/lib/api";
import { CLASSIFICATION_LABEL, INPUT_LABEL } from "@/lib/risk";
import { formatDateTime } from "@/lib/utils";
import type { HistoryPage } from "@/types/api";

const PAGE = 15;

export default function HistoryPageView() {
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [type, setType] = useState("");
  const [level, setLevel] = useState("");
  const [sort, setSort] = useState("newest");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<HistoryPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q.trim()), 250);
    return () => clearTimeout(t);
  }, [q]);
  useEffect(() => setOffset(0), [debouncedQ, type, level, sort]);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api.history({ q: debouncedQ, type, level, sort, limit: PAGE, offset })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [debouncedQ, type, level, sort, offset]);
  useEffect(load, [load]);

  const filtered = !!(debouncedQ || type || level);
  const total = data?.total ?? 0;

  return (
    <div className="space-y-6">
      <SectionHeading
        as="h1"
        eyebrow="History"
        title="Your analyses"
        description="Stored against an anonymous ID for this browser. Only masked previews are kept."
        action={total > 0 || filtered ? <ClearHistory onCleared={load} /> : undefined}
      />

      <div className="grid gap-3 sm:grid-cols-[1fr_repeat(3,minmax(0,10rem))]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-faint" aria-hidden />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search previews" aria-label="Search history" className="pl-9" />
        </div>
        <Select value={type} onChange={(e) => setType(e.target.value)} aria-label="Filter by type">
          <option value="">All types</option>
          {(["TEXT", "URL", "IMAGE", "QR"] as const).map((t) => <option key={t} value={t}>{INPUT_LABEL[t]}</option>)}
        </Select>
        <Select value={level} onChange={(e) => setLevel(e.target.value)} aria-label="Filter by risk">
          <option value="">All risk levels</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </Select>
        <Select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort">
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="risk_desc">Highest risk</option>
          <option value="risk_asc">Lowest risk</option>
        </Select>
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      {data && data.items.length === 0 && !loading ? (
        filtered ? (
          <EmptyState icon={Search} title="No matching analyses" body="Try a different search term or clear the filters."
            action={<Button variant="secondary" onClick={() => { setQ(""); setType(""); setLevel(""); }}>Clear filters</Button>} />
        ) : (
          <EmptyState icon={HistoryIcon} title="No analyses yet"
            body="Submit your first suspicious message, URL, QR code, or screenshot to begin."
            action={<Button asChild><Link href="/analyze">Analyze something</Link></Button>} />
        )
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] text-left text-sm">
              <caption className="sr-only">Analysis history</caption>
              <thead className="border-b border-line bg-surface-2 font-mono text-[0.68rem] uppercase tracking-wider text-muted">
                <tr>
                  <th scope="col" className="px-4 py-3 font-normal">Date</th>
                  <th scope="col" className="px-4 py-3 font-normal">Type</th>
                  <th scope="col" className="px-4 py-3 font-normal">Content</th>
                  <th scope="col" className="px-4 py-3 font-normal">Risk</th>
                  <th scope="col" className="px-4 py-3 font-normal">Result</th>
                  <th scope="col" className="px-4 py-3 font-normal"><span className="sr-only">View</span></th>
                </tr>
              </thead>
              <tbody className={loading ? "opacity-60" : undefined}>
                {(data?.items ?? []).map((item) => (
                  <tr key={item.id} className="border-b border-line last:border-0 hover:bg-surface-2">
                    <td className="whitespace-nowrap px-4 py-3 text-muted">{formatDateTime(item.created_at)}</td>
                    <td className="px-4 py-3 font-mono text-xs uppercase tracking-wider text-ink-2">{INPUT_LABEL[item.input_type]}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-ink-2" title={item.input_preview}>{item.input_preview || "—"}</td>
                    <td className="px-4 py-3"><RiskBadge level={item.risk_level} score={item.risk_score} /></td>
                    <td className="whitespace-nowrap px-4 py-3 text-ink">{CLASSIFICATION_LABEL[item.classification]}</td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/analysis/${item.id}`} className="font-medium text-ink underline decoration-line-strong underline-offset-4 hover:decoration-ink">
                        View<span className="sr-only"> analysis from {formatDateTime(item.created_at)}</span>
                      </Link>
                    </td>
                  </tr>
                ))}
                {!data && loading && [0, 1, 2, 3].map((i) => (
                  <tr key={i} className="border-b border-line"><td colSpan={6} className="px-4 py-3"><div className="h-5 animate-pulse rounded-xs bg-paper-2" /></td></tr>
                ))}
              </tbody>
            </table>
          </div>
          {total > PAGE && (
            <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-muted">
              <span>{offset + 1}–{Math.min(offset + PAGE, total)} of {total}</span>
              <div className="flex gap-1">
                <Button variant="ghost" size="icon" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))} aria-label="Previous page"><ChevronLeft /></Button>
                <Button variant="ghost" size="icon" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)} aria-label="Next page"><ChevronRight /></Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function ClearHistory({ onCleared }: { onCleared: () => void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button variant="secondary"><Trash2 aria-hidden />Clear history</Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-ink/30 animate-fade" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-md border border-line bg-surface p-6 shadow-xl animate-fade">
          <Dialog.Title className="text-lg font-semibold">Delete all analyses from this device?</Dialog.Title>
          <Dialog.Description className="mt-2 text-sm leading-relaxed text-muted">
            This permanently removes every analysis linked to this browser from SENTINEL. Community reports you submitted are not affected.
          </Dialog.Description>
          <div className="mt-6 flex justify-end gap-2">
            <Dialog.Close asChild><Button variant="ghost">Cancel</Button></Dialog.Close>
            <Button
              variant="danger"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try { await api.clearHistory(); setOpen(false); onCleared(); } finally { setBusy(false); }
              }}
            >
              {busy ? "Deleting…" : "Delete history"}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
