# Architecture Decision Records

Short records of the decisions that shape SENTINEL, why they were made and what
they cost.

---

## ADR-001 — No login for the core scanner
**Decision.** Anyone can analyse content without an account. History is grouped
by a random device id kept in `localStorage`.
**Why.** The moment someone receives a suspicious message is exactly when a sign-up
wall makes them give up. The product's value is immediate.
**Consequences.** History is per-browser. `analyses.user_id` is reserved so
accounts can be added later with a migration and an auth dependency.

## ADR-002 — The agent orchestrates; models and rules decide
**Decision.** `SentinelAgent` is a deterministic router with a fixed routing table.
Verdicts come from supervised models and rules; an LLM may only rephrase the
explanation.
**Why.** Security verdicts must be reproducible, auditable and not hallucinated.
A fixed plan also makes every step explainable in the trace.
**Consequences.** Adding an input type means adding tools and a routing entry.
An LLM planner could replace the table without touching the tools.

## ADR-003 — Logistic Regression over TF-IDF as the text baseline
**Decision.** Word + character TF-IDF with Logistic Regression.
**Why.** Calibrated probabilities feed the risk formula; coefficients give
per-term explanations; it trains in under a minute, runs in ~2 ms on CPU, and
reaches F1 0.95 / ROC-AUC 0.99 on the hold-out.
**Consequences.** Limited semantic understanding and weaker on non-English text.
`TextScamDetector` is a protocol, so a fine-tuned transformer can replace it.

## ADR-004 — URL model sees only the registered domain
**Decision.** Train on the registered domain; handle scheme, path, query and
sub-domain with rules; add Tranco popular domains to the legitimate class.
**Why.** In PhiUSIIL every legitimate URL is a bare `https://www.` homepage, so a
full-URL model learns shortcuts ("has a path ⇒ phishing") that would flag nearly
every real link people receive. Its legitimate domains are also obscure, which
made `google.com` look like phishing (0.82) until Tranco was added (→ 0.06).
**Consequences.** Honest domain-level ROC-AUC is 0.81. The model's weight in the
risk formula is capped (55/100) so it needs corroborating rules to reach HIGH.

## ADR-005 — Links are never fetched by the backend
**Decision.** URL analysis is purely lexical plus an optional reputation API.
Shortened links are flagged as "destination hidden" rather than expanded.
**Why.** Fetching attacker-controlled URLs exposes the server (SSRF, malware,
tracking pixels that confirm a victim clicked) and tips off scammers.
**Consequences.** Can't see page content or redirects. Safe redirect expansion
via a sandboxed service is future work.

## ADR-006 — Transparent additive risk formula instead of a learned meta-model
**Decision.** Hand-specified component formula + `max` aggregation + corroboration
bonus + documented floors.
**Why.** Users and examiners can recompute every score from the breakdown; there is
no labelled dataset of *combined* multi-signal inputs to train a meta-model on.
**Consequences.** Weights are expert-set, validated with
`scripts/evaluate_pipeline.py`. A calibrated stacking model is a possible upgrade
once enough labelled reports exist.

## ADR-007 — OCR with RapidOCR (ONNX) instead of Tesseract
**Decision.** RapidOCR via pip, wrapped behind an `OCREngine` protocol.
**Why.** No system binary to install (Windows/Docker friendly), strong accuracy on
phone screenshots. It sometimes drops spaces, so OCR output is repaired
(acronym/case/dictionary word splitting, URL line re-joining).
**Consequences.** ~100 MB of dependencies; first call loads models (~2 s).

## ADR-008 — Offline-first RAG with LSA embeddings + FAISS
**Decision.** Embed the 51 knowledge chunks with TF-IDF→SVD (LSA), index with FAISS,
re-rank by evidence tags. Template explanations by default; Claude optional.
**Why.** Runs with zero downloads or API keys, deterministic for demos, and the
corpus is small and domain-specific (LSA works well there). Retrieval is
grounded in *found evidence*, so guidance matches what was detected.
**Consequences.** Less semantic recall than neural embeddings; `Embedder` protocol
allows swapping in a sentence-transformer.

## ADR-009 — Minimal retention of user content
**Decision.** Never store raw message text or uploaded images from scans. Keep a
160-char preview with long digit runs masked, plus the structured result.
Report evidence is re-encoded to strip EXIF/GPS and never served publicly.
**Why.** Scam messages contain phone numbers, account numbers and names — of
victims as well as scammers.
**Consequences.** Past analyses can't be re-run with newer models.

## ADR-010 — Demo data is flagged in the schema, not just in the UI
**Decision.** Seeded map reports carry `is_demo=true`; every API aggregate reports
`demo_reports` separately and the UI labels them and lets users hide them.
**Why.** An empty map demos badly, but fake data must never be mistaken for real
community intelligence.

## ADR-011 — One analyze endpoint per input type, with `?stream=true`
**Decision.** Keep `POST /api/analyze/{text|url|image|qr|audio}` as specified and add
NDJSON streaming via a query flag rather than WebSockets or SSE routes.
**Why.** Per-type endpoints get precise validation and OpenAPI docs; NDJSON over a
normal POST supports file uploads (EventSource can't POST) and needs no extra
infrastructure.

## ADR-012 — SQLite by default, PostgreSQL in docker-compose
**Decision.** Same SQLAlchemy models and Alembic migrations for both;
`DATABASE_URL` selects the engine.
**Why.** The project must run on a laptop with no services installed, while the
deployment target is PostgreSQL.
