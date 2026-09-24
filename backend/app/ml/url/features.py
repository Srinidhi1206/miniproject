"""Lexical host features for the URL model.

IMPORTANT design decision (docs/decisions.md, ADR-004): the model sees ONLY the
hostname (scheme and leading "www." removed). The PhiUSIIL training data
labels every legitimate URL as a bare `https://www.<domain>` homepage, so a
model trained on full URLs just learns "has a path or http:// => phishing".
Path, query and scheme signals are handled by transparent rules instead.
"""

from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np
import tldextract

from app.ml.url.lexicon import SENSITIVE_KEYWORDS, SUSPICIOUS_TLDS

_VOWELS = set("aeiou")
_tld = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)
NUMERIC_FEATURES = [
    "len", "labels", "hyphens", "digits_ratio", "entropy", "max_label_len", "consonant_run",
    "keyword_hits", "suspicious_tld", "has_digit_in_domain", "is_ip",
]


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def _max_consonant_run(s: str) -> int:
    run = best = 0
    for ch in s:
        if ch.isalpha() and ch not in _VOWELS:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def normalise_host(host: str) -> str:
    host = host.lower().strip().rstrip(".")
    host = re.sub(r"^[a-z]+://", "", host).split("/")[0].split(":")[0]
    return host[4:] if host.startswith("www.") else host


def model_key(host: str) -> str:
    """What the model actually scores: the registered domain (e.g. 'sbi-kyc-verify.co').

    Sub-domains are excluded because the training data's legitimate class has
    almost none, which made the model flag every real sub-domain
    (accounts.google.com). Sub-domain tricks are covered by URL rules instead.
    IP addresses are kept whole.
    """
    host = normalise_host(host)
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
        return host
    ext = _tld(host)
    return f"{ext.domain}.{ext.suffix}" if ext.suffix else host


def host_numeric_features(host: str) -> list[float]:
    labels = host.split(".")
    tld = labels[-1] if labels else ""
    domain_part = ".".join(labels[:-1])
    is_ip = bool(re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host))
    return [
        len(host),
        len(labels),
        host.count("-"),
        sum(ch.isdigit() for ch in host) / max(len(host), 1),
        _entropy(host),
        max((len(x) for x in labels), default=0),
        _max_consonant_run(host),
        sum(1 for kw in SENSITIVE_KEYWORDS if kw in host),
        float(tld in SUSPICIOUS_TLDS),
        float(any(ch.isdigit() for ch in domain_part)),
        float(is_ip),
    ]


def numeric_matrix(hosts) -> np.ndarray:
    """Module-level so it can be pickled inside a FunctionTransformer."""
    return np.array([host_numeric_features(model_key(h)) for h in hosts], dtype=float)
