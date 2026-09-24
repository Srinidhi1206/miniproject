"""System-level evaluation: runs the REAL agent (models + rules + risk engine)
on labelled examples and reports how often the final verdict is right.

    backend/.venv/Scripts/python scripts/evaluate_pipeline.py

This differs from the per-model metrics in models/*.metrics.json: it measures
what a user actually sees. "Flagged" means risk level HIGH or CRITICAL (>= 60);
"not flagged" means LOW (< 30). MEDIUM counts as a warning, reported separately.

Caveat: the curated messages were also used (x3 weighted) to train the text
model, so the message numbers here are optimistic; the URL sets were never
used for training rules or the model and are a fairer test.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.orchestrator import get_agent  # noqa: E402
from app.ml.url.train import SANITY_LEGIT, SANITY_PHISH  # noqa: E402
from app.schemas.analysis import InputType  # noqa: E402


def run(items: list[tuple[InputType, str, int]]) -> dict:
    agent = get_agent()
    buckets = Counter()
    for input_type, payload, is_scam in items:
        r = agent.run(input_type, payload)
        band = "flag" if r.risk_score >= 60 else "warn" if r.risk_score >= 30 else "clear"
        buckets[(is_scam, band)] += 1
    scam_n = sum(v for (s, _), v in buckets.items() if s)
    legit_n = sum(v for (s, _), v in buckets.items() if not s)
    return {
        "scams": scam_n,
        "scams_flagged_high": buckets[(1, "flag")],
        "scams_warned_medium": buckets[(1, "warn")],
        "scams_missed_low": buckets[(1, "clear")],
        "legit": legit_n,
        "legit_cleared_low": buckets[(0, "clear")],
        "legit_warned_medium": buckets[(0, "warn")],
        "legit_false_alarm_high": buckets[(0, "flag")],
        "scam_detection_rate": round((buckets[(1, "flag")] + buckets[(1, "warn")]) / max(scam_n, 1), 3),
        "legit_false_alarm_rate": round(buckets[(0, "flag")] / max(legit_n, 1), 3),
    }


def main() -> int:
    urls = [(InputType.URL, "https://" + h, 0) for h in SANITY_LEGIT] + \
           [(InputType.URL, "http://" + h + "/login", 1) for h in SANITY_PHISH]
    with open(ROOT / "data" / "curated" / "sentinel_messages.csv", encoding="utf-8") as f:
        msgs = [(InputType.TEXT, row["text"], int(row["label"] == "scam")) for row in csv.DictReader(f)]
    report = {"urls_realistic_set": run(urls), "messages_curated_set (seen in training)": run(msgs)}

    # Independent false-alarm test: popular domains the URL model never saw
    # (training used Tranco ranks 1-30,000).
    tranco = ROOT / "data" / "raw" / "tranco" / "top-1m.csv"
    if tranco.exists():
        with open(tranco, encoding="utf-8") as f:
            rows = [line.strip().split(",")[1] for i, line in enumerate(f) if 50_000 <= i < 50_500]
        report["urls_unseen_popular_domains (Tranco 50,001-50,500)"] = run([(InputType.URL, "https://" + d, 0) for d in rows])

    # Full phishing URLs (with paths) from PhiUSIIL. Most of their domains were in
    # the model's training data, so this mainly tests rules + pipeline, not generalisation.
    phi = ROOT / "data" / "raw" / "phiusiil" / "PhiUSIIL_Phishing_URL_Dataset.csv"
    if phi.exists():
        import pandas as pd
        df = pd.read_csv(phi, usecols=["URL", "label"])
        # Seed 7 was inspected while designing URL rules; results are reported on a fresh sample.
        sample = df[df.label == 0].sample(300, random_state=11)["URL"].tolist()
        report["urls_phiusiil_phishing_sample (domains mostly seen)"] = run([(InputType.URL, u, 1) for u in sample])
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
