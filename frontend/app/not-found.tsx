import Link from "next/link";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main id="main" className="grid min-h-dvh place-items-center px-4">
      <div className="max-w-md text-center">
        <Logo className="justify-center" />
        <p className="eyebrow mt-10">Error 404</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.02em]">This page doesn&apos;t exist</h1>
        <p className="mt-3 text-muted">
          If someone sent you a link claiming to be SENTINEL, be careful — check the address carefully.
        </p>
        <div className="mt-8 flex justify-center gap-2">
          <Button asChild><Link href="/">Go home</Link></Button>
          <Button asChild variant="secondary"><Link href="/analyze">Analyze something</Link></Button>
        </div>
      </div>
    </main>
  );
}
