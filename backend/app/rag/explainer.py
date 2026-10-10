"""ExplanationService — evidence-grounded explanations via retrieval.

1. Name the evidence actually found (summary) and explain this result's own
   specifics (e.g. why an uncertain renewal reminder can't be confirmed).
2. Retrieve guidance passages (FAISS over LSA embeddings), restricted to guide
   *sections* written about a found tactic (rag/section_tags.py). No similarity
   fallback, and passages illustrated with a brand that isn't in the user's
   content are skipped, so a result never shows an unrelated example.
3. Compose the explanation:
     - template (default): verdict sentence + specific lines + the lead
       paragraph of each relevant passage.
     - LLM (optional): the same inputs, rewritten in plain language. The LLM
       is told the verdict and may not change it; output is schema-validated.
Sources are always returned so the UI can link to the Safety Center.
"""

from __future__ import annotations

import logging
import re

from app.rag.index import retrieve
from app.rag.llm import get_llm
from app.schemas.analysis import (
    ComponentScore, Evidence, Explanation, InputType, RiskLevel, SourceRef,
)

log = logging.getLogger("sentinel.explain")

_INPUT_NOUN = {InputType.TEXT: "message", InputType.URL: "link", InputType.IMAGE: "screenshot",
               InputType.QR: "QR code", InputType.AUDIO: "recording"}

SYSTEM_PROMPT = (
    "You explain scam-analysis results to ordinary people. "
    "The risk verdict has ALREADY been decided deterministically; do not change it, soften it, or invent new findings. "
    "Write plainly, without technical jargon, model names, probabilities, or exclamation marks. Be concise. "
    "If the risk is LOW, state clearly that no warning signs were found, but note automated analysis cannot guarantee safety. "
    "If HIGH or CRITICAL, clearly explain the strongest evidence without fear-mongering. Ground everything in the exact evidence provided."
)

_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4, "positive": 5}
_MODEL_MATCH = {"TEXT_MODEL_MATCH", "URL_MODEL_MATCH"}
# Brand keys that are also everyday words; never read them as a brand mention.
_COMMON_WORD_BRANDS = {"chase", "apple", "office", "outlook", "meta", "axis"}
_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})

_VERIFY_HINT = {
    "kyc": "Check with your bank in its official app, net banking or at a branch. Banks don't complete KYC through "
           "links or calls.",
    "renewal": "Check the date in the provider's official app or website before renewing.",
    "job": "Check the job on the company's official careers page. A genuine employer never charges you to get a job.",
}
_DEFAULT_HINT = "Verify it through an official channel before you act."


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _as_clause(label: str) -> str:
    """'Asks you to share an OTP' -> 'asks you to share an OTP' (keeps acronyms such as 'UPI ...')."""
    return label[0].lower() + label[1:] if len(label) > 1 and label[1].islower() else label


def _signals(findings: list[Evidence]) -> list[Evidence]:
    """Warning signs that carry points, strongest first (model-similarity notes are not tactics)."""
    return sorted((e for e in findings if e.weight > 0 and e.code not in _MODEL_MATCH),
                  key=lambda e: (_SEVERITY_RANK.get(e.severity, 9), -e.weight))


def _tactics(findings: list[Evidence]) -> list[Evidence]:
    return [e for e in _signals(findings) if e.severity in ("medium", "high", "critical")]


def _named(signs: list[Evidence], k: int = 2) -> str:
    return "; ".join(_as_clause(e.label) for e in signs[:k])


def _hint(scenarios: set[str]) -> str:
    return next((_VERIFY_HINT[s] for s in ("kyc", "renewal", "job") if s in scenarios), _DEFAULT_HINT)


def _summary(level: RiskLevel, noun: str, components: list[ComponentScore], findings: list[Evidence],
             scenarios: set[str]) -> str:
    """Plain-language verdict naming the actual evidence. No model percentages here — those live in the
    technical details. Wording strength follows the risk level (false-positive UX)."""
    signs, tactics = _signals(findings), _tactics(findings)
    top = components[0] if components else None
    parts: list[str] = []
    if level == RiskLevel.CRITICAL:
        parts.append(f"Critical risk. This {noun} strongly matches known scam patterns. Treat it as fraud.")
        if signs:
            parts.append(f"Main warning signs: {_named(signs)}.")
    elif level == RiskLevel.HIGH:
        if signs:
            pattern = "a pattern" if len(signs) == 1 else "several patterns"
            parts.append(f"High risk. This {noun} shows {pattern} commonly used in scams: {_named(signs)}.")
        else:
            parts.append(f"High risk. This {noun} shows patterns commonly used in scams.")
        parts.append("Don't click, pay or reply until you've verified it independently.")
    elif level == RiskLevel.MEDIUM:
        if not tactics and top is not None and top.component == "text":
            uncorroborated = any("model weight" in o for o in top.overrides)
            parts.append(f"Potentially suspicious. The wording of this {noun} resembles some scam messages, but "
                         "SENTINEL found no specific scam tactic"
                         + (" and nothing in it asks you to click, call, reply or pay" if uncorroborated else "")
                         + ". It may be genuine; what can't be confirmed is who really sent it. " + _hint(scenarios))
        else:
            named = f": {_named(signs)}" if signs else ""
            count = _plural(len(signs), "warning sign") if signs else "some warning signs"
            parts.append(f"Potentially suspicious. We found {count} in this {noun}{named}. It may be genuine. "
                         + _hint(scenarios))
    elif signs:
        parts.append(f"SENTINEL found no clear signs of a scam in this {noun}, only minor points "
                     f"({_named(signs)}). That doesn't guarantee it's safe: be careful if it later asks for money, "
                     "codes or personal details.")
    else:
        parts.append(f"SENTINEL didn't find warning signs in this {noun}. That doesn't guarantee it's safe: "
                     "be careful if it later asks for money, codes or personal details.")

    url_cs = [c for c in components if c.component == "url"]
    if noun != "link" and any(c.score >= 60 for c in url_cs):
        parts.append("It contains a link that looks dangerous.")
    # A URL warning driven mostly by how the name LOOKS (little rule evidence) is less certain — say so.
    if (level == RiskLevel.MEDIUM and top is not None and top.component == "url"
            and top.rule_points <= 10 and top.model_points >= 30):
        parts.append("This warning is based mainly on how the website name looks, so treat it as a caution rather than proof.")
    return " ".join(parts)


def _query(findings: list[Evidence], input_type: InputType, channel: str | None) -> str:
    bits = [e.label for e in findings[:6]] + [e.detail or "" for e in findings[:3]]
    if input_type == InputType.QR:
        bits.append("QR code")
    if channel == "job_offer":
        bits.append("job offer recruitment fee")
    return " ".join(bits)


def _brands_in(text: str) -> set[str]:
    from app.ml.url.lexicon import BRANDS  # local import: keeps the RAG package independent of the URL package
    words = set(re.findall(r"[a-z0-9]+", text.lower().translate(_LEET)))
    return {b for b in BRANDS if b not in _COMMON_WORD_BRANDS and b in words}


def _specific_lines(level: RiskLevel, findings: list[Evidence], scenarios: set[str],
                    components: list[ComponentScore]) -> list[str]:
    """Short explanations tied to this result's own evidence and scenario (never generic examples)."""
    codes = {e.code for e in findings}
    top = components[0] if components else None
    lines: list[str] = []
    if level == RiskLevel.MEDIUM and not _tactics(findings) and top is not None and top.component == "text":
        if "renewal" in scenarios:
            lines.append("Genuine and fake renewal reminders look alike, and this one contains nothing that confirms or "
                         "rules out either. Its style resembles scam messages, but it has no link, number or payment "
                         "request to judge.")
        else:
            lines.append("Scam messages often copy the style of genuine ones, so a formal tone proves nothing either "
                         "way. Checking with the sender directly, through a channel you already trust, settles it.")
    if codes & {"BRAND_IMPERSONATION", "TYPOSQUAT"}:
        lines.append("Scam websites put a real organisation's name inside their own address. Only the registered "
                     "domain decides who runs a site, so don't use this link at all: open the organisation's "
                     "official app or type its address yourself.")
    if "qr_link" in scenarios and any(c.component == "url" and c.score >= 30 for c in components):
        lines.append("The QR code leads to a website. SENTINEL read the address without opening it; scanning the code "
                     "with your phone would open it straight away.")
    if "upi_qr" in scenarios and codes & {"UPI_BAIT_NOTE", "UPI_PRESET_AMOUNT", "UPI_PERSONAL_PAYEE"}:
        lines.append("This QR code is a UPI payment request: scanning it and entering your PIN sends money to the "
                     "payee shown, whatever the note says.")
    return lines


def explain(
    *, input_type: InputType, channel: str | None, level: RiskLevel, score: int,
    components: list[ComponentScore], findings: list[Evidence], reassurances: list[Evidence],
    scenarios: set[str] | None = None, content: str = "",
) -> Explanation:
    """`scenarios` (rag/scenarios.py) and `content` (the analysed text, URL or QR payload) only shape wording
    and filter guidance; they never add evidence."""
    scenarios = scenarios or set()
    noun = _INPUT_NOUN.get(input_type, "content")
    summary = _summary(level, noun, components, findings, scenarios)

    signs = _signals(findings)
    passages: list = []
    if not signs and level == RiskLevel.LOW:
        # Nothing suspicious: say what was checked; don't pad with unrelated scam guidance.
        why = ["SENTINEL checked for urgency, payment or fee requests, requests for OTPs or PINs, "
               "impersonation and risky links, and found none of them."]
        why.extend(f"{e.label}. {e.detail}" if e.detail else e.label for e in reassurances[:2])
    else:
        # "Why this matters" = this result's own specifics, then guidance written about the tactics found.
        # The evidence itself (with its own rationale) is listed separately, so it isn't repeated here.
        why = _specific_lines(level, findings, scenarios, components)
        if signs:
            present = _brands_in(content)
            hits = retrieve(_query(signs, input_type, channel), [e.code for e in signs], k=4, require_tag_match=True)
            # Skip passages illustrated with a brand that isn't in this content (e.g. an SBI example on a PayPal
            # or Sun Direct result).
            passages = [(c, s) for c, s in hits if c.lead and _brands_in(c.lead) <= present][:2]
            why.extend(c.lead for c, _ in passages)
        if not why:
            why = ["None of the signs found is conclusive on its own. " + _hint(scenarios)]
    sources = [SourceRef(slug=c.slug, title=c.title, section=c.section, score=s) for c, s in passages]
    explanation = Explanation(summary=summary, why_it_matters=why, sources=sources, generated_by="template+rag")

    llm = get_llm()
    if llm is None:
        return explanation
    evidence_lines = "\n".join(f"- {e.label}" + (f" (\"{e.excerpt}\")" if e.excerpt else "") for e in findings[:8]) or "- none"
    reassure_lines = "\n".join(f"- {e.label}" for e in reassurances[:4]) or "- none"
    passage_lines = "\n\n".join(f"[{c.title} — {c.section}]\n{c.text}" for c, _ in passages)
    prompt = (
        f"Verdict: {level.value} risk for a {noun}.\n\n"
        f"Evidence detected:\n{evidence_lines}\n\nReassuring context:\n{reassure_lines}\n\n"
        f"Trusted guidance:\n{passage_lines}\n\n"
        "Task: Write a concise `summary` (1-2 sentences explaining the verdict and strongest evidence) "
        "and `why_it_matters` (1-3 bullet points explaining the implications, without repeating the summary). "
        "Do not mention scores, probabilities, or model names. Ground everything in the exact evidence provided."
    )
    out = llm.explain(SYSTEM_PROMPT, prompt)
    if out is None or not out.summary.strip():
        return explanation
    return Explanation(summary=out.summary.strip(), why_it_matters=[w.strip() for w in out.why_it_matters if w.strip()][:5],
                       sources=sources, generated_by=f"llm:{llm.name}+rag")
