import Link from "next/link";

import { cn } from "@/lib/utils";

/** SENTINEL mark: a watchtower aperture — a square frame with a scanning slit. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={cn("size-7", className)}>
      <rect x="1" y="1" width="30" height="30" rx="6" fill="var(--console)" />
      <path d="M8 9.5h16M8 22.5h16" stroke="var(--console-line)" strokeWidth="2" strokeLinecap="round" />
      <rect x="7" y="14" width="18" height="4" rx="2" fill="var(--signal)" />
      <circle cx="16" cy="16" r="1.4" fill="var(--console)" />
    </svg>
  );
}

export function Logo({ className, href = "/" }: { className?: string; href?: string }) {
  return (
    <Link href={href} className={cn("inline-flex items-center gap-2.5", className)} aria-label="SENTINEL home">
      <LogoMark />
      <span className="font-mono text-[0.95rem] font-semibold tracking-[0.18em] text-ink">SENTINEL</span>
    </Link>
  );
}
