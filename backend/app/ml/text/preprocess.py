"""Text normalisation shared by training and inference.

The same function MUST be used in both places (it is part of the persisted
sklearn pipeline), otherwise the model sees a different distribution at
inference time.

Concrete values (URLs, amounts, phone numbers) are replaced with placeholder
tokens so the model learns *patterns* ("asks for money", "contains a link")
rather than memorising specific numbers or domains.
"""

from __future__ import annotations

import re
import unicodedata

URL_RE = re.compile(
    r"""(?xi)
    \b(
      (?:https?://|www\.)[^\s<>"']+                      # explicit scheme / www
      |
      (?:[a-z0-9-]+\.)+(?:com|in|net|org|co|info|xyz|top|online|site|shop|link|live|
         click|help|support|io|me|ly|gl|gd|at|to|app|dev|ai|us|uk|biz|cc|tk|ml|ga|cf|gq|buzz|icu|loan|work)
      (?:/[^\s<>"']*)?                                    # bare domain with optional path
    )""",
)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
MONEY_RE = re.compile(r"(?i)(?:rs\.?|inr|₹|\$|£|€|usd|gbp)\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:rs|inr|rupees|lakh|lakhs|crore|usd|dollars|gbp)\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){9,11}\d(?!\d)|\b\d{4,5}x{2,}\d{2,}\b", re.I)
NUM_RE = re.compile(r"\d+")
WS_RE = re.compile(r"\s+")


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = URL_RE.sub(" urltoken ", text)
    text = EMAIL_RE.sub(" emailtoken ", text)
    text = MONEY_RE.sub(" moneytoken ", text)
    text = PHONE_RE.sub(" phonetoken ", text)
    text = NUM_RE.sub(" numtoken ", text)
    text = re.sub(r"[^\w\s!?₹%]", " ", text)
    return WS_RE.sub(" ", text).strip()


def extract_urls(text: str, limit: int = 5) -> list[str]:
    """Return unique URL-like strings in order of appearance (trailing punctuation trimmed)."""
    seen: list[str] = []
    for m in URL_RE.finditer(EMAIL_RE.sub(" ", text)):
        candidate = m.group(0).rstrip(".,;:!?)]}'\"")
        if candidate.lower() not in (s.lower() for s in seen):
            seen.append(candidate)
        if len(seen) >= limit:
            break
    return seen
