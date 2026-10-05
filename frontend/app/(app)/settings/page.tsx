"use client";

import { History, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, SectionHeading } from "@/components/ui/card";
import { getClientId, resetClientId } from "@/lib/client-id";

export default function SettingsPage() {
  const [deviceId, setDeviceId] = useState("");
  const [renewed, setRenewed] = useState(false);

  useEffect(() => { setDeviceId(getClientId()); }, []);

  return (
    <div className="space-y-8">
      <SectionHeading as="h1" eyebrow="Settings" title="Privacy & protection" />

      <Card className="p-5 sm:p-6">
        <h2 className="font-semibold text-ink">Your privacy</h2>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted">
          SENTINEL works without an account. A random ID created in this browser keeps your past checks together.
          It isn&apos;t linked to your name, phone number or email.
        </p>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-[10rem_1fr]">
          <dt className="text-muted">Anonymous device ID</dt>
          <dd className="break-all font-mono text-xs text-ink">{deviceId || "—"}</dd>
          <dt className="text-muted">What we keep</dt>
          <dd className="text-ink-2">The result of each check and a short preview, with long numbers such as phone or account numbers masked.</dd>
          <dt className="text-muted">What we don&apos;t keep</dt>
          <dd className="text-ink-2">The full text of your messages and the images you upload. Links you check are never opened.</dd>
        </dl>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => { setDeviceId(resetClientId()); setRenewed(true); }}>
            <RefreshCw aria-hidden />Start a new anonymous ID
          </Button>
          <Button asChild variant="ghost">
            <Link href="/history"><History aria-hidden />Manage or clear history</Link>
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted" role={renewed ? "status" : undefined}>
          {renewed
            ? "Done — you have a new anonymous ID. Your earlier checks are no longer shown on this device."
            : "A new ID hides your previous history on this device. To delete it permanently, clear your history first."}
        </p>
      </Card>
    </div>
  );
}
