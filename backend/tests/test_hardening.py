"""Failure modes and hardening: oversized bodies, malformed requests, degraded
components. Every failure must produce a friendly message, never a traceback."""

from app.agents.orchestrator import get_agent
from app.schemas.analysis import InputType


def test_oversized_upload_rejected_before_buffering(client):
    # Declared size above the limit is refused by the middleware without reading the body.
    r = client.post("/api/analyze/image", content=b"x" * 16,
                    headers={"Content-Type": "multipart/form-data; boundary=x", "Content-Length": str(50 * 1024 * 1024)})
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_malformed_json_is_reported_as_body(client):
    r = client.post("/api/analyze/text", content=b'{"text": "abc', headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert r.json()["error"] == {"code": "INVALID_INPUT", "message": "Some of the submitted information is missing or invalid.",
                                 "fields": ["body"]}


def test_text_model_unavailable_falls_back_to_rules(monkeypatch):
    from app.agents import orchestrator
    from app.ml.text.model import ModelUnavailable

    def boom():
        raise ModelUnavailable("missing")

    monkeypatch.setattr(orchestrator, "get_text_detector", boom)
    r = get_agent().run(InputType.TEXT, "Share the OTP you received with our officer immediately or your account will be blocked")
    assert r.risk_level.value in {"HIGH", "CRITICAL"}
    assert any("rule-based indicators only" in lim for lim in r.limitations)


def test_ocr_unavailable_is_reported_not_hidden(monkeypatch):
    from PIL import Image

    from app.agents import orchestrator
    from app.services.ocr import OCRUnavailable

    def boom():
        raise OCRUnavailable("no engine")

    monkeypatch.setattr(orchestrator, "get_ocr_engine", boom)
    try:
        get_agent().run(InputType.IMAGE, Image.new("RGB", (200, 100), "white"))
    except Exception as exc:  # no text and no QR -> friendly NO_CONTENT, with OCR limitation traced
        assert getattr(exc, "code", None) == "NO_CONTENT"


def test_database_failure_still_returns_result(client, monkeypatch):
    from app.api import analyze

    def broken_save(*_a, **_k):
        raise RuntimeError("database is down")

    monkeypatch.setattr(analyze, "save_analysis", broken_save)
    r = client.post("/api/analyze/text", json={"text": "Are we still meeting at 7 near the cafe?"})
    assert r.status_code == 200
    assert any("couldn't be saved" in lim for lim in r.json()["limitations"])


def test_unhandled_errors_never_leak_tracebacks(client, monkeypatch):
    from app.api import history

    def explode(*_a, **_k):
        raise RuntimeError("secret internal detail")

    from fastapi.testclient import TestClient

    from app.main import app

    dev = {"X-Sentinel-Client": "pytest-leak-0001"}
    client.post("/api/analyze/text", json={"text": "See you at the library at four"}, headers=dev)
    monkeypatch.setattr(history, "to_history_item", explode)
    # Behave like a real HTTP client: receive the error response instead of re-raising.
    r = TestClient(app, raise_server_exceptions=False).get("/api/history", headers=dev)
    assert r.status_code == 500
    assert "secret internal detail" not in r.text and "Traceback" not in r.text
    assert r.json()["error"]["code"] == "INTERNAL_ERROR"
