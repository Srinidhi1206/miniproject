"use client";

import { Map as MapIcon, ShieldCheck } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, DemoTag, SectionHeading } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/form";
import { CategoryBars } from "@/features/community/category-bars";
import { SCAM_TYPE_LABEL, SCAM_TYPES } from "@/features/community/scam-types";
import { api } from "@/lib/api";
import type { ScamMapData, ScamType } from "@/types/api";

const ScamMapView = dynamic(() => import("@/features/community/scam-map-view"), {
  ssr: false,
  loading: () => <div className="h-[26rem] animate-pulse bg-paper-2 sm:h-[32rem]" />,
});

export default function MapPage() {
  const [type, setType] = useState<ScamType | "">("");
  const [region, setRegion] = useState("");
  const [days, setDays] = useState(90);
  const [includeDemo, setIncludeDemo] = useState(true);
  const [data, setData] = useState<ScamMapData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.scamMap({ type: type || undefined, region: region || undefined, days, include_demo: includeDemo })
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [type, region, days, includeDemo]);
  useEffect(load, [load]);

  return (
    <div className="space-y-6">
      <SectionHeading
        as="h1"
        eyebrow="Community intelligence"
        title="Scam map"
        description="Reports are grouped to the nearest city. No names, numbers, addresses or evidence are ever shown."
      />

      {/* Filters: one row above the chart */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-full sm:w-52">
          <label className="mb-1 block text-xs text-muted" htmlFor="f-type">Scam type</label>
          <Select id="f-type" value={type} onChange={(e) => setType(e.target.value as ScamType | "")}>
            <option value="">All types</option>
            {SCAM_TYPES.map((t) => <option key={t} value={t}>{SCAM_TYPE_LABEL[t]}</option>)}
          </Select>
        </div>
        <div className="w-[calc(50%-0.375rem)] sm:w-48">
          <label className="mb-1 block text-xs text-muted" htmlFor="f-region">Region</label>
          <Select id="f-region" value={region} onChange={(e) => setRegion(e.target.value)}>
            <option value="">All regions</option>
            {data?.regions.map((r) => <option key={r} value={r}>{r}</option>)}
          </Select>
        </div>
        <div className="w-[calc(50%-0.375rem)] sm:w-40">
          <label className="mb-1 block text-xs text-muted" htmlFor="f-days">Time period</label>
          <Select id="f-days" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last 12 months</option>
          </Select>
        </div>
        <label className="flex h-11 cursor-pointer items-center gap-2 text-sm text-ink-2">
          <input type="checkbox" checked={includeDemo} onChange={(e) => setIncludeDemo(e.target.checked)} className="size-4 accent-[var(--ink)]" />
          Include demo data
        </label>
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      {data && data.demo_reports > 0 && (
        <p className="flex flex-wrap items-center gap-2 rounded-sm border border-dashed border-warn-line bg-warn-bg/50 px-3 py-2 text-sm text-ink-2">
          <DemoTag />
          {data.demo_reports} of {data.total_reports} reports shown are fictional demonstration data so the map isn&apos;t empty
          in this prototype. Untick “Include demo data” to see only real submissions.
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_19rem]">
        <Card className="overflow-hidden">
          <ScamMapView locations={data?.locations ?? []} />
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2.5 text-xs text-muted">
            <span className="flex items-center gap-2">
              <span className="inline-block size-2 rounded-full bg-ink" aria-hidden /><span className="inline-block size-3.5 rounded-full bg-ink" aria-hidden />
              Circle area = number of reports
            </span>
            <span>Tap a circle for the breakdown</span>
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="p-5">
            <p className="text-xs text-muted">Reports in view</p>
            <p className="mt-1 font-mono text-3xl font-semibold tabular-nums">{data?.total_reports ?? "—"}</p>
            <p className="mt-1 text-xs text-muted">
              {data ? `${data.community_reports} from users · ${data.demo_reports} demo · ${data.locations.length} cities` : "Loading…"}
            </p>
            <div className="mt-5 border-t border-line pt-4">
              <p className="mb-3 text-sm font-medium text-ink">By scam type</p>
              {data && <CategoryBars totals={data.totals_by_type} selected={type} onSelect={(t) => setType(type === t ? "" : t)} />}
            </div>
          </Card>
          <Card className="p-5">
            <ShieldCheck className="size-5 text-ink" aria-hidden />
            <p className="mt-3 text-sm font-medium text-ink">Seen a scam?</p>
            <p className="mt-1 text-sm text-muted">Your report is added to this map anonymously and helps warn others nearby.</p>
            <Button asChild variant="secondary" className="mt-4 w-full"><Link href="/report">Report a scam</Link></Button>
          </Card>
        </div>
      </div>

      {/* Table view: the accessible, exact-number alternative to the map */}
      {data && (data.locations.length === 0 ? (
        <EmptyState icon={MapIcon} title="No scam reports in this area yet." body="That doesn't mean it's safe — stay cautious and verify suspicious requests. Try a longer time period or a different scam type to see broader trends." />
      ) : (
        <Card className="overflow-hidden">
          <details>
            <summary className="cursor-pointer px-5 py-4 text-sm font-medium text-ink hover:bg-surface-2">
              View as table ({data.locations.length} cities)
            </summary>
            <div className="overflow-x-auto border-t border-line">
              <table className="w-full min-w-[32rem] text-left text-sm">
                <thead className="bg-surface-2 font-mono text-[0.68rem] uppercase tracking-wider text-muted">
                  <tr>
                    <th scope="col" className="px-4 py-2 font-normal">City</th>
                    <th scope="col" className="px-4 py-2 font-normal">Region</th>
                    <th scope="col" className="px-4 py-2 text-right font-normal">Reports</th>
                    <th scope="col" className="px-4 py-2 font-normal">Most reported</th>
                  </tr>
                </thead>
                <tbody>
                  {data.locations.map((l) => {
                    const top = (Object.entries(l.by_type) as [ScamType, number][]).sort((a, b) => b[1] - a[1])[0];
                    return (
                      <tr key={l.slug} className="border-t border-line">
                        <td className="px-4 py-2 text-ink">{l.city}</td>
                        <td className="px-4 py-2 text-muted">{l.region}</td>
                        <td className="px-4 py-2 text-right font-mono tabular-nums">{l.total}</td>
                        <td className="px-4 py-2 text-ink-2">{top ? SCAM_TYPE_LABEL[top[0]] : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </details>
        </Card>
      ))}
    </div>
  );
}
