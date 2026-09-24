"""Input hardening helpers: upload validation, text sanitisation, safe logging.

Uploaded files are never executed or written to disk under a user-supplied
name. Images are validated by magic bytes AND by fully decoding them with
Pillow before any analysis touches them.
"""

from __future__ import annotations

import io
import re
import unicodedata

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import SentinelError, file_too_large, unsupported_file

IMAGE_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "BMP": "image/bmp", "GIF": "image/gif"}
ACCEPTED_IMAGES = "PNG, JPG, WEBP, BMP, GIF"

# Pillow's decompression-bomb guard: refuse anything above ~40 megapixels.
Image.MAX_IMAGE_PIXELS = 40_000_000

_MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"\xff\xd8\xff", "JPEG"),
    (b"GIF87a", "GIF"),
    (b"GIF89a", "GIF"),
    (b"BM", "BMP"),
]

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sniff_image_format(data: bytes) -> str | None:
    for magic, fmt in _MAGIC:
        if data.startswith(magic):
            return fmt
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return None


async def read_upload(file: UploadFile) -> bytes:
    """Read an upload with a hard size cap (never trusts Content-Length)."""
    limit = get_settings().max_upload_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise file_too_large(get_settings().max_upload_mb)
    if not data:
        raise SentinelError("EMPTY_FILE", "The uploaded file is empty.", 400)
    return data


def load_image(data: bytes) -> Image.Image:
    """Validate and decode an image. Returns an RGB Pillow image."""
    if sniff_image_format(data) is None:
        raise unsupported_file(ACCEPTED_IMAGES)
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()  # structural integrity check
        img = Image.open(io.BytesIO(data))
        img.load()
    except Image.DecompressionBombError:
        raise SentinelError("IMAGE_TOO_LARGE", "That image's dimensions are too large to analyse safely.", 413)
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise SentinelError("CORRUPT_IMAGE", "We couldn't read that image. It may be damaged or not a real image.", 400)
    if img.format not in IMAGE_FORMATS:
        raise unsupported_file(ACCEPTED_IMAGES)
    if getattr(img, "n_frames", 1) > 1:
        img.seek(0)
    return img.convert("RGB")


def clean_text(text: str) -> str:
    """Normalise user text: NFKC, strip control chars, collapse runaway whitespace."""
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL_CHARS.sub("", text)
    text = re.sub(r"[ \t]{3,}", "  ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def validate_text(text: str, *, field: str = "text", min_chars: int = 3) -> str:
    text = clean_text(text or "")
    limit = get_settings().max_text_chars
    if len(text) < min_chars:
        raise SentinelError("TEXT_TOO_SHORT", "Please paste the full message so SENTINEL has enough to analyse.", 400)
    if len(text) > limit:
        raise SentinelError("TEXT_TOO_LONG", f"That's longer than the {limit:,}-character limit.", 413,
                            hint="Paste the most relevant part of the message.")
    return text


def redact_for_log(text: str, keep: int = 24) -> str:
    """Never log full user content — just a short, digit-masked prefix."""
    masked = re.sub(r"\d", "#", text[:keep])
    return masked + ("…" if len(text) > keep else "")
