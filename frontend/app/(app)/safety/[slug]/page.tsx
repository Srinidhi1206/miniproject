import { ArrowLeft, ScanSearch } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { headingsOf, Markdown } from "@/components/markdown";
import { Button } from "@/components/ui/button";
import { serverApi } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const g = await serverApi.guide((await params).slug);
  return { title: g ? g.title : "Guide", description: g?.summary };
}

export default async function GuidePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [guide, all] = await Promise.all([serverApi.guide(slug), serverApi.guides()]);
  if (!guide) notFound();
  const toc = headingsOf(guide.body_markdown);
  const related = (all ?? []).filter((g) => g.slug !== slug && (g.category === guide.category || g.tags.some((t) => guide.tags.includes(t)))).slice(0, 4);

  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_16rem]">
      <article className="min-w-0 max-w-2xl">
        <Link href="/safety" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
          <ArrowLeft className="size-4" aria-hidden />Safety Center
        </Link>
        <p className="eyebrow mt-6">{guide.category} · {guide.read_minutes} min read</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.025em] text-ink sm:text-4xl">{guide.title}</h1>
        <p className="mt-4 border-l-4 border-signal pl-4 text-lg leading-relaxed text-ink">{guide.summary}</p>
        <div className="mt-8">
          <Markdown source={guide.body_markdown} />
        </div>
        <div className="mt-10 flex flex-col gap-3 rounded-md border border-line bg-surface p-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-ink-2">Received something like this?</p>
          <Button asChild><Link href="/analyze"><ScanSearch aria-hidden />Check it with SENTINEL</Link></Button>
        </div>
      </article>

      <aside className="space-y-8 lg:sticky lg:top-8 lg:self-start">
        {toc.length > 1 && (
          <nav aria-label="On this page">
            <p className="eyebrow mb-3">On this page</p>
            <ul className="space-y-2 border-l border-line text-sm">
              {toc.map((h) => (
                <li key={h.id}><a href={`#${h.id}`} className="-ml-px block border-l border-transparent pl-3 text-muted hover:border-ink hover:text-ink">{h.text}</a></li>
              ))}
            </ul>
          </nav>
        )}
        {related.length > 0 && (
          <div>
            <p className="eyebrow mb-3">Related guides</p>
            <ul className="space-y-3">
              {related.map((g) => (
                <li key={g.slug}><Link href={`/safety/${g.slug}`} className="text-sm font-medium text-ink underline decoration-line-strong underline-offset-4 hover:decoration-ink">{g.title}</Link></li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}
