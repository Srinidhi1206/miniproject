"""System status — reports exactly which capabilities are live, so the UI can
be honest about what is and isn't available."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.ml.text.model import ModelUnavailable, get_text_detector
from app.ml.url.analyzer import get_url_model
from app.rag.index import get_index
from app.rag.llm import get_llm
from app.services import reputation
from app.services.ocr import OCRUnavailable, get_ocr_engine

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", summary="Capability and component status")
def health():
    caps: dict[str, dict] = {}
    try:
        tm = get_text_detector()
        h = tm.metrics.get("holdout", {})
        caps["text_model"] = {"status": "ready", "name": tm.name, "version": tm.version,
                              "holdout_f1": h.get("f1"), "holdout_roc_auc": h.get("roc_auc")}
    except ModelUnavailable:
        caps["text_model"] = {"status": "unavailable", "note": "Rule-based indicators only"}
    um = get_url_model()
    if um:
        h = um.metrics.get("holdout", {})
        caps["url_model"] = {"status": "ready", "name": um.name, "version": um.version,
                             "holdout_roc_auc": h.get("roc_auc"), "sanity_roc_auc": um.metrics.get("sanity_set", {}).get("roc_auc")}
    else:
        caps["url_model"] = {"status": "unavailable", "note": "URL rules only"}
    try:
        caps["ocr"] = {"status": "ready", "engine": get_ocr_engine().name}
    except OCRUnavailable:
        caps["ocr"] = {"status": "unavailable"}
    caps["qr_decoder"] = {"status": "ready", "engine": "opencv"}
    idx = get_index()
    caps["rag"] = {"status": "ready", "chunks": len(idx.chunks), "backend": idx.backend, "embedder": idx.embedder.name}
    llm = get_llm()
    caps["llm_explanations"] = {"status": "ready", "provider": llm.name} if llm else {
        "status": "disabled", "note": "Grounded template explanations are used"}
    caps["url_reputation"] = {"status": "ready" if reputation.is_configured() else "not_configured"}
    caps["audio"] = {"status": "unavailable", "note": "Voice analysis is planned for Phase 2"}
    caps["voice_authenticity"] = {"status": "unavailable", "note": "Deepfake detection is not available"}

    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": {"status": "ready" if db_ok else "error",
            "dialect": engine.dialect.name}, "environment": get_settings().sentinel_env, "capabilities": caps}
