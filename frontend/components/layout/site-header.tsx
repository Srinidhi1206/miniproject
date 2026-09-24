"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";

const LINKS = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/map", label: "Scam map" },
  { href: "/safety", label: "Safety Center" },
  { href: "/report", label: "Report a scam" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-line/80 bg-paper/90 backdrop-blur supports-[backdrop-filter]:bg-paper/75">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-6 px-4 sm:px-6">
        <Logo />
        <nav aria-label="Main" className="hidden items-center gap-7 text-sm text-ink-2 md:flex">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="hover:text-ink">
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Button asChild variant="secondary" size="sm" className="hidden sm:inline-flex">
            <Link href="/dashboard">Dashboard</Link>
          </Button>
          <Button asChild size="sm" className="hidden sm:inline-flex">
            <Link href="/#scan">Analyze something</Link>
          </Button>
          <Dialog.Root open={open} onOpenChange={setOpen}>
            <Dialog.Trigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
                <Menu />
              </Button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="fixed inset-0 z-50 bg-ink/30 animate-fade" />
              <Dialog.Content className="fixed inset-x-0 top-0 z-50 border-b border-line bg-paper p-4 animate-rise">
                <div className="flex items-center justify-between">
                  <Dialog.Title className="sr-only">Menu</Dialog.Title>
                  <Logo />
                  <Dialog.Close asChild>
                    <Button variant="ghost" size="icon" aria-label="Close menu"><X /></Button>
                  </Dialog.Close>
                </div>
                <nav aria-label="Mobile" className="mt-4 grid gap-1">
                  {[...LINKS, { href: "/dashboard", label: "Dashboard" }, { href: "/history", label: "History" }].map((l) => (
                    <Link key={l.href} href={l.href} onClick={() => setOpen(false)}
                      className="rounded-sm px-3 py-3 text-[0.95rem] text-ink hover:bg-paper-2">
                      {l.label}
                    </Link>
                  ))}
                </nav>
                <Button asChild className="mt-3 w-full" size="lg" onClick={() => setOpen(false)}>
                  <Link href="/#scan">Analyze something suspicious</Link>
                </Button>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </div>
      </div>
    </header>
  );
}
