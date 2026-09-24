"""Optional URL reputation lookup (Google Safe Browsing v4 Lookup API).

Only runs when URL_REPUTATION_API_KEY is set. The URL string is sent to the
reputation API; SENTINEL itself never requests the suspicious URL. When the
key is missing or the API fails, the result is reported as "not checked" —
never as "clean".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.schemas.analysis import Evidence

log = logging.getLogger("sentinel.reputation")
ENDPOINT = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


@dataclass
class ReputationResult:
    checked: bool
    malicious: bool = False
    threats: list[str] | None = None
    note: str | None = None


def is_configured() -> bool:
    return bool(get_settings().url_reputation_api_key)


def check_url(url: str, timeout: float = 4.0) -> ReputationResult:
    key = get_settings().url_reputation_api_key
    if not key:
        return ReputationResult(checked=False, note="URL reputation service not configured.")
    body = {
        "client": {"clientId": "sentinel", "clientVersion": "0.1"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        resp = httpx.post(ENDPOINT, params={"key": key}, json=body, timeout=timeout)
        resp.raise_for_status()
        matches = resp.json().get("matches", [])
    except Exception as exc:
        log.warning("Reputation lookup failed: %s", type(exc).__name__)
        return ReputationResult(checked=False, note="URL reputation service unavailable right now.")
    threats = sorted({m.get("threatType", "UNKNOWN") for m in matches})
    return ReputationResult(checked=True, malicious=bool(matches), threats=threats)


def reputation_evidence(res: ReputationResult) -> list[Evidence]:
    if not res.checked:
        return []
    if res.malicious:
        return [Evidence(code="REPUTATION_MALICIOUS", label="Listed as dangerous by Google Safe Browsing",
                         severity="critical", weight=60, source="reputation",
                         detail="Threat types: " + ", ".join(res.threats or []))]
    return [Evidence(code="REPUTATION_CLEAN", label="Not on Google Safe Browsing's threat lists", severity="info",
                     weight=0, source="reputation",
                     detail="New scam sites often aren't listed yet, so this is not proof of safety.")]
