import { Fragment } from "react";

/**
 * Minimal Markdown renderer for the knowledge-base guides: `## headings`,
 * `- lists`, paragraphs and **bold**. Produces React elements only — no raw
 * HTML is ever injected, so content can't execute scripts.
 */
export function Markdown({ source }: { source: string }) {
  const blocks = source.trim().split(/\n{2,}/);
  return (
    <div className="space-y-4">
      {blocks.map((block, i) => {
        if (block.startsWith("## ")) {
          const [heading, ...rest] = block.split("\n");
          return (
            <Fragment key={i}>
              <h2 id={slugify(heading.slice(3))} className="scroll-mt-20 pt-4 text-xl font-semibold tracking-[-0.01em] text-ink first:pt-0">
                {heading.slice(3)}
              </h2>
              {rest.length > 0 && <Block text={rest.join("\n")} />}
            </Fragment>
          );
        }
        return <Block key={i} text={block} />;
      })}
    </div>
  );
}

function Block({ text }: { text: string }) {
  const lines = text.split("\n");
  if (lines.every((l) => l.startsWith("- "))) {
    return (
      <ul className="space-y-2">
        {lines.map((l, i) => (
          <li key={i} className="flex gap-3 leading-relaxed text-ink-2">
            <span className="mt-2.5 size-1.5 shrink-0 bg-ink" aria-hidden />
            <span>{inline(l.slice(2))}</span>
          </li>
        ))}
      </ul>
    );
  }
  return <p className="text-[1.02rem] leading-[1.75] text-ink-2">{inline(text.replace(/\n/g, " "))}</p>;
}

function inline(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") ? <strong key={i} className="font-semibold text-ink">{part.slice(2, -2)}</strong> : part,
  );
}

export function slugify(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export function headingsOf(source: string) {
  return source.split("\n").filter((l) => l.startsWith("## ")).map((l) => ({ text: l.slice(3), id: slugify(l.slice(3)) }));
}
