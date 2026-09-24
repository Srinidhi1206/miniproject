"""QR decoding with OpenCV.

The decoder only *extracts* the payload. Whether the payload is dangerous is
decided downstream by the URL analyzer / UPI analyzer / text analyzer.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass
class QRDecodeResult:
    payloads: list[str]
    attempts: int


_detector = cv2.QRCodeDetector()


def _variants(img: np.ndarray):
    """Pre-processing variants that rescue photos of printed/on-screen QR codes."""
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    yield gray
    h, w = gray.shape
    if max(h, w) < 600:  # small screenshots: upscale so modules are > 2px
        yield cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_NEAREST)
    if max(h, w) > 1600:
        scale = 1600 / max(h, w)
        yield cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    yield cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5)
    _, otsu = cv2.threshold(cv2.GaussianBlur(gray, (3, 3), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    yield otsu
    yield cv2.bitwise_not(gray)  # inverted (light-on-dark) codes


def decode_qr(image: Image.Image) -> QRDecodeResult:
    arr = np.array(image.convert("RGB"))
    attempts = 0
    for variant in _variants(arr):
        attempts += 1
        try:
            ok, decoded, _, _ = _detector.detectAndDecodeMulti(variant)
        except cv2.error:
            ok, decoded = False, ()
        payloads = [d for d in (decoded or ()) if d]
        if ok and payloads:
            return QRDecodeResult(payloads=list(dict.fromkeys(payloads)), attempts=attempts)
        try:
            single, _, _ = _detector.detectAndDecode(variant)
        except cv2.error:
            single = ""
        if single:
            return QRDecodeResult(payloads=[single], attempts=attempts)
    return QRDecodeResult(payloads=[], attempts=attempts)


def classify_payload(payload: str) -> str:
    p = payload.strip().lower()
    if p.startswith("upi://"):
        return "upi"
    if p.startswith(("http://", "https://", "www.")):
        return "url"
    if p.startswith("wifi:"):
        return "wifi"
    if "." in p and " " not in p and len(p) < 300 and "/" in p:
        return "url"
    return "text"
