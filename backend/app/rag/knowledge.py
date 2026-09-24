"""Knowledge-base loader. Markdown files with a small front-matter header.

Each `## Section` becomes one retrievable chunk. Document-level `tags` list the
evidence codes the guide is about, so retrieval can boost guidance that
matches what the analyzers actually found.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

_FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    slug: str
    title: str
    section: str
    text: str
    tags: tuple[str, ...]

    @property
    def lead(self) -> str:
        """First paragraph — the self-contained explanation used in results."""
        return self.text.split("\n\n")[0].strip()


@dataclass
class KnowledgeDoc:
    slug: str
    title: str
    category: str
    summary: str
    tags: list[str]
    order: int
    read_minutes: int
    body: str
    chunks: list[KnowledgeChunk] = field(default_factory=list)


def _parse_front(raw: str) -> tuple[dict, str]:
    m = _FRONT.match(raw)
    if not m:
        raise ValueError("missing front matter")
    meta: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key.strip()] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key.strip()] = value
    return meta, raw[m.end():].strip()


def parse_doc(raw: str) -> KnowledgeDoc:
    meta, body = _parse_front(raw)
    doc = KnowledgeDoc(
        slug=meta["slug"], title=meta["title"], category=meta.get("category", "General"),
        summary=meta.get("summary", ""), tags=meta.get("tags", []), order=int(meta.get("order", 99)),
        read_minutes=int(meta.get("read_minutes", 2)), body=body,
    )
    for i, section in enumerate(re.split(r"^## ", body, flags=re.M)):
        section = section.strip()
        if not section:
            continue
        heading, _, text = section.partition("\n")
        doc.chunks.append(KnowledgeChunk(
            id=f"{doc.slug}#{i}", slug=doc.slug, title=doc.title, section=heading.strip(),
            text=text.strip(), tags=tuple(doc.tags),
        ))
    return doc


@lru_cache
def load_knowledge(directory: Path | None = None) -> tuple[KnowledgeDoc, ...]:
    directory = directory or get_settings().knowledge_dir
    docs = [parse_doc(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.md"))]
    return tuple(sorted(docs, key=lambda d: d.order))
