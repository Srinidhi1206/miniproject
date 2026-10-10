"""What the analysed content is *about* (renewal, KYC, job offer, QR link ...).

Scenarios only choose wording and advice: how to verify a renewal, where KYC is
really done, that a QR destination was not opened. They are never evidence: they
add no findings and no points, so a scenario can't make anything look riskier.
"""

from __future__ import annotations

import re

_TEXT_SCENARIOS: dict[str, re.Pattern] = {
    "renewal": re.compile(r"\b(?:renew\w*|subscription|recharge|expir\w*|(?:bill|payment|premium)\s+(?:is\s+)?due|due\s+(?:date|on))\b", re.I),
    "kyc": re.compile(r"\b(?:re-?)?kyc\b", re.I),
    "otp": re.compile(r"\botp\b|\bone[\s-]?time\s+password\b|\bverification\s+code\b", re.I),
    "job": re.compile(r"\b(?:job|recruit\w*|hiring|offer\s+letter|work\s+from\s+home|part[\s-]?time)\b", re.I),
}


def detect_scenarios(text: str | None, qr_payload_kind: str | None = None) -> set[str]:
    found = {name for name, rx in _TEXT_SCENARIOS.items() if text and rx.search(text)}
    if qr_payload_kind == "url":
        found.add("qr_link")
    elif qr_payload_kind == "upi":
        found.add("upi_qr")
    return found
