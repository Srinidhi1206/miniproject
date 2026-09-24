"""Generate synthetic test images (QR codes, fake screenshots) in memory.

All content is fictional. Used by pytest and by scripts/demo_samples.py.
"""

from __future__ import annotations

import io
import textwrap

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def qr_png(payload: str, scale: int = 8, border: int = 4) -> bytes:
    encoder = cv2.QRCodeEncoder.create()
    matrix = encoder.encode(payload)
    img = cv2.resize(matrix, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    img = cv2.copyMakeBorder(img, border * scale, border * scale, border * scale, border * scale,
                             cv2.BORDER_CONSTANT, value=255)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def _font(size: int):
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def chat_screenshot_png(message: str, sender: str = "+91 98XXX XX210", width: int = 720) -> bytes:
    """A plain chat-bubble style screenshot containing `message`."""
    font, small = _font(30), _font(24)
    lines = []
    for para in message.split("\n"):
        lines.extend(textwrap.wrap(para, width=36) or [""])
    line_h = 42
    h = 220 + line_h * len(lines)
    img = Image.new("RGB", (width, h), (236, 229, 221))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, 90], fill=(7, 94, 84))
    d.text((30, 28), sender, font=font, fill=(255, 255, 255))
    d.rounded_rectangle([24, 120, width - 60, 150 + line_h * len(lines)], radius=14, fill=(255, 255, 255))
    for i, line in enumerate(lines):
        d.text((44, 135 + i * line_h), line, font=font, fill=(20, 20, 20))
    d.text((width - 170, 160 + line_h * len(lines)), "10:42 AM", font=small, fill=(110, 110, 110))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def blank_png(color=(250, 250, 250), size=(400, 300)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def noise_png(size=(300, 300)) -> bytes:
    arr = (np.random.default_rng(0).random((size[1], size[0], 3)) * 255).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()
