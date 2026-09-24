# Models

Model binaries are **not committed** (see `.gitignore`). Recreate them:

```bash
python scripts/fetch_datasets.py          # once
cd backend
python -m app.ml.text.train               # -> text_scam_lr.joblib + .metrics.json
python -m app.ml.url.train                # -> url_host_lr.joblib + .metrics.json
```

| Artifact | Model | Input |
|---|---|---|
| `text_scam_lr.joblib` | TF-IDF (word 1–2 + char 3–5 grams) → Logistic Regression | normalised message text |
| `url_host_lr.joblib` | char 2–5-gram TF-IDF + 11 lexical features → Logistic Regression | registered domain only |

Each bundle stores the sklearn pipeline, a version stamp (UTC timestamp), the
decision threshold and its evaluation metrics. If a model file is missing the
backend still runs: the text analyzer falls back to rule-based indicators and
the URL analyzer to URL rules, and `/api/health` reports the degraded state.
