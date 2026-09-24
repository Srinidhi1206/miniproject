"""Train and evaluate the text scam classifier.

    cd backend && python -m app.ml.text.train

Data
  * UCI SMS Spam Collection (5,574 real SMS; spam -> scam=1, ham -> 0)
  * SENTINEL curated set (data/curated/sentinel_messages.csv): author-written,
    fictional examples of India-specific scam patterns (UPI, KYC, task jobs,
    digital arrest...) and realistic legitimate transactional messages.
    Curated rows get a higher sample weight because they represent the
    target domain far better than 2011-era UK SMS spam.

Evaluation
  * Stratified 80/20 hold-out split (seeded) — reported overall AND on the
    curated subset of the hold-out.
  * 5-fold stratified CV F1 on the training portion for C selection.

Outputs models/text_scam_lr.joblib and models/text_scam_lr.metrics.json.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

from app.core.config import REPO_DIR, get_settings
from app.ml.text.model import ARTIFACT_NAME
from app.ml.text.preprocess import normalise

SEED = 42
CURATED_WEIGHT = 3.0
SMS_PATH = REPO_DIR / "data" / "raw" / "sms_spam" / "SMSSpamCollection"
CURATED_PATH = REPO_DIR / "data" / "curated" / "sentinel_messages.csv"


def load_data() -> pd.DataFrame:
    frames = []
    if SMS_PATH.exists():
        sms = pd.read_csv(SMS_PATH, sep="\t", header=None, names=["label", "text"], quoting=3, encoding="utf-8")
        sms["y"] = (sms["label"] == "spam").astype(int)
        sms["source"] = "uci_sms"
        frames.append(sms[["text", "y", "source"]])
    else:
        print(f"[warn] {SMS_PATH} missing — run scripts/fetch_datasets.py. Training on curated data only.")
    cur = pd.read_csv(CURATED_PATH)
    cur["y"] = (cur["label"] == "scam").astype(int)
    cur["source"] = "curated"
    frames.append(cur[["text", "y", "source"]])
    df = pd.concat(frames, ignore_index=True).dropna(subset=["text"])
    df["text"] = df["text"].astype(str).str.strip()
    return df.drop_duplicates(subset=["text"]).reset_index(drop=True)


def build_pipeline(C: float = 4.0) -> Pipeline:
    return Pipeline([
        ("features", FeatureUnion([
            ("word", TfidfVectorizer(preprocessor=normalise, ngram_range=(1, 2), min_df=2,
                                     sublinear_tf=True, max_features=30_000)),
            ("char", TfidfVectorizer(preprocessor=normalise, analyzer="char_wb", ngram_range=(3, 5),
                                     min_df=3, sublinear_tf=True, max_features=40_000)),
        ])),
        ("clf", LogisticRegression(C=C, class_weight="balanced", max_iter=3000, solver="liblinear")),
    ])


def _metrics(y, p, threshold=0.5) -> dict:
    pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "n": int(len(y)), "positives": int(y.sum()),
        "accuracy": round(accuracy_score(y, pred), 4),
        "precision": round(precision_score(y, pred, zero_division=0), 4),
        "recall": round(recall_score(y, pred, zero_division=0), 4),
        "f1": round(f1_score(y, pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y, p), 4) if len(set(y)) > 1 else None,
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def main() -> int:
    df = load_data()
    print(f"Loaded {len(df)} messages: {df.groupby(['source', 'y']).size().to_dict()}")
    train, test = train_test_split(df, test_size=0.2, stratify=df["y"].astype(str) + df["source"], random_state=SEED)
    weights = np.where(train["source"] == "curated", CURATED_WEIGHT, 1.0)

    search = GridSearchCV(
        build_pipeline(), {"clf__C": [1.0, 4.0, 10.0]}, scoring="f1",
        cv=StratifiedKFold(5, shuffle=True, random_state=SEED), n_jobs=-1,
    )
    search.fit(train["text"], train["y"], clf__sample_weight=weights)
    best_C = search.best_params_["clf__C"]
    print(f"CV best C={best_C} f1={search.best_score_:.4f}")

    pipe = search.best_estimator_
    p_test = pipe.predict_proba(test["text"])[:, 1]
    metrics = {
        "holdout": _metrics(test["y"].to_numpy(), p_test),
        "holdout_curated": _metrics(test["y"][test["source"] == "curated"].to_numpy(),
                                    p_test[(test["source"] == "curated").to_numpy()]),
        "cv_f1": round(float(search.best_score_), 4),
        "best_C": best_C,
    }
    print(json.dumps(metrics, indent=2))

    # Refit on all data for the shipped model (hyper-parameters fixed from CV).
    final = build_pipeline(best_C)
    final.fit(df["text"], df["y"], clf__sample_weight=np.where(df["source"] == "curated", CURATED_WEIGHT, 1.0))

    version = datetime.now(timezone.utc).strftime("%Y%m%d.%H%M")
    out_dir = get_settings().models_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "pipeline": final, "version": version, "threshold": 0.5, "metrics": metrics,
        "data": {"total": int(len(df)), "by_source": df["source"].value_counts().to_dict(),
                 "scam": int(df["y"].sum())},
    }
    joblib.dump(bundle, out_dir / ARTIFACT_NAME, compress=3)
    (out_dir / ARTIFACT_NAME.replace(".joblib", ".metrics.json")).write_text(
        json.dumps({"version": version, **metrics, "data": bundle["data"]}, indent=2))
    print(f"Saved {out_dir / ARTIFACT_NAME} (version {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
