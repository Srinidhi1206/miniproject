"""SentinelAgent — the orchestration layer.

The agent is a COORDINATOR, not a classifier. It:
  1. identifies what kind of artifact it is holding,
  2. selects the specialist tools for that artifact (routing table below),
  3. runs them, collecting evidence and any NEW artifacts they produce
     (OCR text, decoded QR payloads, extracted URLs),
  4. repeats until no artifacts remain,
  5. hands all evidence to the RiskEngine, then to the ExplanationService.

Every tool call is recorded as an `AgentStep` (tool, stage, timing, status)
and streamed to the client, so the progress UI reflects real work.

The planner is deterministic on purpose: the security verdict must be
reproducible and must not depend on an LLM. An LLM planner could replace
`ROUTES` later without changing the tools.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from PIL import Image

from app.core.errors import SentinelError
from app.ml.text.indicators import detect_indicators
from app.ml.text.model import ModelUnavailable, get_text_detector
from app.ml.text.preprocess import extract_urls, normalise
from app.ml.url.analyzer import analyze_url
from app.ml.url.parsing import parse_url
from app.rag.explainer import explain
from app.risk import engine as risk
from app.risk.recommendations import recommend
from app.schemas.analysis import (
    AgentStep, AnalysisResult, Channel, ComponentScore, Evidence, ExtractedContent, InputType,
)
from app.services import reputation
from app.services.ocr import OCRUnavailable, get_ocr_engine
from app.services.qr import classify_payload, decode_qr
from app.services.upi import parse_upi, upi_evidence

log = logging.getLogger("sentinel.agent")

Emit = Callable[[dict], None]
MAX_URLS = 5
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4, "positive": 5}


@dataclass
class Artifact:
    kind: str  # text | url | image | qr_image | upi | qr_other
    value: object
    origin: str = "user"  # user | ocr | qr


@dataclass
class RunContext:
    input_type: InputType
    channel: Channel | None
    emit: Emit
    steps: list[AgentStep] = field(default_factory=list)
    components: list[ComponentScore] = field(default_factory=list)
    extracted: ExtractedContent = field(default_factory=ExtractedContent)
    limitations: list[str] = field(default_factory=list)
    seen_urls: set[str] = field(default_factory=set)
    stages_started: set[str] = field(default_factory=set)

    def stage(self, name: str) -> None:
        if name not in self.stages_started:
            self.stages_started.add(name)
            self.emit({"type": "stage", "stage": name})

    def record(self, tool: str, stage: str, label: str, started: float, status: str = "done", note: str | None = None):
        step = AgentStep(tool=tool, stage=stage, label=label, status=status,
                         duration_ms=int((time.perf_counter() - started) * 1000), note=note)
        self.steps.append(step)
        self.emit({"type": "step", "step": step.model_dump()})


def _mask_long_numbers(text: str) -> str:
    """Mask digit runs ≥ 6 (phone / account / reference numbers) in stored previews."""
    return re.sub(r"\d(?:[\s-]?\d){5,}", lambda m: "•" * min(len(m.group(0)), 10), text)


def make_preview(text: str, limit: int = 160) -> str:
    one_line = re.sub(r"\s+", " ", text).strip()
    one_line = _mask_long_numbers(one_line)
    return one_line[:limit] + ("…" if len(one_line) > limit else "")


class SentinelAgent:
    """Routing table: artifact kind -> tools, in order."""

    ROUTES: dict[str, list[str]] = {
        "image": ["qr_scanner", "ocr_reader"],     # screenshots may contain a QR code as well as text
        "qr_image": ["qr_decoder"],
        "text": ["text_classifier", "url_extractor"],
        "url": ["url_analyzer"],
        "upi": ["upi_analyzer"],
        "qr_other": ["qr_payload_describer"],
    }

    def __init__(self) -> None:
        self.tools: dict[str, tuple[str, str, Callable[[Artifact, RunContext], list[Artifact]]]] = {
            "qr_decoder": ("extract", "Decoding QR code", self._qr_decoder),
            "qr_scanner": ("extract", "Looking for QR codes", self._qr_scanner),
            "ocr_reader": ("extract", "Reading text from image (OCR)", self._ocr_reader),
            "text_classifier": ("analyze", "Checking message for scam patterns", self._text_classifier),
            "url_extractor": ("extract", "Extracting links", self._url_extractor),
            "url_analyzer": ("analyze", "Analyzing link", self._url_analyzer),
            "upi_analyzer": ("analyze", "Inspecting UPI payment request", self._upi_analyzer),
            "qr_payload_describer": ("analyze", "Inspecting QR contents", self._qr_other),
        }

    # ------------------------------------------------------------------ run
    def run(self, input_type: InputType, payload: object, *, channel: Channel | None = None,
            emit: Emit | None = None, analysis_id: str | None = None) -> AnalysisResult:
        started = time.perf_counter()
        ctx = RunContext(input_type=input_type, channel=channel, emit=emit or (lambda _e: None))
        ctx.stage("validate")
        t = time.perf_counter()
        initial = self._initial_artifact(input_type, payload, ctx)
        ctx.record("input_router", "validate", f"Input identified as {input_type.value.lower()}", t,
                   note=f"route: {' → '.join(self.ROUTES[initial.kind])}")

        queue = [initial]
        while queue:
            art = queue.pop(0)
            for tool_name in self.ROUTES[art.kind]:
                stage, label, fn = self.tools[tool_name]
                ctx.stage(stage)
                t = time.perf_counter()
                try:
                    produced = fn(art, ctx)
                except SentinelError:
                    raise
                except Exception:
                    log.exception("Tool %s failed", tool_name)
                    ctx.record(tool_name, stage, label, t, status="failed", note="internal error")
                    ctx.limitations.append(f"The {label.lower()} step failed, so its evidence is missing.")
                    continue
                queue.extend(produced)

        if not ctx.components:
            raise SentinelError("NO_CONTENT", "We couldn't find anything to analyze in that input.", 422,
                                hint="Try a clearer screenshot, or paste the message text directly.")

        ctx.stage("risk")
        t = time.perf_counter()
        breakdown = risk.combine(ctx.components)
        level = risk.band(breakdown.final_score)
        ctx.record("risk_engine", "risk", "Combining evidence into a risk score", t,
                   note=f"{breakdown.final_score}/100 ({level.value})")

        all_ev = [e for c in breakdown.components for e in c.evidence]
        findings, reassurances = self._split_evidence(all_ev)
        has_risky_url = any(c.component == "url" and c.score >= 60 for c in breakdown.components)

        ctx.stage("explain")
        t = time.perf_counter()
        explanation = explain(input_type=input_type, channel=channel.value if channel else None, level=level,
                              score=breakdown.final_score, components=breakdown.components,
                              findings=findings, reassurances=reassurances)
        recs = recommend(level, findings, has_risky_url)
        ctx.record("explanation_service", "explain", "Preparing explanation", t,
                   note=f"{explanation.generated_by}; {len(explanation.sources)} guidance sources")

        if not reputation.is_configured() and any(c.component == "url" for c in breakdown.components):
            ctx.limitations.append("Live URL reputation lookup is not configured; links were judged on their structure only.")

        preview_src = ctx.extracted.text or ctx.extracted.qr_payload or (ctx.extracted.urls[0] if ctx.extracted.urls else "")
        return AnalysisResult(
            id=analysis_id or uuid.uuid4().hex, created_at=datetime.now(timezone.utc),
            input_type=input_type, channel=channel, input_preview=make_preview(str(preview_src)),
            classification=risk.classify(level), verdict=risk.VERDICTS[level],
            risk_score=breakdown.final_score, risk_level=level,
            confidence=risk.primary_confidence(breakdown.components),
            findings=findings, reassurances=reassurances, recommendations=recs, explanation=explanation,
            extracted=ctx.extracted, breakdown=breakdown, trace=ctx.steps, limitations=ctx.limitations,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ------------------------------------------------------------- helpers
    def _initial_artifact(self, input_type: InputType, payload: object, ctx: RunContext) -> Artifact:
        if input_type == InputType.TEXT:
            ctx.extracted.text, ctx.extracted.text_source = str(payload), "user"
            return Artifact("text", payload)
        if input_type == InputType.URL:
            return Artifact("url", payload)
        if input_type == InputType.IMAGE:
            return Artifact("image", payload)
        if input_type == InputType.QR:
            return Artifact("qr_image", payload)
        raise SentinelError("CAPABILITY_UNAVAILABLE", "This input type isn't supported yet.", 501)

    @staticmethod
    def _split_evidence(evidence: list[Evidence]) -> tuple[list[Evidence], list[Evidence]]:
        reassuring_codes = {"REPUTATION_CLEAN"}
        findings: dict[str, Evidence] = {}
        reassurances: dict[str, Evidence] = {}
        for e in evidence:
            target = reassurances if (e.severity == "positive" or e.code in reassuring_codes) else findings
            if e.code not in target or e.weight > target[e.code].weight:
                target[e.code] = e
        order = lambda e: (_SEVERITY_RANK[e.severity], -e.weight)  # noqa: E731
        return sorted(findings.values(), key=order), sorted(reassurances.values(), key=order)

    def _add_url(self, raw: str, origin: str, ctx: RunContext) -> list[Artifact]:
        key = raw.lower().rstrip("/")
        if key in ctx.seen_urls or len(ctx.seen_urls) >= MAX_URLS:
            return []
        ctx.seen_urls.add(key)
        return [Artifact("url", raw, origin)]

    # --------------------------------------------------------------- tools
    def _qr_decoder(self, art: Artifact, ctx: RunContext) -> list[Artifact]:
        t = time.perf_counter()
        result = decode_qr(art.value)  # type: ignore[arg-type]
        if not result.payloads:
            ctx.record("qr_decoder", "extract", "Decoding QR code", t, status="failed", note="no QR code found")
            raise SentinelError("QR_NOT_FOUND", "We couldn't detect a QR code in this image.", 422,
                                hint="Crop the image around the QR code, make sure it's in focus, and try again.")
        ctx.record("qr_decoder", "extract", "Decoding QR code", t,
                   note=f"{len(result.payloads)} code(s) decoded after {result.attempts} pass(es)")
        return self._route_payloads(result.payloads, ctx)

    def _qr_scanner(self, art: Artifact, ctx: RunContext) -> list[Artifact]:
        t = time.perf_counter()
        result = decode_qr(art.value)  # type: ignore[arg-type]
        if not result.payloads:
            ctx.record("qr_scanner", "extract", "Looking for QR codes", t, status="skipped", note="no QR code in image")
            return []
        ctx.record("qr_scanner", "extract", "Looking for QR codes", t, note=f"found {len(result.payloads)} QR code(s)")
        return self._route_payloads(result.payloads, ctx)

    def _route_payloads(self, payloads: list[str], ctx: RunContext) -> list[Artifact]:
        out: list[Artifact] = []
        for payload in payloads[:3]:
            kind = classify_payload(payload)
            ctx.extracted.qr_payload = ctx.extracted.qr_payload or payload
            ctx.extracted.qr_payload_kind = ctx.extracted.qr_payload_kind or kind  # type: ignore[assignment]
            if kind == "upi":
                out.append(Artifact("upi", payload, "qr"))
            elif kind == "url":
                out.extend(self._add_url(payload, "qr", ctx))
            elif kind == "text":
                out.append(Artifact("text", payload, "qr"))
            else:
                out.append(Artifact("qr_other", payload, "qr"))
        return out

    def _ocr_reader(self, art: Artifact, ctx: RunContext) -> list[Artifact]:
        t = time.perf_counter()
        try:
            engine = get_ocr_engine()
        except OCRUnavailable:
            ctx.record("ocr_reader", "extract", "Reading text from image (OCR)", t, status="failed", note="OCR engine unavailable")
            ctx.limitations.append("Text recognition (OCR) is unavailable, so text in the image was not analyzed.")
            return []
        result = engine.read(art.value)  # type: ignore[arg-type]
        if len(result.text.strip()) < 4:
            ctx.record("ocr_reader", "extract", "Reading text from image (OCR)", t, status="skipped", note="no readable text")
            return []
        ctx.extracted.text, ctx.extracted.text_source = result.text, "ocr"
        ctx.extracted.ocr_confidence = round(result.confidence, 3)
        if result.confidence < 0.8:
            ctx.limitations.append(f"Some text in the image was hard to read (OCR confidence {result.confidence:.0%}); "
                                   "results may miss details. Pasting the text directly is more accurate.")
        ctx.record("ocr_reader", "extract", "Reading text from image (OCR)", t,
                   note=f"{result.lines} lines, confidence {result.confidence:.0%}")
        return [Artifact("text", result.text, "ocr")]

    def _text_classifier(self, art: Artifact, ctx: RunContext) -> list[Artifact]:
        text = str(art.value)
        t = time.perf_counter()
        try:
            model_out = get_text_detector().predict(text)
        except ModelUnavailable:
            model_out = None
            ctx.limitations.append("The text ML model is not loaded; the verdict relies on rule-based indicators only.")
        evidence = detect_indicators(text, normalise(text))
        if model_out and model_out.probability >= 0.8:
            evidence.append(Evidence(
                code="TEXT_MODEL_MATCH", label="Wording closely matches known scam messages", severity="high", weight=0,
                source="text_model",
                detail=f"The ML classifier estimates a {model_out.probability:.0%} probability that this is a scam, "
                       "based on patterns learned from thousands of labelled messages.",
            ))
        if len(text) < 25:
            ctx.limitations.append("The message is very short, so there is less for the analysis to go on.")
        subject = make_preview(text, 80)
        comp = risk.score_text(subject, model_out, evidence)
        ctx.components.append(comp)
        note = f"P(scam)={model_out.probability:.2f}" if model_out else "rules only"
        ctx.record("text_classifier", "analyze", "Checking message for scam patterns", t,
                   note=f"{note}; {len([e for e in evidence if e.weight > 0])} indicators")
        return []

    def _url_extractor(self, art: Artifact, ctx: RunContext) -> list[Artifact]:
        t = time.perf_counter()
        found = extract_urls(str(art.value), limit=MAX_URLS)
        out: list[Artifact] = []
        for u in found:
            out.extend(self._add_url(u, art.origin if art.origin != "user" else "text", ctx))
        status = "done" if found else "skipped"
        ctx.record("url_extractor", "extract", "Extracting links", t, status=status,
                   note=f"{len(found)} link(s) found" if found else "no links")
        return out

    def _url_analyzer(self, art: Artifact, ctx: RunContext) -> list[Artifact]:
        raw = str(art.value)
        t = time.perf_counter()
        try:
            parsed = parse_url(raw)
        except SentinelError:
            if ctx.input_type == InputType.URL:
                raise  # the user's own input is invalid -> tell them
            ctx.record("url_analyzer", "analyze", "Analyzing link", t, status="skipped", note="not a valid web link")
            return []
        ctx.extracted.urls.append(parsed.original)
        analysis = analyze_url(parsed)
        evidence = list(analysis.evidence)
        for e in evidence:
            if e.excerpt is None:
                e.excerpt = parsed.host
        if analysis.model and analysis.model.probability >= 0.8 and not analysis.trusted:
            evidence.append(Evidence(
                code="URL_MODEL_MATCH", label=f"Domain name resembles known phishing domains ({parsed.registered_domain})",
                severity="high", weight=0, source="url_model",
                detail=f"The URL model estimates a {analysis.model.probability:.0%} probability of phishing from the "
                       "domain's characters and structure.", excerpt=parsed.host,
            ))
        if art.origin == "qr":
            evidence.append(Evidence(code="QR_URL", label=f"QR code opens a website ({parsed.host})", severity="info",
                                     weight=0, source="qr_decoder", excerpt=parsed.original[:120],
                                     detail="Always check where a QR code leads before opening it."))
        rep = reputation.check_url(parsed.normalised) if reputation.is_configured() else None
        if rep is not None:
            evidence.extend(reputation.reputation_evidence(rep))
            if not rep.checked and rep.note:
                ctx.limitations.append(rep.note)
        comp = risk.score_url(parsed.original[:200], analysis.model, evidence)
        ctx.components.append(comp)
        p = f"P(phishing)={analysis.model.probability:.2f}" if analysis.model else "rules only"
        ctx.record("url_analyzer", "analyze", f"Analyzing link {parsed.host}", t,
                   note=f"{p}; {len([e for e in evidence if e.weight > 0])} risk signals" + ("; reputation checked" if rep and rep.checked else ""))
        return []

    def _upi_analyzer(self, art: Artifact, ctx: RunContext) -> list[Artifact]:
        t = time.perf_counter()
        upi = parse_upi(str(art.value)) or {}
        ctx.extracted.upi = upi
        evidence = upi_evidence(upi)
        comp = risk.score_upi(f"UPI payment to {upi.get('payee_vpa') or 'unknown'}", evidence)
        ctx.components.append(comp)
        ctx.record("upi_analyzer", "analyze", "Inspecting UPI payment request", t,
                   note=f"payee {upi.get('payee_vpa') or 'unknown'}" + (f", amount ₹{upi['amount']}" if upi.get("amount") else ""))
        return []

    def _qr_other(self, art: Artifact, ctx: RunContext) -> list[Artifact]:
        t = time.perf_counter()
        payload = str(art.value)
        kind = classify_payload(payload)
        label = "QR code contains Wi-Fi network details" if kind == "wifi" else "QR code contains data that isn't a link or payment"
        ev = [Evidence(code="QR_DATA", label=label, severity="info", weight=0, source="qr_decoder", excerpt=payload[:80])]
        ctx.components.append(risk.score_text(make_preview(payload, 80), None, ev))
        ctx.record("qr_payload_describer", "analyze", "Inspecting QR contents", t, note=kind)
        return []


_agent: SentinelAgent | None = None


def get_agent() -> SentinelAgent:
    global _agent
    if _agent is None:
        _agent = SentinelAgent()
    return _agent


def warm_up() -> dict[str, str]:
    """Load models/indexes at startup so the first scan is fast. Returns component status."""
    status: dict[str, str] = {}
    try:
        status["text_model"] = get_text_detector().version
    except ModelUnavailable as exc:
        status["text_model"] = f"unavailable: {exc}"
    from app.ml.url.analyzer import get_url_model
    m = get_url_model()
    status["url_model"] = m.version if m else "unavailable (rules only)"
    from app.rag.index import get_index
    idx = get_index()
    status["rag_index"] = f"{len(idx.chunks)} chunks ({idx.backend})"
    try:
        status["ocr"] = get_ocr_engine().name
    except OCRUnavailable as exc:
        status["ocr"] = f"unavailable: {exc}"
    return status


__all__ = ["SentinelAgent", "get_agent", "warm_up", "make_preview", "Image"]
