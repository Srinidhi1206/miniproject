"""TextScamDetector — supervised baseline (TF-IDF + Logistic Regression).

The detector is an interface with one method, `predict(text) -> ModelOutput`.
Any replacement (e.g. a fine-tuned transformer) only needs to honour that
contract; the agent, risk engine and API do not change.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import joblib
import numpy as np

from app.core.config import get_settings
from app.ml.text.preprocess import normalise
from app.schemas.analysis import FeatureContribution, ModelOutput

log = logging.getLogger("sentinel.ml.text")

ARTIFACT_NAME = "text_scam_lr.joblib"
_TOKEN_LABELS = {"urltoken": "[link]", "moneytoken": "[money amount]", "phonetoken": "[phone number]",
                 "numtoken": "[number]", "emailtoken": "[email address]"}


class TextScamDetector(Protocol):
    name: str
    version: str

    def predict(self, text: str) -> ModelOutput: ...


class ModelUnavailable(RuntimeError):
    pass


class LogisticTextDetector:
    """Loads the persisted sklearn pipeline produced by `app.ml.text.train`."""

    def __init__(self, artifact_path: Path):
        if not artifact_path.exists():
            raise ModelUnavailable(
                f"Text model not found at {artifact_path}. Train it with: python -m app.ml.text.train")
        bundle = joblib.load(artifact_path)
        self.pipeline = bundle["pipeline"]
        self.version: str = bundle["version"]
        self.metrics: dict = bundle.get("metrics", {})
        self.threshold: float = bundle.get("threshold", 0.5)
        self.name = "tfidf-logreg"
        features = self.pipeline.named_steps["features"]
        self._word_vec = dict(features.transformer_list)["word"]
        self._word_names = self._word_vec.get_feature_names_out()
        clf = self.pipeline.named_steps["clf"]
        self._word_coef = clf.coef_[0][: len(self._word_names)]

    def _contributions(self, text: str, k: int = 6) -> list[FeatureContribution]:
        x = self._word_vec.transform([text])
        idx = x.indices
        if len(idx) == 0:
            return []
        contrib = x.data * self._word_coef[idx]
        # Only terms that pushed the prediction TOWARD "scam" — that is what the UI explains.
        order = [i for i in np.argsort(-contrib)[:k] if contrib[i] > 0]
        out = []
        for i in order:
            name = self._word_names[idx[i]]
            pretty = " ".join(_TOKEN_LABELS.get(t, t) for t in name.split())
            out.append(FeatureContribution(feature=pretty, weight=round(float(contrib[i]), 4)))
        return out

    def predict(self, text: str) -> ModelOutput:
        p = float(self.pipeline.predict_proba([text])[0][1])
        return ModelOutput(
            name=self.name, version=self.version, target="text",
            probability=round(p, 4), label="scam" if p >= self.threshold else "legit",
            top_features=self._contributions(text),
        )


@lru_cache
def get_text_detector() -> LogisticTextDetector:
    path = get_settings().models_dir / ARTIFACT_NAME
    detector = LogisticTextDetector(path)
    log.info("Loaded text model %s (%s)", detector.name, detector.version)
    return detector


__all__ = ["TextScamDetector", "LogisticTextDetector", "ModelUnavailable", "get_text_detector", "normalise"]
