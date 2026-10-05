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

| | |
|---|---|
| **Live website** | https://miniproject-sage-rho.vercel.app/ |
| **Frontend** | Next.js on Vercel (root directory `frontend/`) |
| **Backend API** | FastAPI on Render — **not deployed yet**: follow [§19 Production deployment](#19-production-deployment), then record the URL here |
| **API docs / health** | `<backend-url>/docs` · `<backend-url>/api/health` |

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
| Testing | pytest (83 tests), Vitest + Testing Library, Playwright |

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

# 2. Frontend
cd ../frontend
npm install
```

The two trained models (`models/text_scam_lr.joblib`, `models/url_host_lr.joblib`,
about 1.8 MB) are committed, so no training is needed. To reproduce them from the
public datasets (about 75 MB download, ~2 min):

```bash
python scripts/fetch_datasets.py        # from the repo root
cd backend
python -m app.ml.text.train
python -m app.ml.url.train
```

## 7. Environment variables

Copy `.env.example` to `.env` for local overrides. **Locally every variable is
optional**: with none set, SENTINEL runs offline on SQLite with the committed
models. Never commit `.env`; production values are set in the Render and Vercel
dashboards.

**Backend (FastAPI)**

| Variable | Local value | Production value (Render) | Purpose |
|---|---|---|---|
| `DATABASE_URL` | *(unset → SQLite `backend/var/sentinel.db`)* | set automatically from the Render PostgreSQL database | `postgres://…` / `postgresql://…` URLs are accepted and rewritten for psycopg |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` (default) | `https://miniproject-sage-rho.vercel.app,http://localhost:3000` | exact browser origins allowed to call the API (never `*`) |
| `CORS_ORIGIN_REGEX` | *(unset)* | *(optional)* e.g. Vercel preview URLs | extra allowed origins by regex |
| `SENTINEL_ENV` | `development` | `production` | reported by `/api/health` |
| `FORWARDED_ALLOW_IPS` | *(unset)* | `*` | trust the host's proxy headers so rate limiting is per visitor |
| `RATE_LIMIT_PER_MINUTE` | `30` | `30` | per-IP limit on analyze and report endpoints |
| `MAX_UPLOAD_MB` | `8` | `8` | upload limit (enforced before the body is read) |
| `SEED_DEMO` | `1` | `1` | `0` disables the clearly flagged fictional demo map reports |
| `LLM_PROVIDER` | `none` | `none` | `anthropic` enables optional Claude rewriting of explanations |
| `LLM_API_KEY` / `LLM_MODEL` | — / `claude-opus-5` | secret, only if `LLM_PROVIDER=anthropic` | never needed for detection |
| `URL_REPUTATION_API_KEY` | — | secret, optional | Google Safe Browsing v4; without it links are judged on structure only |

**Frontend (Next.js)**

| Variable | Local value | Production value (Vercel) | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` (default) | `https://<your-render-service>.onrender.com` | where the **browser** reaches the API; inlined at **build** time |
| `INTERNAL_API_URL` | *(unset)* | *(unset)* | only used by docker-compose (`http://backend:8000`) |

`NEXT_PUBLIC_*` values are visible to every visitor, so never put secrets in them.
A Vercel build **fails on purpose** if `NEXT_PUBLIC_API_URL` is missing or points
to localhost (see `frontend/next.config.ts`).

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

Or run the full stack (`models/` is mounted into the backend container):

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
cd backend && pytest                    # 83 tests: rules, models, risk engine, RAG, API incl. OCR/QR, prod config
cd frontend && npm test                 # 15 Vitest tests: stream parsing, errors, risk UI, validation, scanner
cd frontend && npm run test:e2e         # 10 Playwright tests (desktop + mobile), needs both servers running
python scripts/evaluate_pipeline.py     # system-level evaluation on labelled sets
```

The backend suite runs on SQLite by default; point it at an empty PostgreSQL
database to test the production engine (verified on PostgreSQL 16):

```bash
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/sentinel_test pytest
```

Playwright uses its bundled Chromium (`npx playwright install chromium`), or an
installed browser via `PLAYWRIGHT_CHANNEL=msedge` / `chrome`.

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

## 18. Recommended Demo Flow (3–5 minutes)

For project evaluation, follow this sequence to demonstrate the full lifecycle:

1. **Open SENTINEL**: Show the clean, no-login landing page and problem statement.
2. **Main Scanner**: Switch to the "Scan" tab.
3. **Analyze**: Submit a highly suspicious phishing SMS or UPI scam screenshot.
4. **Risk Score**: Show the final 0–100 deterministic risk score (e.g., HIGH or CRITICAL).
5. **Evidence**: Point out the specific extracted text, triggered rules, and the ML probability.
6. **Explanation**: Show the plain-language RAG explanation and actionable Next Steps.
7. **Report**: Click "Report this scam". Submit the fictional report anonymously.
8. **Scam Map**: Open the Community Scam Map to show how the report safely aggregates by city and type without exposing the raw description or screenshot.
9. **Your Checks**: Open the local History dashboard to show the persisted analysis.
10. **Safety Center**: Briefly open the Safety Center to show the curated RAG knowledge base.

## 19. Production deployment

```
Browser ──► Vercel (Next.js, frontend/) ──HTTPS + CORS──► Render (FastAPI) ──► Render PostgreSQL
```

The backend is deployed from [`render.yaml`](render.yaml), a Render Blueprint
that creates a free Python web service plus a free PostgreSQL database. SQLite
is **not** used in production: Render's disk is wiped on every deploy, which
would erase history and reports.

### Step 1 — Deploy the backend (Render)

1. Sign in at https://dashboard.render.com with the GitHub account that owns this repository.
2. **New → Blueprint** → select `Srinidhi1206/miniproject` → branch `main`.
3. Render reads `render.yaml` and lists **sentinel-api** (web service) and **sentinel-db** (PostgreSQL).
   It asks for `URL_REPUTATION_API_KEY` and `LLM_API_KEY`: leave both **empty** (optional features).
4. Click **Apply**. The first build takes about 5–10 minutes (OpenCV, ONNX Runtime, scikit-learn).
5. Copy the service URL from the **sentinel-api** page, e.g. `https://sentinel-api.onrender.com`
   (Render adds a suffix if that name is taken).

What `render.yaml` sets up: `pip install -r backend/requirements.txt`; start command
`cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`;
health check `/api/health`; Python 3.11.9; `DATABASE_URL` from the database;
`CORS_ORIGINS=https://miniproject-sage-rho.vercel.app,http://localhost:3000`.
On startup the app applies Alembic migrations (non-destructive) and seeds cities,
safety guides and the flagged demo reports only if they are missing.

### Step 2 — Verify the backend

```bash
curl https://<backend-url>/api/health
```

Expect `"status": "ok"`, database dialect `postgresql`, and the text model, URL
model, OCR, QR decoder and RAG reported as `ready`. The interactive API docs are at
`https://<backend-url>/docs`.

### Step 3 — Point the frontend at it (Vercel)

1. Vercel → project **miniproject** → **Settings → General**: Root Directory `frontend`,
   Framework Preset **Next.js**, Build Command `npm run build`.
2. **Settings → Environment Variables** → add for **Production** (and **Preview** if you use previews):
   `NEXT_PUBLIC_API_URL` = `https://<backend-url>` (no trailing slash).
3. **Deployments** → latest deployment → **⋯ → Redeploy**. A rebuild is required because the URL
   is inlined at build time.

### Step 4 — Verify end to end

1. Open https://miniproject-sage-rho.vercel.app/dashboard: there must be no "can't be reached" message.
2. Analyze a message, a link, a QR code and a screenshot (QR and screenshot files are in [`samples/`](samples)).
3. Open **History**, submit a **Report**, confirm it appears on the **Scam Map**, open the **Safety Center**.
4. Check all 25 labelled samples against the live API automatically:
   `python scripts/review_samples.py --api https://<backend-url>`

### Free-tier notes

* The Render free web service sleeps after 15 minutes without traffic; the next request takes up to about a minute.
* Render free PostgreSQL databases expire 30 days after creation. For a longer-lived database, create one with
  another provider (e.g. Neon) and set its connection URL as `DATABASE_URL` on the web service.
* Report screenshots are saved on the web service's local disk, which Render does not persist across deploys;
  the report records themselves are stored in PostgreSQL.

## 20. Troubleshooting

**"SENTINEL's analysis service can't be reached right now."**
The browser could not reach the FastAPI backend. Check, in order:

1. `https://<backend-url>/api/health` responds (on the free plan, allow up to a minute for it to wake up).
2. Vercel has `NEXT_PUBLIC_API_URL` set to that URL **and the frontend was redeployed after setting it**.
   In the browser's dev tools (Network tab) API requests must go to the Render URL, not `localhost:8000`.
3. The backend's `CORS_ORIGINS` contains the exact site origin (`https://miniproject-sage-rho.vercel.app`,
   no trailing slash). A CORS rejection appears in the browser console as a blocked request.

**Vercel build fails with "NEXT_PUBLIC_API_URL is not set" or "points to localhost".**
This is an intentional guard. Set the variable to the deployed backend URL and redeploy.

**Local dev server shows a blank page or missing styles after a build.**
`npm run build` and `npm run dev` share the `.next` folder. Never run `npm run build` while
`npm run dev` is running. To recover, stop the dev server, then:

```powershell
cd frontend
Remove-Item -Recurse -Force .next      # macOS/Linux: rm -rf .next
npm run dev
```

**Backend fails to start with a database error.**
`DATABASE_URL` must point to a reachable PostgreSQL database (leave it unset locally to use SQLite).


---

**Disclaimer.** SENTINEL is an academic prototype. It gives an automated
assessment that can be wrong. When money or accounts are involved, verify
through official channels. In India, report cyber fraud at
[cybercrime.gov.in](https://cybercrime.gov.in) or call **1930**.
