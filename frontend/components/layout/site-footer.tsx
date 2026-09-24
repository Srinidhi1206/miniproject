import Link from "next/link";

import { Logo } from "@/components/brand/logo";

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-paper">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <Logo />
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted">
            SENTINEL gives an automated risk assessment to help you pause and verify. It can be wrong — when money or
            accounts are involved, always confirm through official channels.
          </p>
        </div>
        <div>
          <p className="eyebrow mb-3">If you&apos;ve been scammed (India)</p>
          <ul className="space-y-2 text-sm text-ink-2">
            <li>
              Call <a href="tel:1930" className="font-semibold text-ink underline underline-offset-4">1930</a> — national cybercrime helpline
            </li>
            <li>
              Report at{" "}
              <a href="https://cybercrime.gov.in" target="_blank" rel="noopener noreferrer" className="font-semibold text-ink underline underline-offset-4">
                cybercrime.gov.in
              </a>
            </li>
            <li>Contact your bank to block cards and UPI</li>
          </ul>
        </div>
        <div>
          <p className="eyebrow mb-3">SENTINEL</p>
          <ul className="space-y-2 text-sm text-ink-2">
            <li><Link href="/analyze" className="hover:text-ink">Analyse</Link></li>
            <li><Link href="/safety" className="hover:text-ink">Safety Center</Link></li>
            <li><Link href="/map" className="hover:text-ink">Scam map</Link></li>
            <li><Link href="/settings" className="hover:text-ink">Privacy &amp; system status</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-line">
        <p className="mx-auto max-w-6xl px-4 py-4 font-mono text-[0.7rem] uppercase tracking-wider text-faint sm:px-6">
          Final-year project prototype · no account required · not affiliated with any bank or government body
        </p>
      </div>
    </footer>
  );
}
