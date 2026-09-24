"""Embeddings + vector index for the knowledge base.

Embedder: LSA (TF-IDF -> truncated SVD -> L2-normalised dense vectors) fitted
on the knowledge chunks themselves. Fully offline, deterministic, no model
download. `Embedder` is a protocol, so a sentence-transformer can replace it
by implementing `fit`/`embed`.

Index: FAISS inner-product index (cosine similarity on normalised vectors),
with a NumPy fallback if FAISS isn't installed.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Protocol

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from app.rag.knowledge import KnowledgeChunk, load_knowledge

log = logging.getLogger("sentinel.rag")

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class Embedder(Protocol):
    name: str

    def fit(self, corpus: list[str]) -> None: ...
    def embed(self, texts: list[str]) -> np.ndarray: ...


class LSAEmbedder:
    name = "lsa-tfidf-svd"

    def __init__(self, dims: int = 96):
        self.dims = dims
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english", min_df=1)
        self.svd: TruncatedSVD | None = None

    def fit(self, corpus: list[str]) -> None:
        x = self.vectorizer.fit_transform(corpus)
        n = min(self.dims, x.shape[0] - 1, x.shape[1] - 1)
        self.svd = TruncatedSVD(n_components=max(2, n), random_state=0)
        self.svd.fit(x)

    def embed(self, texts: list[str]) -> np.ndarray:
        assert self.svd is not None, "call fit() first"
        v = self.svd.transform(self.vectorizer.transform(texts))
        return normalize(v).astype("float32")


class VectorIndex:
    def __init__(self, embedder: Embedder, chunks: list[KnowledgeChunk]):
        self.embedder = embedder
        self.chunks = chunks
        corpus = [f"{c.title}. {c.section}. {c.text}" for c in chunks]
        embedder.fit(corpus)
        self.vectors = embedder.embed(corpus)
        if faiss is not None:
            self.backend = "faiss"
            self._index = faiss.IndexFlatIP(self.vectors.shape[1])
            self._index.add(self.vectors)
        else:
            self.backend = "numpy"
            self._index = None

    def search(self, query: str, k: int) -> list[tuple[KnowledgeChunk, float]]:
        q = self.embedder.embed([query])
        k = min(k, len(self.chunks))
        if self._index is not None:
            scores, idx = self._index.search(q, k)
            pairs = zip(idx[0], scores[0])
        else:
            sims = self.vectors @ q[0]
            order = np.argsort(-sims)[:k]
            pairs = zip(order, sims[order])
        return [(self.chunks[i], float(s)) for i, s in pairs if i >= 0]


@lru_cache
def get_index() -> VectorIndex:
    chunks = [c for doc in load_knowledge() for c in doc.chunks]
    index = VectorIndex(LSAEmbedder(), chunks)
    log.info("RAG index ready: %d chunks, backend=%s, dims=%d", len(chunks), index.backend, index.vectors.shape[1])
    return index


def retrieve(query: str, evidence_codes: list[str], k: int = 4, tag_boost: float = 0.12,
             require_tag_match: bool = False) -> list[tuple[KnowledgeChunk, float]]:
    """Semantic search, re-ranked with a boost for chunks tagged with the found evidence codes.

    With `require_tag_match`, only chunks from guides tagged with a found evidence
    code are eligible (falls back to similarity when no guide matches).
    Sections that are lists of generic 'warning signs' / 'what to do' are
    down-weighted for explanations — the result page shows actions separately.
    """
    index = get_index()
    candidates = index.search(query, k=min(24, len(index.chunks)))
    codes = set(evidence_codes)
    rescored = []
    for chunk, score in candidates:
        s = score + tag_boost * len(codes.intersection(chunk.tags))
        if chunk.section.lower().startswith(("warning signs", "what to do")):
            s -= 0.25
        rescored.append((chunk, s))
    if require_tag_match and codes:
        # Ground guidance in the evidence: only guides written about a found tactic,
        # unless none match (then fall back to pure similarity).
        tagged = [p for p in rescored if codes.intersection(p[0].tags)]
        rescored = tagged or rescored
    rescored.sort(key=lambda p: -p[1])
    out: list[tuple[KnowledgeChunk, float]] = []
    per_doc: dict[str, int] = {}
    for chunk, s in rescored:  # at most two chunks per guide, for variety
        if per_doc.get(chunk.slug, 0) >= 2:
            continue
        out.append((chunk, round(s, 4)))
        per_doc[chunk.slug] = per_doc.get(chunk.slug, 0) + 1
        if len(out) >= k:
            break
    return out
