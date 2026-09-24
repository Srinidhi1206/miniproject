"""OCR service.

Default engine: RapidOCR (PaddleOCR models exported to ONNX) — pip-installable,
no system binaries, runs on CPU. Wrapped behind `OCREngine` so Tesseract or a
cloud OCR can be swapped in without touching the agent.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import numpy as np
from PIL import Image

log = logging.getLogger("sentinel.ocr")


@dataclass
class OCRResult:
    text: str
    confidence: float  # mean line confidence 0..1
    lines: int


_MERGED_WORDS = re.compile(r"[A-Za-z]{11,}")
_URLISH = re.compile(r"(?:https?://|www\.)\S+|\S+\.(?:com|in|net|org|co|xyz|top|online|site|shop|info|link|ly|me)\S*", re.I)
_PLACEHOLDER = "⁣URL{}⁣"  # invisible separator, never produced by OCR
_PLACEHOLDER_RE = re.compile("⁣URL(\\d+)⁣")


_ACRONYMS = "OTP|KYC|UPI|PIN|CVV|ATM|PAN|SBI|HDFC|ICICI|SMS|EMI|GST|TRAI|CBI|RBI|NEFT|IFSC|URL|ID"
_ACRONYM_EDGE = re.compile(rf"(?<=[a-z])({_ACRONYMS})|({_ACRONYMS})(?=[a-z])")


def _ninja(piece: str) -> str:
    import wordninja  # small pure-Python unigram word splitter
    if len(piece) < 8 or not piece.isalpha():
        return piece
    parts = wordninja.split(piece)
    # Only accept splits into real-looking words; otherwise keep the original token.
    if len(parts) > 1 and all(len(p) > 1 or p.lower() in {"a", "i"} for p in parts):
        return " ".join(parts)
    return piece


def _split_merged(match: re.Match) -> str:
    """Split one merged token: known acronyms first ("theOTPsent"), then
    lower→Upper boundaries ("YourPaytm"), then dictionary splitting."""
    word = _ACRONYM_EDGE.sub(lambda m: f" {m.group(0)} ", match.group(0))
    word = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", word)
    return " ".join(_ninja(p) for p in word.split())


def postprocess(text: str) -> str:
    """Repair common OCR artefacts before analysis.

    * Re-join lines that were wrapped mid-URL or mid-hyphenated word
      ("http://bill-" + "update-power.online").
    * Split runs of letters the recognition model merged without spaces
      ("immediatelycontactour" -> "immediately contact our"). URLs are
      protected so domains are never altered.
    """
    # After "-", "/", "@", "_" always; after "." only when the next line continues in
    # lowercase (a domain like "power.\nonline"), so sentence breaks are kept.
    text = re.sub(r"(?<=[-/@_])\n(?=\S)|(?<=\.)\n(?=[a-z])", "", text)
    protected: list[str] = []

    def _protect(m: re.Match) -> str:
        protected.append(m.group(0))
        return _PLACEHOLDER.format(len(protected) - 1)

    text = _URLISH.sub(_protect, text)
    text = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z]{3,})", " ", text)  # "at9.30pm" -> "at 9.30pm"
    text = _MERGED_WORDS.sub(_split_merged, text)
    return _PLACEHOLDER_RE.sub(lambda m: protected[int(m.group(1))], text)


class OCREngine(Protocol):
    name: str

    def read(self, image: Image.Image) -> OCRResult: ...


class OCRUnavailable(RuntimeError):
    pass


class RapidOCREngine:
    name = "rapidocr-onnx"

    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR  # heavy import, deferred
        self._engine = RapidOCR()
        self._lock = threading.Lock()  # onnxruntime sessions are not re-entrant here

    def read(self, image: Image.Image) -> OCRResult:
        img = image.convert("RGB")
        # Cap resolution: OCR cost grows with pixels, and phone screenshots are huge.
        max_side = 2000
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side))
        arr = np.array(img)[:, :, ::-1]  # RGB -> BGR
        with self._lock:
            result, _ = self._engine(arr)
        if not result:
            return OCRResult(text="", confidence=0.0, lines=0)
        # result rows: [box, text, score]. Sort top-to-bottom, then left-to-right.
        rows = sorted(result, key=lambda r: (round(r[0][0][1] / 12), r[0][0][0]))
        lines, confs = [], []
        for _box, text, score in rows:
            if text and float(score) >= 0.5:
                lines.append(text.strip())
                confs.append(float(score))
        return OCRResult(text=postprocess("\n".join(lines)), confidence=float(np.mean(confs)) if confs else 0.0, lines=len(lines))


@lru_cache
def get_ocr_engine() -> OCREngine:
    try:
        engine = RapidOCREngine()
        log.info("OCR engine ready: %s", engine.name)
        return engine
    except Exception as exc:  # pragma: no cover - depends on environment
        raise OCRUnavailable(str(exc)) from exc
