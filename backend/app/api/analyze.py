"""Analysis endpoints.

Each endpoint returns the final AnalysisResult as JSON, or — with
`?stream=true` — an NDJSON stream of real progress events:

  {"type":"stage","stage":"extract"}
  {"type":"step","step":{...AgentStep}}
  {"type":"result","result":{...AnalysisResult}}
  {"type":"error","error":{"code":..., "message":...}}

Input validation (size, type, decodability) happens BEFORE the stream
starts, so invalid input always gets a normal HTTP error status.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Callable

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import get_agent
from app.api.deps import optional_client_id
from app.core.errors import SentinelError
from app.core.ratelimit import rate_limit
from app.core.security import load_image, read_upload, redact_for_log, validate_text
from app.db.session import SessionLocal
from app.ml.url.parsing import parse_url
from app.schemas.analysis import AnalysisResult, Channel, InputType, TextAnalyzeRequest, UrlAnalyzeRequest
from app.services.audio import audio_unavailable
from app.services.persistence import save_analysis

log = logging.getLogger("sentinel.api.analyze")
router = APIRouter(prefix="/api/analyze", tags=["analyze"], dependencies=[Depends(rate_limit)])


def _execute(input_type: InputType, payload, channel: Channel | None, client_id: str | None,
             emit: Callable[[dict], None] | None = None) -> AnalysisResult:
    result = get_agent().run(input_type, payload, channel=channel, emit=emit)
    db = SessionLocal()
    try:
        save_analysis(db, result, client_id)
    except Exception:  # storage failure must not hide the result from the user
        log.exception("Failed to persist analysis %s", result.id)
        result.limitations.append("This result couldn't be saved to your history.")
    finally:
        db.close()
    return result


def _respond(stream: bool, input_type: InputType, payload, channel: Channel | None, client_id: str | None):
    if not stream:
        return _execute(input_type, payload, channel, client_id)

    events: queue.Queue = queue.Queue()

    def worker():
        try:
            result = _execute(input_type, payload, channel, client_id, emit=events.put)
            events.put({"type": "result", "result": result.model_dump(mode="json")})
        except SentinelError as exc:
            events.put({"type": "error", "status": exc.status_code, **exc.to_dict()})
        except Exception:
            log.exception("Streaming analysis failed")
            events.put({"type": "error", "status": 500, "error": {
                "code": "INTERNAL_ERROR", "message": "Something went wrong during analysis. Please try again."}})
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True, name="sentinel-analysis").start()

    def gen():
        while (item := events.get()) is not None:
            yield json.dumps(item, ensure_ascii=False, default=str) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.post("/text", response_model=AnalysisResult, summary="Analyse a message (SMS, WhatsApp, email, job offer)")
def analyze_text(body: TextAnalyzeRequest, stream: bool = Query(False), client_id: str | None = Depends(optional_client_id)):
    text = validate_text(body.text)
    log.info("analyze text channel=%s len=%d preview=%s", body.channel.value, len(text), redact_for_log(text))
    return _respond(stream, InputType.TEXT, text, body.channel, client_id)


@router.post("/url", response_model=AnalysisResult, summary="Analyse a link without visiting it")
def analyze_url(body: UrlAnalyzeRequest, stream: bool = Query(False), client_id: str | None = Depends(optional_client_id)):
    parsed = parse_url(body.url)  # validate up front -> friendly 400
    log.info("analyze url host=%s", parsed.host)
    return _respond(stream, InputType.URL, parsed.original, None, client_id)


@router.post("/image", response_model=AnalysisResult, summary="Analyse a screenshot (OCR + QR + text + links)")
async def analyze_image(file: UploadFile = File(...), channel: Channel = Form(Channel.other), stream: bool = Query(False),
                        client_id: str | None = Depends(optional_client_id)):
    image = load_image(await read_upload(file))
    log.info("analyze image %sx%s", *image.size)
    return _respond(stream, InputType.IMAGE, image, channel, client_id)


@router.post("/qr", response_model=AnalysisResult, summary="Decode a QR code image and analyse its destination")
async def analyze_qr(file: UploadFile = File(...), stream: bool = Query(False),
                     client_id: str | None = Depends(optional_client_id)):
    image = load_image(await read_upload(file))
    log.info("analyze qr %sx%s", *image.size)
    return _respond(stream, InputType.QR, image, None, client_id)


@router.post("/audio", summary="Voice analysis (not available in the current configuration)",
             responses={501: {"description": "Capability unavailable"}})
async def analyze_audio(file: UploadFile = File(...)):
    raise audio_unavailable()
