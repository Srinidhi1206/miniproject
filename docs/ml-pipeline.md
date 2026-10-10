# SENTINEL — ML, rules, risk engine and RAG

All numbers below come from `models/*.metrics.json` and
`models/pipeline_evaluation.json`, produced by the scripts in this repo.
Reproduce with:

```bash
python scripts/fetch_datasets.py
cd backend
python -m app.ml.text.train
python -m app.ml.url.train
cd .. && python scripts/evaluate_pipeline.py
```

---

## 1. Text scam detection

### Data

| Source | Rows | Notes |
|---|---|---|
| UCI SMS Spam Collection | 5,160 (after dedupe) | real SMS; `spam` → scam (1), `ham` → 0 |
| SENTINEL curated set | 242 | author-written, fictional, India-specific scam patterns + formal legitimate messages; weighted ×3 |

The 2011 SMS corpus under-represents today's scams (UPI, KYC, task jobs, digital
arrest) and its legitimate class is mostly casual chat — so a model trained on it
alone flags formal bank/OTP messages. The curated set fixes both gaps.

### Preprocessing (`app/ml/text/preprocess.py`)

NFKC normalisation → lower-case → entity placeholders (`urltoken`, `emailtoken`,
`moneytoken`, `phonetoken`, `numtoken`) → punctuation removal. Placeholders make
the model learn *patterns* ("asks for an amount", "contains a link") instead of
memorising specific numbers or domains. The function is part of the persisted
pipeline, so training and inference cannot drift.

### Model

```
FeatureUnion(
  word TF-IDF  (1–2 grams, min_df 2, sublinear, 30k features),
  char TF-IDF  (char_wb 3–5 grams, min_df 3, sublinear, 40k features)
) → LogisticRegression(class_weight="balanced", liblinear)
```

Logistic regression was chosen over a linear SVM because it gives calibrated
probabilities (the risk engine needs P(scam)) and per-term contributions for
explainability. `C` is selected by 5-fold stratified CV (grid 1 / 4 / 10).

### Results (stratified 80/20 hold-out, seed 42)

| Split | n | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Full hold-out | 1,081 | 0.953 | 0.946 | **0.950** | **0.991** |
| Curated subset of hold-out | 49 | 0.870 | 0.952 | 0.909 | 0.985 |
| 5-fold CV F1 (train) | — | — | — | 0.934 | — |

### Explainability

For each prediction the detector returns the word n-grams that pushed the score
**toward "scam"** (TF-IDF value × coefficient), e.g. `[link]`, `update`, `kyc`,
`will be blocked`. Shown under *View technical details*.

### Indicator rules (`app/ml/text/indicators.py`)

22 named, weighted regular expressions detect specific tactics — the model says
*how scam-like* the text is; rules say *which tactics* are used:

| Code | Example trigger | Weight |
|---|---|---|
| `OTP_REQUEST` | "share the OTP you received" | 18 (critical) |
| `PIN_REQUEST` | "enter your UPI PIN" | 18 (critical) |
| `RECEIVE_MONEY_TRICK` | "scan … to receive ₹" | 16 (critical) |
| `DIGITAL_ARREST` | "digital arrest", "money laundering" | 16 (critical) |
| `REMOTE_ACCESS` | "AnyDesk", ".apk" | 16 (critical) |
| `THREAT_EXPOSURE` | "send your photos to your family" | 16 (critical) |
| `UPFRONT_FEE` | "registration fee" | 12 |
| `SENSITIVE_DATA` | "send card number / CVV / Aadhaar" | 12 |
| `GIFT_CARDS` | "buy gift cards, send codes" | 12 |
| `ACCOUNT_THREAT` | "account will be blocked" | 10 |
| `PAYMENT_REQUEST`, `UNREALISTIC_RETURNS`, `AUTHORITY_CLAIM`, `SECRECY`, `MISDIRECTED_MONEY`, `FAMILY_EMERGENCY` | | 10 |
| `URGENCY`, `PRIZE`, `TASK_JOB` | | 8 |
| `CRYPTO_INVEST`, `CALL_UNKNOWN_NUMBER`, `MESSAGING_REDIRECT`, `GENERIC_GREETING` | | 3–6 |
| `SAFETY_ADVICE` / `OFFICIAL_CHANNEL` (reassuring) | "Do not share this OTP" | −6 / −4 |

Negation handling: "Do not share your OTP" does **not** trigger `OTP_REQUEST`;
negatable rules run only on raw text so sentence boundaries are respected.

---

## 2. URL risk analysis

### Data and a dataset-bias problem

PhiUSIIL (235,795 URLs) labels **every** legitimate URL as a bare
`https://www.<domain>` homepage — 0 % have a path, 100 % use HTTPS. A model
trained on full URLs learns "has a path or uses http ⇒ phishing". Two fixes
(see ADR-004):

1. The model scores only the **registered domain** (`sbi-kyc-verify.co`).
   Scheme, path, query and sub-domain signals are handled by transparent rules.
2. PhiUSIIL's legitimate domains are mostly obscure small sites, so the model
   learned "brand-looking ⇒ phishing" and scored `google.com` 0.82. The
   legitimate class is supplemented with the **Tranco top-30k** popular domains
   (excluding any domain seen as phishing, free-hosting platforms and shorteners).

### Model

Char 2–5-gram TF-IDF on the registered domain + 11 scaled lexical features
(length, labels, hyphens, digit ratio, Shannon entropy, longest label, consonant
run, bait-keyword hits, suspicious TLD, digits in name, IP) → Logistic Regression.
Domains are de-duplicated before the split so none appears in train and test.

### Results

| Evaluation | ROC-AUC | Note |
|---|---|---|
| Domain-level hold-out (26,216 domains) | 0.808 | hard, honest task: judging a bare domain name |
| Realistic hand-picked set (52 hosts) | 1.000 | real sub-domains of banks/Google/etc. vs typical phishing hosts |

A domain name alone is weak evidence — many phishing pages sit on compromised,
ordinary-looking domains. That is why the model can contribute at most 55 of
100 points and **rules must corroborate** before a URL is called HIGH risk.

### URL rules (`app/ml/url/analyzer.py`)

`BRAND_IMPERSONATION` (brand keyword on a non-official domain), `TYPOSQUAT`
(edit distance to official brand labels, including sub-domain tokens and
deletion typos, first letter anchored), `IP_HOST`, `PUNYCODE` (mixed-script
homographs only), `AT_SYMBOL`, `SHORTENER`, `FREE_HOSTING` (incl. tunnels and
dynamic DNS), `USER_CONTENT_PAGE` (forms/files on trusted platforms),
`SUSPICIOUS_TLD`, `NO_HTTPS`, `ODD_PORT`, `DEEP_SUBDOMAIN`, `HYPHENATED_HOST`,
`LONG_URL`, `SENSITIVE_KEYWORDS`, `RISKY_DOWNLOAD` (.apk/.exe…), `EMAIL_IN_URL`,
`COMPROMISED_SITE_PATH`, `EMBEDDED_REDIRECT`, `HEAVY_ENCODING`; reassuring:
`KNOWN_DOMAIN` (−40, exact registered-domain allowlist) and `OFFICIAL_SUFFIX`
(−30, gov.in / nic.in / ac.in …).

**No network access**: the backend never fetches the URL. Optional Google Safe
Browsing lookups (API key) send only the URL string; if unset, results say
"judged on structure only".

---

## 3. QR codes, screenshots, UPI

* **QR** — OpenCV `QRCodeDetector` tries up to six pre-processing variants
  (grey, upscale for tiny codes, downscale for huge photos, adaptive threshold,
  Otsu, inverted). The decoder only *extracts*; the payload is routed to the URL,
  UPI or text analyzer.
* **Screenshots** — RapidOCR (PaddleOCR models in ONNX, CPU). OCR output is
  repaired before analysis: lines wrapped mid-URL are re-joined; runs of merged
  words are split using known acronyms, case boundaries and a unigram word
  splitter ("SharetheOTPsenttoyourphone" → "Share the OTP sent to your phone").
  The image is also scanned for QR codes.
* **UPI** — a `upi://pay` payload is parsed (payee, amount, note). Rules state the
  fact that a UPI QR always *pays* the payee; a pre-filled amount, a personal
  payee handle and refund/prize wording in the note are flagged.

---

## 4. Risk engine (`app/risk/engine.py`)

```
TEXT component = 70 × P_text(scam)     + clamp(Σ rule weights, −15, +30)
                 (45 × P instead when uncorroborated: no medium+ tactic AND no call to action)
URL  component = 55 × P_url(phishing)  + clamp(Σ rule weights, −45, +45)
UPI  component = 20 (baseline)         + Σ rule weights

Floors (recorded as "overrides" in the result):
  ≥1 critical text tactic → 60   ·  ≥2 → 80
  brand impersonation / typosquat / risky download URL → 70
  UPI note promising refund/prize → 75
  reputation service: malicious → 95

FINAL = max(component scores) + 5 × (other components ≥ 50), bonus capped at +10

0–29 LOW (SAFE) · 30–59 MEDIUM (SUSPICIOUS) · 60–79 HIGH (SCAM) · 80–100 CRITICAL (SCAM)
```

**Worked example** — "Dear customer your SBI account will be blocked today.
Update KYC at http://sbi-kyc-verify.co/update":

| Component | Model pts | Rule pts | Score |
|---|---|---|---|
| Text: P=1.00 → 70; ACCOUNT_THREAT 10 + URGENCY 8 + GENERIC_GREETING 3 + … (cap 30) | 70.0 | +26 | 96 |
| URL: P=0.92 → 50.7; BRAND_IMPERSONATION 22 + SENSITIVE_KEYWORDS 10 + NO_HTTPS 6 + … (cap 45) | 50.7 | +45 | 96 |
| Final: max(96) + 5 (URL ≥ 50 corroborates) | | | **100 · CRITICAL** |

Why `max` and not an average: one dangerous link inside an innocent-sounding
message is still dangerous. Confidence shown to users is the primary model's
confidence in its own label, `max(p, 1−p)`.

---

## 5. RAG explanation layer

* **Knowledge base**: 12 markdown guides in `backend/knowledge/` (UPI, OTP/PIN,
  phishing, fake websites, jobs, QR, social engineering, digital arrest,
  investment, account security, deepfakes, what to do if scammed). Each
  `## section` is a chunk (51 chunks). The same files seed the Safety Center.
* **Embeddings**: LSA — TF-IDF (1–2 grams) → TruncatedSVD → L2-normalised dense
  vectors, fitted on the corpus. Offline and deterministic; the `Embedder`
  protocol allows a sentence-transformer later.
* **Index**: FAISS `IndexFlatIP` (cosine), NumPy fallback.
* **Retrieval**: query built from the *found evidence* labels; results re-ranked
  with +0.12 per matching evidence tag; generic "warning signs / what to do"
  sections down-weighted; max two chunks per guide.
* **Generation**:
  * default `template+rag`: verdict sentence with the real numbers, each top
    finding's rationale, plus the lead paragraph of retrieved passages;
  * optional `llm:<model>+rag` (`LLM_PROVIDER=anthropic`): Claude receives the
    fixed verdict, the evidence and the passages and returns a schema-validated
    `{summary, why_it_matters[]}`. It cannot change the score or level; on any
    failure the template is used.
* Sources are returned and linked to the Safety Center.

---

## 6. System-level evaluation (`scripts/evaluate_pipeline.py`)

Runs the complete agent (models + rules + risk engine). "Flagged" = HIGH/CRITICAL,
"warned" = MEDIUM.

| Set | Result |
|---|---|
| 500 unseen popular domains (Tranco ranks 50,001–50,500) | **0.6 % false HIGH**, 21.8 % MEDIUM, 77.6 % LOW |
| 300 PhiUSIIL phishing URLs (fresh sample; domains mostly seen by the model) | 23 % HIGH, 61 % MEDIUM → **84.3 % warned or flagged**, 15.7 % missed |
| 52 realistic hosts | 100 % correct (optimistic: written alongside the rules) |
| 242 curated messages | 100 % of scams flagged, 0.7 % false alarms (optimistic: seen in training) |

### Known limitations

* A bare, ordinary-looking domain carries little signal; about 1 in 5 unfamiliar
  legitimate sites receive a MEDIUM "verify first" and ~16 % of phishing URLs
  without other signals score LOW. Domain-age / reputation lookups and page
  content analysis are the natural next steps.
* The text model is English-first; Hinglish and regional-language scams are
  partially covered by character n-grams only.
* The curated set is small and author-written; a larger, independently labelled
  Indian scam corpus would give more reliable estimates.
