"use client";

import * as Dialog from "@radix-ui/react-dialog";
import {
  BookOpenCheck, Flag, History, LayoutDashboard, Map, Menu, ScanSearch, Settings, X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard },
  { href: "/analyze", label: "Analyze", icon: ScanSearch },
  { href: "/history", label: "History", icon: History },
  { href: "/map", label: "Scam Map", icon: Map },
  { href: "/report", label: "Report Scam", icon: Flag },
  { href: "/safety", label: "Safety Center", icon: BookOpenCheck },
  { href: "/settings", label: "Settings", icon: Settings },
];

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const path = usePathname();
  return (
    <ul className="space-y-0.5">
      {NAV.map((item) => {
        const active = path === item.href || (item.href !== "/dashboard" && path.startsWith(item.href))
          || (item.href === "/analyze" && path.startsWith("/analysis"));
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors",
                active ? "bg-ink font-medium text-white" : "text-ink-2 hover:bg-paper-2 hover:text-ink",
              )}
            >
              <item.icon className={cn("size-4", active ? "text-signal" : "text-muted")} aria-hidden />
              {item.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function SidebarFoot() {
  return (
    <div className="rounded-sm border border-line bg-surface p-3 text-xs leading-relaxed text-muted">
      <p className="font-medium text-ink">Lost money to a scam?</p>
      <p className="mt-1">
        Call <a href="tel:1930" className="font-semibold text-ink underline underline-offset-2">1930</a> or report at{" "}
        <a href="https://cybercrime.gov.in" target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">cybercrime.gov.in</a>.
      </p>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[15rem_1fr]">
      <aside className="sticky top-0 hidden h-dvh flex-col justify-between border-r border-line bg-paper px-3 py-5 lg:flex">
        <div>
          <div className="px-2"><Logo /></div>
          <nav aria-label="App" className="mt-8"><NavList /></nav>
        </div>
        <SidebarFoot />
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-paper/90 px-4 backdrop-blur lg:hidden">
          <Logo />
          <Dialog.Root open={open} onOpenChange={setOpen}>
            <Dialog.Trigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open navigation"><Menu /></Button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="fixed inset-0 z-50 bg-ink/30 animate-fade" />
              <Dialog.Content className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col justify-between border-r border-line bg-paper p-4 animate-rise">
                <div>
                  <div className="flex items-center justify-between">
                    <Dialog.Title className="sr-only">Navigation</Dialog.Title>
                    <Logo />
                    <Dialog.Close asChild>
                      <Button variant="ghost" size="icon" aria-label="Close navigation"><X /></Button>
                    </Dialog.Close>
                  </div>
                  <nav aria-label="App" className="mt-6"><NavList onNavigate={() => setOpen(false)} /></nav>
                </div>
                <SidebarFoot />
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </header>
        <main id="main" className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10 lg:py-10">
          {children}
        </main>
      </div>
    </div>
  );
}
