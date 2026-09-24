"""Train and evaluate the URL host-risk model.

    cd backend && python -m app.ml.url.train

Data: PhiUSIIL Phishing URL Dataset (UCI, 235,795 URLs; label 1 = legitimate,
0 = phishing), supplemented with the Tranco top-30k popular domains as extra
legitimate examples. Only the REGISTERED DOMAIN of the host is used (see features.py / ADR-004).
Domains are de-duplicated before splitting so the same host can never appear
in both train and test.

Model: char n-gram TF-IDF (host string) + 11 scaled numeric host features ->
Logistic Regression. Chosen over boosted trees for calibrated probabilities
and inspectable weights.

Also runs a "sanity set" of hand-picked realistic URLs (legit sub-domains of
real services + typical phishing hosts) because PhiUSIIL's legitimate class
contains almost no sub-domains — the metric that matters for real users.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from app.core.config import REPO_DIR, get_settings
from app.ml.url.features import model_key, numeric_matrix
from app.ml.url.lexicon import FREE_HOSTING, SHORTENERS

SEED = 42
DATA = REPO_DIR / "data" / "raw" / "phiusiil" / "PhiUSIIL_Phishing_URL_Dataset.csv"
TRANCO = REPO_DIR / "data" / "raw" / "tranco" / "top-1m.csv"
TRANCO_TOP = 30_000
ARTIFACT = "url_host_lr.joblib"
MAX_PER_CLASS = 60_000  # keeps training < 1 min on a laptop; plenty for a linear model

SANITY_LEGIT = [
    "accounts.google.com", "mail.google.com", "docs.google.com", "onlinesbi.sbi", "retail.onlinesbi.sbi",
    "netbanking.hdfcbank.com", "www.icicibank.com", "pay.google.com", "www.amazon.in", "m.facebook.com",
    "web.whatsapp.com", "portal.office.com", "login.microsoftonline.com", "www.irctc.co.in",
    "incometax.gov.in", "www.flipkart.com", "developer.mozilla.org", "en.wikipedia.org",
    "cybercrime.gov.in", "www.bbc.co.uk", "news.ycombinator.com", "www.nptel.ac.in", "zerodha.com",
    "kite.zerodha.com", "www.swiggy.com", "classroom.google.com", "www.linkedin.com", "github.com",
]
SANITY_PHISH = [
    "sbi-kyc-verify.co", "hdfc-netbanking-update.xyz", "secure-axisbank-login.com", "paypa1-resolution.com",
    "appleid-verify-secure.com", "indiapost-redelivery.top", "amzn-refund-help.com", "icici-rewardz.in",
    "login-microsoftonline.support-portal.net", "netflix-billing-support.com", "fastag-kyc-update.site",
    "echallan-parivahan.pay-online.top", "flipkart-lucky-win.shop", "metamask-wallet-restore.web.app",
    "mygov-refund.surge.sh", "uidai-update.online", "dhl-customs-pay.info", "bescom-bill-pay.online",
    "google-security-check.accounts-verify.co", "bit-ly.claim-reward.xyz", "192.168.4.21",
    "epfo-claim-update.in", "incometax-refund-gov.in", "jio-free5g-offer.net",
]


def build_pipeline(C: float = 2.0) -> Pipeline:
    return Pipeline([
        ("features", FeatureUnion([
            ("chars", TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=3, sublinear_tf=True,
                                      max_features=80_000, preprocessor=model_key)),
            ("numeric", Pipeline([("extract", FunctionTransformer(numeric_matrix)), ("scale", StandardScaler())])),
        ])),
        ("clf", LogisticRegression(C=C, class_weight="balanced", max_iter=2000, solver="liblinear")),
    ])


def _metrics(y, p) -> dict:
    pred = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "n": int(len(y)), "accuracy": round(accuracy_score(y, pred), 4),
        "precision": round(precision_score(y, pred, zero_division=0), 4),
        "recall": round(recall_score(y, pred, zero_division=0), 4),
        "f1": round(f1_score(y, pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y, p), 4),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def main() -> int:
    if not DATA.exists():
        print(f"[error] {DATA} missing — run scripts/fetch_datasets.py first.")
        return 1
    df = pd.read_csv(DATA, usecols=["URL", "label"])
    df["host"] = df["URL"].astype(str).map(model_key)
    df["y"] = (df["label"] == 0).astype(int)  # 1 = phishing
    df = df[df["host"].str.len() > 3].drop_duplicates(subset=["host"])
    # Hosts appearing with both labels are ambiguous -> drop.
    conflicted = df.groupby("host")["y"].nunique()
    df = df[~df["host"].isin(conflicted[conflicted > 1].index)]
    df = (df.groupby("y", group_keys=False)
            .apply(lambda g: g.sample(min(len(g), MAX_PER_CLASS), random_state=SEED)))
    df["source"] = "phiusiil"

    # PhiUSIIL's legitimate class is mostly small, obscure sites, so the model
    # learns "brand-looking domain => phishing" and flags google.com. Supplement
    # it with real popular domains, excluding any domain seen as phishing and
    # free-hosting/shortener platforms (whose sub-sites are frequently abused).
    if TRANCO.exists():
        tranco = pd.read_csv(TRANCO, header=None, names=["rank", "domain"], nrows=TRANCO_TOP)
        tranco["host"] = tranco["domain"].astype(str).map(model_key)
        excluded = set(df.loc[df.y == 1, "host"]) | FREE_HOSTING | SHORTENERS
        tranco = tranco[~tranco["host"].isin(excluded)].drop_duplicates(subset=["host"])
        tranco = tranco[~tranco["host"].isin(set(df["host"]))]
        extra = pd.DataFrame({"host": tranco["host"], "y": 0, "source": "tranco"})
        df = pd.concat([df[["host", "y", "source"]], extra], ignore_index=True)
    else:
        print(f"[warn] {TRANCO} missing — training without popular-domain supplement.")
    print(f"Unique domains used: {len(df)} (phishing={int(df.y.sum())}) by source {df.source.value_counts().to_dict()}")

    train, test = train_test_split(df, test_size=0.2, stratify=df["y"], random_state=SEED)
    pipe = build_pipeline()
    pipe.fit(train["host"], train["y"])
    p = pipe.predict_proba(test["host"])[:, 1]

    sanity_hosts = SANITY_LEGIT + SANITY_PHISH
    sanity_y = np.array([0] * len(SANITY_LEGIT) + [1] * len(SANITY_PHISH))
    sp = pipe.predict_proba(sanity_hosts)[:, 1]
    metrics = {"holdout": _metrics(test["y"].to_numpy(), p), "sanity_set": _metrics(sanity_y, sp)}
    print(json.dumps(metrics, indent=2))
    for h, prob in zip(sanity_hosts, sp):
        print(f"  {prob:.2f}  {h}")

    version = datetime.now(timezone.utc).strftime("%Y%m%d.%H%M")
    out = get_settings().models_dir
    out.mkdir(parents=True, exist_ok=True)
    bundle = {"pipeline": pipe, "version": version, "metrics": metrics,
              "data": {"domains": int(len(df)), "phishing": int(df.y.sum()), "by_source": df.source.value_counts().to_dict()}}
    joblib.dump(bundle, out / ARTIFACT, compress=3)
    (out / ARTIFACT.replace(".joblib", ".metrics.json")).write_text(
        json.dumps({"version": version, **metrics, "data": bundle["data"]}, indent=2))
    print(f"Saved {out / ARTIFACT} (version {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
