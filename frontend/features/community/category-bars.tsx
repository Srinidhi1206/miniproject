import { SCAM_TYPE_LABEL } from "@/features/community/scam-types";
import type { ScamType } from "@/types/api";

/**
 * Single-series magnitude: one neutral hue, sorted, value labels in text ink.
 * Deliberately not colour-coded so category bars can't be confused with risk levels.
 */
export function CategoryBars({ totals, onSelect, selected }: {
  totals: Partial<Record<ScamType, number>>;
  onSelect?: (t: ScamType) => void;
  selected?: ScamType | "";
}) {
  const rows = (Object.entries(totals) as [ScamType, number][]).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...rows.map(([, n]) => n));
  const total = rows.reduce((s, [, n]) => s + n, 0);
  if (!rows.length) return <p className="text-sm text-muted">No reports in this period.</p>;
  return (
    <ul className="space-y-2.5" aria-label="Reports by scam type">
      {rows.map(([type, n]) => {
        const pct = Math.round((n / total) * 100);
        const content = (
          <>
            <span className="flex items-baseline justify-between gap-3 text-sm">
              <span className="text-ink-2">{SCAM_TYPE_LABEL[type] ?? type}</span>
              <span className="font-mono text-xs tabular-nums text-ink">{n} <span className="text-faint">· {pct}%</span></span>
            </span>
            <span className="mt-1 block h-2 w-full rounded-xs bg-paper-2">
              <span
                className="block h-full rounded-r-[4px] bg-ink transition-[width] duration-500"
                style={{ width: `${(n / max) * 100}%`, opacity: selected && selected !== type ? 0.25 : 1 }}
              />
            </span>
          </>
        );
        return (
          <li key={type} title={`${SCAM_TYPE_LABEL[type]}: ${n} reports (${pct}%)`}>
            {onSelect ? (
              <button type="button" onClick={() => onSelect(type)} className="block w-full rounded-xs text-left hover:bg-surface-2"
                aria-pressed={selected === type}>
                {content}
              </button>
            ) : content}
          </li>
        );
      })}
    </ul>
  );
}
