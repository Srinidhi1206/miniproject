# SENTINEL — AI Consumer Scam Prevention

> **Before you click, pay, reply, or trust — check it.**

SENTINEL helps ordinary people decide whether a message, link, screenshot or QR
code is a scam *before* they act on it. Paste or upload the content (no account
needed) and SENTINEL shows:

* a **0–100 risk score** and level (Low · Medium · High · Critical),
* **the exact warning signs** it found, quoted from your content,
* **why they matter**, grounded in a curated safety knowledge base,
* **what to do next**, and
* for the curious, the full score breakdown, model outputs and agent trace.

---

## 1. Problem statement

Digital payment fraud in India is dominated by social engineering: fake KYC and
account-block SMS, "scan to receive money" UPI tricks, task-based job scams,
fake police "digital arrest" calls and look-alike websites. Victims usually act
within minutes, under pressure. Existing protections are either invisible
(bank-side), generic ("be careful online") or unexplained ("this looks like
spam"). People need a fast, free check that **explains its reasoning** in plain
language at the moment of doubt.

## 2. Features

| Feature | Status |
|---|---|
| No-login instant scanner — messages (SMS/WhatsApp/email/job offer), links, screenshots, QR codes | ✅ |
| Text scam classifier (TF-IDF + Logistic Regression, trained & evaluated) + 22 tactic rules | ✅ |
| URL risk analyzer (domain model + 20+ rules, never opens links), optional Safe Browsing | ✅ |
| QR decoding (OpenCV) → URL / UPI / text analysis | ✅ |
| Screenshot OCR (RapidOCR) → text + link + QR analysis | ✅ |
| UPI payment-request analysis ("scanning pays, it never receives") | ✅ |
| Transparent risk engine with documented formula | ✅ |
| Agentic orchestration with live progress streaming | ✅ |
| RAG explanations (FAISS) + optional Claude rewriting that cannot change verdicts | ✅ |
| Device history (search/filter/sort), dashboard | ✅ |
| Scam reporting with report IDs, EXIF-stripped private evidence | ✅ |
| Anonymised community scam map (city-level, demo data clearly flagged) | ✅ |
| Safety Center (12 guides) | ✅ |
| Voice / deepfake analysis | ⏳ Phase 2 — interfaces exist; the UI says "unavailable" instead of faking it |
| Accounts | ⏳ Phase 2 — schema reserved |

## 3. Architecture

```
Browser (Next.js) ──► FastAPI ──► Input validation ──► SentinelAgent (router)
                                                        ├─ OCR · QR decoder
                                                        ├─ Text classifier + rules
                                                        ├─ URL analyzer (+ reputation)
                                                        └─ UPI analyzer
                                                     ──► Risk engine ──► RAG explanation
                                                     ──► PostgreSQL / SQLite
```

The agent **coordinates**; it never classifies. Verdicts come from supervised
models and deterministic rules. Full details: [`docs/architecture.md`](docs/architecture.md).

## 4. Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS v4, shadcn-style components on Radix UI, Lucide icons, React Leaflet |
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 (docker-compose) · SQLite (zero-setup local default) |
| ML | scikit-learn, pandas, NumPy, joblib |
| Vision | OpenCV (QR), RapidOCR / ONNX Runtime (OCR), Pillow |
| RAG | FAISS, LSA embeddings (TF-IDF + SVD) · optional Anthropic Claude |
| Testing | pytest (66 tests), Vitest + Testing Library, Playwright |

## 5. Folder structure

```
.
├── frontend/                 Next.js app
│   ├── app/(site)/           landing page
│   ├── app/(app)/            dashboard, analyze, analysis/[id], history, map, report, safety, settings
│   ├── features/             scanner, analysis report, community
│   ├── components/ hooks/ lib/ types/
├── backend/
│   ├── app/
│   │   ├── api/              REST endpoints
│   │   ├── agents/           SentinelAgent orchestrator
│   │   ├── ml/text/ ml/url/  models, rules, training scripts
│   │   ├── services/         OCR, QR, UPI, reputation, audio (Phase 2), persistence
│   │   ├── risk/             risk engine, recommendations
│   │   ├── rag/              knowledge loader, FAISS index, explainer, LLM provider
│   │   ├── core/ db/ models/ schemas/
│   │   └── main.py
│   ├── knowledge/            safety guides (Safety Center + RAG corpus)
│   ├── alembic/              migrations
│   └── tests/
├── data/                     datasets (raw/ is downloaded, curated/ is committed)
├── models/                   trained artifacts + metrics (binaries git-ignored)
├── docs/                     architecture · api · ml-pipeline · decisions
├── scripts/                  dataset fetch, pipeline evaluation
├── docker-compose.yml
└── .env.example
```

## 6. Local setup

Prerequisites: **Python 3.11**, **Node 20+**. Docker is optional.

```bash
# 1. Backend environment
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Datasets + models (≈75 MB download, ~2 min training)
cd ..
python scripts/fetch_datasets.py
cd backend
python -m app.ml.text.train
python -m app.ml.url.train

# 3. Frontend
cd ../frontend
npm install
```

## 7. Environment variables

Copy `.env.example` to `.env`. **Every variable is optional** — with none set,
SENTINEL runs fully offline on SQLite with local models.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite at `backend/var/sentinel.db` | e.g. `postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel` |
| `CORS_ORIGINS` | `http://localhost:3000,…` | allowed browser origins |
| `MAX_UPLOAD_MB` | `8` | upload limit |
| `RATE_LIMIT_PER_MINUTE` | `30` | per-IP limit on analyze/report |
| `LLM_PROVIDER` | `none` | `anthropic` enables Claude explanation rewriting |
| `LLM_API_KEY` / `LLM_MODEL` | — / `claude-opus-5` | used only when `LLM_PROVIDER=anthropic` |
| `URL_REPUTATION_API_KEY` | — | Google Safe Browsing v4 key |
| `SEED_DEMO` | `1` | `0` disables fictional demo map reports |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | where the browser reaches the API |
| `INTERNAL_API_URL` | = public URL | server-side rendering → API (docker network) |

## 8. Running the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Startup applies migrations, seeds cities, safety guides and (flagged) demo
reports, and warms up the models. API docs: http://localhost:8000/docs.
Capability status: http://localhost:8000/api/health.

## 9. Running the frontend

```bash
cd frontend
npm run dev        # http://localhost:3000
```

## 10. Running the database

SQLite needs nothing. For PostgreSQL:

```bash
docker compose up -d db
# then set DATABASE_URL=postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel
```

Or run the full stack (train the models first; `models/` is mounted):

```bash
docker compose up --build
```

## 11. ML pipeline

* **Text** — UCI SMS Spam Collection + 242 curated India-specific examples →
  normalisation with entity placeholders → word & char TF-IDF → Logistic
  Regression. Hold-out **F1 0.950, ROC-AUC 0.991**.
* **URL** — PhiUSIIL (235k URLs) + Tranco popular domains → registered-domain
  char n-grams + lexical features → Logistic Regression, combined with
  transparent rules. On 500 unseen popular domains the full pipeline raises
  **0.6 % false HIGH alarms**; it warns on or flags **84 %** of phishing URLs.
* **Risk engine** — `text = 70·P + rules`, `url = 55·P + rules`, final = max +
  corroboration, fixed bands. Every result includes its own breakdown.

Details, rule catalogue, dataset-bias handling and limitations:
[`docs/ml-pipeline.md`](docs/ml-pipeline.md).

## 12. RAG pipeline

12 markdown guides → 51 section chunks → LSA embeddings → FAISS. The retrieval
query is built from the **evidence actually found**, re-ranked by evidence tags.
Explanations are composed from findings + retrieved passages; if
`LLM_PROVIDER=anthropic`, Claude rewrites them under a fixed verdict and a
validated output schema, falling back to the template on any error. The same
guides power the Safety Center.

## 13. Agentic architecture

`SentinelAgent` holds a queue of *artifacts*. Each artifact kind maps to
specialist tools, and tools can create new artifacts:

```
QR image  → qr_decoder → (UPI payload → upi_analyzer) | (URL → url_analyzer)
Screenshot→ qr_scanner + ocr_reader → text_classifier → url_extractor → url_analyzer
```

Every tool call is recorded and streamed (`?stream=true`), so the progress UI
shows real work, and the final report contains the full trace. If a tool fails,
the agent records the failure, adds a limitation note and continues.

## 14. API documentation

See [`docs/api.md`](docs/api.md) or the live Swagger UI at `/docs`.

```
POST /api/analyze/{text|url|image|qr|audio}[?stream=true]
GET  /api/analysis/{id}
GET  /api/history   DELETE /api/history   GET /api/stats
GET  /api/reports/options   POST /api/reports
GET  /api/scam-map
GET  /api/safety-guides   GET /api/safety-guides/{slug}
GET  /api/health
```

## 15. Testing

```bash
cd backend && pytest                    # 66 tests: rules, models, risk, RAG, full API incl. OCR/QR
cd frontend && npm test                 # Vitest component & logic tests
cd frontend && npx playwright test      # end-to-end journey (needs both servers running)
python scripts/evaluate_pipeline.py     # system-level evaluation on labelled sets
```

## 16. Security & privacy

No login; raw text and images are never stored; links are never fetched;
uploads are size-capped, magic-byte checked and fully decoded before analysis;
report evidence is re-encoded (EXIF/GPS removed) and never public; the map shows
only city-level aggregates; errors never leak stack traces; logs never contain
full user content; rate limiting and restricted CORS are on by default.

## 17. Future improvements

* Voice: speech-to-text (e.g. Whisper) + a validated deepfake-voice model.
* Domain age / WHOIS and certificate-transparency signals; sandboxed page
  rendering for link content analysis.
* Transformer text model fine-tuned on a larger, independently labelled Indian
  scam corpus including Hindi/Hinglish.
* Optional accounts for cross-device history; moderation queue for reports.
* Browser extension and share-sheet integration on mobile.
* Integration with official reporting (cybercrime.gov.in) where APIs allow.

---

**Disclaimer.** SENTINEL is an academic prototype. It gives an automated
assessment that can be wrong. When money or accounts are involved, verify
through official channels. In India, report cyber fraud at
[cybercrime.gov.in](https://cybercrime.gov.in) or call **1930**.
