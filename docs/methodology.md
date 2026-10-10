# SENTINEL — Methodology

This document describes **how** SENTINEL was designed, built, evaluated and
deployed. It is written for the project report; implementation details live in
[`architecture.md`](architecture.md), [`ml-pipeline.md`](ml-pipeline.md) and
[`decisions.md`](decisions.md) (ADR-001 … ADR-013). Every number quoted here is
produced by a script in this repository (see §7.5).

Figures (rendered from [`diagrams/architecture.html`](diagrams/architecture.html)):

| Figure | File |
|---|---|
| 1 · System & deployment architecture | [`images/architecture/01-system-architecture.png`](images/architecture/01-system-architecture.png) |
| 2 · Analysis pipeline (agentic orchestration) | [`images/architecture/02-analysis-pipeline.png`](images/architecture/02-analysis-pipeline.png) |
| 3 · Detection models & risk scoring | [`images/architecture/03-models-and-risk-engine.png`](images/architecture/03-models-and-risk-engine.png) |
| 4 · Data model | [`images/architecture/04-data-model.png`](images/architecture/04-data-model.png) |

---

## 1. Problem definition and objectives

Consumer fraud in India is dominated by **social engineering** delivered through
SMS/WhatsApp messages, look-alike links, "scan to receive money" UPI QR codes and
screenshots forwarded between people. Victims act within minutes and under
pressure; available protection is either invisible (bank-side), generic, or an
unexplained "spam" label.

Objectives:

1. **O1 — Multi-modal check**: accept a message, a link, a screenshot or a QR
   code, with no account or installation.
2. **O2 — Decision support, not just a label**: a 0–100 risk score, the exact
   warning signs quoted from the input, why they matter, and what to do next.
3. **O3 — Honest, explainable scoring**: every score must be reproducible from
   documented model outputs and rule weights; no feature may be faked.
4. **O4 — Privacy by design**: no login, raw content and images not stored,
   links never opened.
5. **O5 — Deployable**: a publicly reachable, tested production system.

## 2. Development approach

The project followed an **iterative, incremental** process (build → verify →
review → fix), with each step committed to git:

| Phase | Outcome |
|---|---|
| 1. Requirements & design | Feature scope, honest-feature policy ("unavailable" instead of fake), architecture decisions recorded as ADRs |
| 2. Data & models | Dataset collection, preprocessing, model training and offline evaluation (§4–5) |
| 3. Backend services | FastAPI API, analyzers, risk engine, RAG, agent, persistence |
| 4. Frontend | Scanner, live progress, result report, history, dashboard, map, safety center |
| 5. MVP verification | Unit, integration, end-to-end and labelled-sample review (§7) |
| 6. Post-MVP review | Prioritised P0/P1/P2 issues → fixes → re-test |
| 7. Production | Render (API + PostgreSQL) and Vercel (web); production verification, memory diagnosis and fix for OCR (§8) |

Design principles applied throughout:

* **The agent coordinates; it never classifies.** Verdicts come only from
  supervised models and deterministic rules (ADR-002).
* **Models estimate likelihood, rules name tactics.** Each contributes a bounded
  number of points so neither can dominate unchecked (§6).
* **Fail visibly.** If a tool fails, the result records the failure as a
  limitation rather than silently returning "safe".

## 3. System architecture (Figure 1, Figure 2)

* **Client** — Next.js 15 (TypeScript, Tailwind) on Vercel. An anonymous random
  device ID in `localStorage` (`X-Sentinel-Client` header) groups a person's
  history without an account.
* **API** — FastAPI on Render. Input validation (size limits, magic-byte checks,
  full image decode), rate limiting, CORS allow-list, request body cap.
* **SentinelAgent** — a queue of *artifacts* (text, URL, image, QR payload, UPI
  payload). Each artifact kind is routed to specialist tools; tools can emit new
  artifacts (e.g. OCR text → extracted URLs → URL analyzer). Every tool call is
  traced and streamed to the browser as NDJSON (`?stream=true`), so the progress
  UI reflects real work.
* **Risk engine → explanation** — component scores are combined (§6), then the
  RAG layer retrieves guidance for the evidence found.
* **Persistence** — PostgreSQL (production) / SQLite (local) through SQLAlchemy 2
  and Alembic migrations (Figure 4).

## 4. Data collection and preprocessing

### 4.1 Text (messages)

| Source | Rows | Use |
|---|---|---|
| UCI SMS Spam Collection | 5,160 after de-duplication | real SMS; spam → scam |
| Curated India-specific set | 242 | fictional, author-written UPI/KYC/task-job/digital-arrest scams and formal legitimate bank/OTP messages; weighted ×3 |
| **Total** | **5,402 (745 scam)** | |

The 2011 corpus under-represents current Indian scam types and its legitimate
class is mostly casual chat; a model trained on it alone flagged formal bank
messages. The curated set closes both gaps.

Preprocessing: Unicode NFKC normalisation → lower-casing → **entity
placeholders** (`urltoken`, `emailtoken`, `moneytoken`, `phonetoken`,
`numtoken`) → punctuation removal. Placeholders make the model learn patterns
("contains a link", "asks for an amount") rather than memorise numbers or
domains. The preprocessing function is stored inside the persisted pipeline so
training and inference cannot drift.

### 4.2 URLs

| Source | Use |
|---|---|
| PhiUSIIL phishing dataset (235,795 URLs) | phishing + legitimate URLs |
| Tranco top-30k popular domains | additional legitimate domains |
| **Total after de-duplication** | **131,076 registered domains (43,468 phishing)** |

**Dataset-bias analysis.** In PhiUSIIL every legitimate URL is a bare
`https://www.<domain>` homepage (0 % have a path, 100 % HTTPS), so a model
trained on full URLs learns "has a path ⇒ phishing". Its legitimate domains are
also mostly obscure, so the model initially scored `google.com` as 0.82
phishing. Corrective steps (ADR-004):

1. The model sees only the **registered domain**; scheme, path, query and
   sub-domain signals are handled by transparent rules.
2. Tranco popular domains were added to the legitimate class (excluding any
   domain known as phishing, free-hosting platforms and shorteners).
3. Domains were de-duplicated **before** the train/test split so no domain
   appears in both.

### 4.3 Images and QR

No model is trained for images. Screenshots are processed with a pre-trained OCR
engine and QR codes with a classical decoder (§5.3). Sample images in
[`samples/`](../samples) were created for testing.

## 5. Model and analyzer design (Figure 3)

### 5.1 Text scam classifier

`FeatureUnion(word TF-IDF 1–2-grams, char_wb TF-IDF 3–5-grams) → Logistic
Regression (class_weight="balanced")`. Regularisation strength `C` is chosen by
5-fold stratified cross-validation over {1, 4, 10}.

Logistic Regression was chosen over a linear SVM or a transformer because it:
(a) produces probabilities the risk engine can scale, (b) exposes per-term
contributions for explanation, (c) runs in milliseconds on a free-tier CPU.

**22 tactic rules** (named, weighted regular expressions — e.g. `OTP_REQUEST`,
`PIN_REQUEST`, `RECEIVE_MONEY_TRICK`, `DIGITAL_ARREST`, `ACCOUNT_THREAT`,
`URGENCY`) identify *which* tactic is used. Negation is handled ("Do not share
your OTP" does not trigger `OTP_REQUEST`); reassuring rules (`SAFETY_ADVICE`,
`OFFICIAL_CHANNEL`) subtract points.

### 5.2 URL risk analyzer

Character 2–5-gram TF-IDF on the registered domain + 11 scaled lexical features
(length, hyphens, digit ratio, Shannon entropy, suspicious TLD, bait keywords,
…) → Logistic Regression. Combined with 20+ rules: brand impersonation,
typosquatting (edit distance to official brand domains), IP host, punycode
homographs, shorteners, free hosting/tunnels, risky downloads (.apk/.exe),
missing HTTPS, and reassuring allow-lists (exact known domains, official
suffixes such as `gov.in`). **The backend never fetches the URL.** An optional
Google Safe Browsing lookup sends only the URL string.

### 5.3 Screenshot OCR, QR and UPI

* **OCR** — RapidOCR (PaddleOCR models in ONNX Runtime, CPU). Detector input is
  capped at 960 px on the longest side and ONNX Runtime is limited to one thread
  per pool (a production memory fix, §8.2). OCR text is repaired (re-joining
  URLs wrapped across lines, splitting merged words) before analysis, and the
  same image is scanned for QR codes.
* **QR** — OpenCV `QRCodeDetector` with up to six pre-processing variants
  (grey, up/down-scaling, adaptive threshold, Otsu, inversion).
* **UPI** — `upi://pay` payloads are parsed (payee, amount, note). Rules encode
  the fact that scanning a UPI QR always *pays* the payee; a pre-filled amount,
  a personal payee handle and refund/prize wording are flagged.

## 6. Risk scoring and explanation

### 6.1 Risk engine

```
TEXT = 70 × P_text(scam)    + clamp(Σ rule weights, −15, +30)
       (45 × P when uncorroborated: no medium+ tactic and no call to action)
URL  = 55 × P_url(phishing) + clamp(Σ rule weights, −45, +45)
UPI  = 20 (baseline)        + Σ rule weights
Floors: critical tactics → 60/80 · brand impersonation, typosquat, risky download → 70
        UPI refund/prize note → 75 · reputation "malicious" → 95
FINAL = max(components) + 5 per other component ≥ 50 (bonus ≤ +10)
Bands: 0–29 LOW · 30–59 MEDIUM · 60–79 HIGH · 80–100 CRITICAL
```

The URL model's maximum contribution (55) is deliberately below the HIGH
threshold, so **a URL can only be called HIGH when rules corroborate the
model**. The text side follows the same principle (ADR-014): if a message has
no medium-or-stronger tactic **and** no call to action (no link to a
non-official domain, no un-negated click / call / reply / pay / scan request),
the model weight drops to 45. Resemblance in style alone can then raise a MEDIUM
"uncertain" result but never HIGH. Tactics quoted inside a warning ("Beware of
fraudsters asking you to …") are not counted as requests, and a plain expiry
date is not treated as an account threat. `max` (not an average) is used because one dangerous link inside an
innocent-sounding message is still dangerous. Each result stores its full
breakdown, which the UI shows under *View technical details*.

### 6.2 Retrieval-augmented explanation

12 safety guides → 51 section chunks → LSA embeddings (TF-IDF + truncated SVD)
→ FAISS index. The retrieval query is built from the **evidence found**. For a
result explanation, only guide *sections* written about a found tactic are
eligible, with no similarity fallback, and a passage illustrated with a brand
absent from the user's content is skipped (ADR-015). Before this rule, a
renewal reminder with no link was shown an SBI link-checking example. The
explanation names the strongest warning signs actually found. MEDIUM results
state what is uncertain and how to verify; LOW states that nothing was found,
not that the content is safe. Advice is selected from the evidence codes plus
the *scenario* the content is about (renewal, KYC, QR link, UPI QR), which
chooses wording only and never adds evidence or points. An optional LLM rewrite
(disabled in production) operates under a fixed verdict and a validated schema,
and falls back to the template on any error — it can never change the score.

## 7. Testing and evaluation methodology

### 7.1 Model evaluation (offline)

Stratified 80/20 hold-out split (seed 42), plus cross-validation on the training
portion.

| Model | Set | n | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|---|
| Text | hold-out | 1,081 | 0.953 | 0.946 | **0.950** | **0.991** |
| Text | curated subset of hold-out | 49 | 0.870 | 0.952 | 0.909 | 0.985 |
| Text | 5-fold CV (train) | — | — | — | 0.934 | — |
| URL (domain only) | hold-out | 26,216 | 0.614 | 0.655 | 0.633 | 0.808 |
| URL (domain only) | realistic hand-picked hosts | 52 | 0.750 | 1.000 | 0.857 | 1.000 |

Text hold-out confusion matrix: TP 141 · FP 7 · FN 8 · TN 925.

The URL model's hold-out score is modest **by design**: judging a bare domain
name is a hard task, and that is why its weight is capped (§6.1).

### 7.2 System-level evaluation (full agent: models + rules + risk engine)

`scripts/evaluate_pipeline.py` runs the complete pipeline on labelled sets:

| Set | Result |
|---|---|
| Realistic URLs (24 scam / 28 legitimate) | 24/24 scams flagged HIGH+, 0 false HIGH |
| Unseen popular domains (Tranco ranks 50,001–50,500, 500 legitimate) | 388 LOW, 109 MEDIUM, **3 false HIGH (0.6 %)** |
| PhiUSIIL phishing sample (300) | 69 HIGH+, 184 MEDIUM, 47 missed — **84.3 % warned or flagged** |
| Curated messages (seen in training; 103 scam / 139 legitimate) | 103/103 flagged, 1 false HIGH (0.7 %) |

### 7.3 Scenario review

`scripts/review_samples.py` runs **25 labelled scenarios** across all input
types — scam/safe/suspicious messages, links, QR codes (website, phishing URL,
UPI refund bait), screenshots (scam text, scam text + URL, normal chat) and
error cases (invalid link, undecodable QR, image without text). Result:
**25/25 matched the expected outcome**.

### 7.4 Software testing

| Level | Tool | Scope | Result |
|---|---|---|---|
| Unit + integration (backend) | pytest | rules, models, risk engine, RAG, agent, API (incl. OCR/QR uploads), validation, production config, false-positive calibration, scam regressions and explanation grounding; SQLite by default, verified on PostgreSQL 16 | **154 passed** |
| Unit (frontend) | Vitest + Testing Library | NDJSON stream parsing, error mapping, risk UI, input validation, scanner, settings | **18 passed** |
| Static checks | TypeScript, ESLint | whole frontend | clean |
| Build | Next.js production build with Vercel configuration | build guard rejects a missing/localhost API URL | success |
| End-to-end | Playwright (desktop + mobile) | real browser against the **live** site (desktop project) | **5/5 passed** |
| Production verification | scripted checks | health, streaming OCR (CRITICAL 100, OCR confidence 0.98, 7.3 s), 10 health probes during/after OCR | all 200 |

Transcripts are rendered in [`images/testing/`](images/testing).

### 7.5 Reproducibility

```bash
python scripts/fetch_datasets.py
cd backend && python -m app.ml.text.train && python -m app.ml.url.train && cd ..
python scripts/evaluate_pipeline.py          # §7.2
python scripts/review_samples.py             # §7.3 (needs the backend on :8000)
cd backend && pytest                         # §7.4
cd frontend && npm test && npm run typecheck && npm run lint
```

Metrics are written to `models/*.metrics.json` and
`models/pipeline_evaluation.json`.

## 8. Deployment methodology

### 8.1 Infrastructure

* **Backend** — Render Blueprint (`render.yaml`): Python 3.11.9, single uvicorn
  worker, health check `/api/health`, managed PostgreSQL, secrets marked
  `sync: false` (set only in the Render dashboard, never in the repo).
* **Frontend** — Vercel (root `frontend/`); the build fails if
  `NEXT_PUBLIC_API_URL` is missing or points to localhost.
* **CORS** — explicit allow-list of the production site and local development.
* Frontend-only commits carry `[skip render]` so the API is not redeployed.

### 8.2 Production issue: OCR out-of-memory (case study)

Screenshot analysis crashed the free-tier (512 MB) instance. Diagnosis from
Render events ("Ran out of memory") and local memory profiling showed two
causes: large images inflating the OCR detector input, and ONNX Runtime
allocating per-core thread pools and memory arenas. Fixes: cap detector input at
960 px, one intra-/inter-op thread, `MALLOC_ARENA_MAX=2` and single-threaded
BLAS/OpenMP. After the fix, streaming OCR completed in 7.3 s with the service
staying healthy (§7.4).

## 9. Privacy, security and ethics

* No account; an anonymous random device ID that the user can reset.
* Raw message text and uploaded images are **not stored** — only the result and
  a masked preview (long numbers masked).
* Links are never opened; uploads are size-capped, magic-byte checked and fully
  decoded before analysis.
* Scam-report evidence is re-encoded (EXIF/GPS removed) and never public; the
  map shows only city-level aggregates, and demonstration data is labelled.
* Secrets exist only as platform environment variables; `.env.example` contains
  placeholders only.
* The UI states that the assessment is automated and can be wrong, and points
  to official channels (helpline 1930, cybercrime.gov.in).

## 10. Limitations

* Text model is English-centric; Hindi/Hinglish and very new scam scripts are
  under-represented. Curated examples are author-written.
* A domain name alone is weak evidence; compromised legitimate sites can host
  phishing pages and will rely on rules/reputation only.
* No domain age, WHOIS or page-content analysis (links are deliberately not
  fetched).
* OCR accuracy drops on low-resolution or heavily stylised screenshots.
* Free-tier hosting: cold starts, and the non-streaming image endpoint can block
  the single worker on a small CPU (the website uses the streaming path).
* Voice/deepfake analysis is not implemented (shown as unavailable).

See [README §17](../README.md#17-future-improvements) for planned improvements.
