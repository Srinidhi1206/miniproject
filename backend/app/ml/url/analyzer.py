"""URLRiskAnalyzer — lexical ML model + transparent rules. No network access.

Output is a list of `Evidence` plus the model's `ModelOutput`; the risk engine
turns those into a component score.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache

import joblib

from app.core.config import get_settings
from app.ml.url.features import model_key
from app.ml.url.lexicon import (
    ALLOWLIST, BRANDS, FREE_HOSTING, MESSAGING_DOMAINS, OFFICIAL_SUFFIXES, RISKY_EXTENSIONS,
    SENSITIVE_KEYWORDS, SHORTENERS, SUSPICIOUS_TLDS,
)
from app.ml.url.parsing import ParsedURL
from app.schemas.analysis import Evidence, FeatureContribution, ModelOutput

log = logging.getLogger("sentinel.ml.url")
ARTIFACT = "url_host_lr.joblib"
_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


@dataclass
class URLAnalysis:
    parsed: ParsedURL
    model: ModelOutput | None
    evidence: list[Evidence] = field(default_factory=list)
    trusted: bool = False


class URLHostModel:
    def __init__(self, path):
        bundle = joblib.load(path)
        self.pipeline = bundle["pipeline"]
        self.version: str = bundle["version"]
        self.metrics: dict = bundle.get("metrics", {})
        self.name = "domain-charngram-logreg"

    def predict(self, host: str) -> ModelOutput:
        p = float(self.pipeline.predict_proba([host])[0][1])
        return ModelOutput(
            name=self.name, version=self.version, target="url", probability=round(p, 4),
            label="scam" if p >= 0.5 else "legit",
            top_features=[FeatureContribution(feature=f"domain: {model_key(host)}", weight=round(p, 4))],
        )


@lru_cache
def get_url_model() -> URLHostModel | None:
    path = get_settings().models_dir / ARTIFACT
    if not path.exists():
        log.warning("URL model missing at %s — rules only. Train with: python -m app.ml.url.train", path)
        return None
    return URLHostModel(path)


def _lev(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _ev(code, label, severity, weight, detail=None, excerpt=None) -> Evidence:
    return Evidence(code=code, label=label, severity=severity, weight=weight, source="url_rules",
                    detail=detail, excerpt=excerpt)


def url_rules(u: ParsedURL) -> tuple[list[Evidence], bool]:
    """Return (evidence, trusted). `trusted` = exact registered-domain allowlist match."""
    ev: list[Evidence] = []
    host, reg = u.host, u.registered_domain
    full_lower = (u.host + u.path + "?" + u.query).lower()
    on_free_host = any(host == fh or host.endswith("." + fh) for fh in FREE_HOSTING)

    trusted = (not u.is_ip and not on_free_host and reg in ALLOWLIST and reg not in MESSAGING_DOMAINS)
    official = not u.is_ip and any(u.suffix == s or u.suffix.endswith("." + s) for s in OFFICIAL_SUFFIXES)
    if trusted:
        ev.append(_ev("KNOWN_DOMAIN", f"Recognised legitimate domain ({reg})", "positive", -40,
                      "This is the genuine domain of a well-known organisation. The link could still lead to "
                      "user-created content, so stay alert to what the page asks for."))
    elif official:
        ev.append(_ev("OFFICIAL_SUFFIX", f"Official government / education domain (.{u.suffix})", "positive", -30,
                      "These domain endings can only be registered by verified institutions."))

    if u.is_ip:
        ev.append(_ev("IP_HOST", "Uses a raw IP address instead of a website name", "high", 18,
                      "Legitimate services use domain names. IP-address links hide who runs the site.", host))
    if "xn--" in host:
        ev.append(_ev("PUNYCODE", "Uses look-alike (internationalised) characters", "high", 15,
                      "Punycode can make a fake domain look identical to a real one, e.g. 'аpple.com' with a Cyrillic 'а'.", host))
    if "@" in u.normalised.split("//", 1)[-1].split("/")[0]:
        ev.append(_ev("AT_SYMBOL", "Contains '@', which hides the real destination", "high", 12,
                      "Browsers ignore everything before '@' in a link — the real site is after it."))

    # Brand impersonation: brand keyword in host but not the brand's own domain.
    if not trusted:
        host_l = host.translate(_LEET)
        for brand, domains in BRANDS.items():
            if reg in domains:
                break
            # Short brands (sbi, lic, jio) need word boundaries on both sides; longer
            # ones only at the start of a word ("axisbank", "hdfcnetbanking").
            pattern = rf"(?<![a-z]){re.escape(brand)}" + (r"(?![a-z])" if len(brand) < 4 else "")
            if re.search(pattern, host_l):
                ev.append(_ev("BRAND_IMPERSONATION", f"Mentions '{brand}' but isn't {brand}'s official website", "critical", 22,
                              f"The official {brand} domains are {', '.join(sorted(domains))}. This link is on {reg}.", host))
                break
        else:
            label = u.domain.translate(_LEET)
            for brand, domains in BRANDS.items():
                for d in domains:
                    official_label = d.split(".")[0]
                    if len(official_label) >= 5 and label != official_label and _lev(label, official_label) <= 1 + (len(official_label) > 7):
                        ev.append(_ev("TYPOSQUAT", f"Look-alike of {d}", "critical", 22,
                                      f"'{reg}' differs from the real '{d}' by only a character or two — a classic typosquatting trick.", host))
                        break
                else:
                    continue
                break

    if reg in SHORTENERS or host in SHORTENERS:
        ev.append(_ev("SHORTENER", "Shortened link hides the real destination", "medium", 10,
                      "SENTINEL does not open links, so the final destination is unknown. Scammers use shorteners to disguise malicious sites."))
    if reg in MESSAGING_DOMAINS or host in MESSAGING_DOMAINS:
        ev.append(_ev("MESSAGING_LINK", "Opens a chat with an unknown WhatsApp/Telegram account", "low", 5,
                      "Links that move you into private chats are common in task-job and investment scams."))
    if on_free_host:
        ev.append(_ev("FREE_HOSTING", "Hosted on a free website builder", "medium", 10,
                      "Free hosting platforms are legitimate, but are heavily abused for throwaway phishing pages.", host))
    if u.suffix.split(".")[-1] in SUSPICIOUS_TLDS and not trusted:
        ev.append(_ev("SUSPICIOUS_TLD", f"Uses a high-abuse domain ending (.{u.suffix})", "medium", 8,
                      "Cheap domain endings like this are disproportionately used for scam sites."))
    if u.scheme == "http" and u.has_explicit_scheme and not trusted:
        ev.append(_ev("NO_HTTPS", "Not encrypted (http instead of https)", "low", 6,
                      "Anything you type on this page can be intercepted. Note: https alone does NOT mean a site is safe."))
    if u.port and u.port not in (80, 443):
        ev.append(_ev("ODD_PORT", f"Uses an unusual port (:{u.port})", "medium", 8))
    sub_depth = len([x for x in u.subdomain.split(".") if x and x != "www"])
    if sub_depth >= 3:
        ev.append(_ev("DEEP_SUBDOMAIN", "Unusually many sub-domains", "medium", 6,
                      "Long chains like 'secure.login.bank.example.com' push the real domain out of view.", host))
    if host.count("-") >= 3 or (u.domain.count("-") >= 2 and not trusted):
        ev.append(_ev("HYPHENATED_HOST", "Domain stuffed with hyphenated words", "low", 5,
                      "Names like 'secure-bank-kyc-update' mimic official wording.", host))
    if len(u.normalised) > 110:
        ev.append(_ev("LONG_URL", "Very long link", "low", 4))

    if not trusted:
        kws = sorted({kw for kw in SENSITIVE_KEYWORDS if kw in full_lower})
        if kws:
            ev.append(_ev("SENSITIVE_KEYWORDS", "Uses bait words like " + ", ".join(f"'{k}'" for k in kws[:4]), "medium",
                          min(15, 5 * len(kws)), "Words about login, verification, KYC or rewards are typical of phishing pages."))
    path_l = u.path.lower()
    if path_l.endswith(RISKY_EXTENSIONS):
        ev.append(_ev("RISKY_DOWNLOAD", "Downloads an app or program file", "critical", 20,
                      "Installing apps from links (especially .apk) can give criminals control of your phone and OTPs.", u.path[-40:]))
    if re.search(r"(?:url|redirect|next|dest|goto|continue)=https?", u.query, re.I) or "//" in u.path[1:]:
        ev.append(_ev("EMBEDDED_REDIRECT", "Contains a redirect to another website", "medium", 8))
    if u.normalised.count("%") >= 6:
        ev.append(_ev("HEAVY_ENCODING", "Heavily encoded characters in the link", "low", 4))
    return ev, trusted


def analyze_url(u: ParsedURL) -> URLAnalysis:
    model = get_url_model()
    output = model.predict(u.host) if model else None
    evidence, trusted = url_rules(u)
    return URLAnalysis(parsed=u, model=output, evidence=evidence, trusted=trusted)
