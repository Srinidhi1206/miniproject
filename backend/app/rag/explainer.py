"""ExplanationService — evidence-grounded explanations via retrieval.

1. Build a retrieval query from the evidence actually found.
2. Retrieve guidance passages (FAISS over LSA embeddings, tag re-ranking).
3. Compose the explanation:
     - template (default): verdict sentence with real numbers + the lead
       paragraph of each retrieved passage, each tied to a finding.
     - LLM (optional): the same inputs, rewritten in plain language. The LLM
       is told the verdict and may not change it; output is schema-validated.
Sources are always returned so the UI can link to the Safety Center.
"""

from __future__ import annotations

import logging

from app.rag.index import retrieve
from app.rag.llm import get_llm
from app.schemas.analysis import (
    ComponentScore, Evidence, Explanation, InputType, RiskLevel, SourceRef,
)

log = logging.getLogger("sentinel.explain")

_INPUT_NOUN = {InputType.TEXT: "message", InputType.URL: "link", InputType.IMAGE: "screenshot",
               InputType.QR: "QR code", InputType.AUDIO: "recording"}

SYSTEM_PROMPT = (
    "You explain scam-analysis results to ordinary people in India and elsewhere. "
    "The risk verdict has ALREADY been decided by SENTINEL's models and rules; you must not change it, "
    "soften it, or add new findings. Use only the evidence and guidance passages provided. "
    "Write plainly, without jargon, markdown, or exclamation marks. Never claim certainty the evidence does not support."
)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _summary(level: RiskLevel, noun: str, components: list[ComponentScore], findings: list[Evidence]) -> str:
    """Plain-language verdict. No model percentages here — those live in the
    technical details. Wording strength follows the risk level (false-positive UX)."""
    warnings = [e for e in findings if e.weight > 0 or e.severity in ("high", "critical")]
    n = len(warnings)
    top = components[0] if components else None
    parts: list[str] = []
    if level == RiskLevel.CRITICAL:
        parts.append(f"This {noun} strongly matches known scam patterns. Treat it as a scam.")
    elif level == RiskLevel.HIGH:
        parts.append(f"This {noun} shows several patterns commonly used in scams. "
                     "Don't click, pay or reply until you've verified it independently.")
    elif level == RiskLevel.MEDIUM:
        parts.append(f"We found {_plural(n, 'warning sign') if n else 'some warning signs'} in this {noun}. "
                     "It may be genuine — verify it through an official channel before you act.")
    else:
        parts.append(f"SENTINEL didn't find warning signs in this {noun}. That doesn't guarantee it's safe — "
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


def explain(
    *, input_type: InputType, channel: str | None, level: RiskLevel, score: int,
    components: list[ComponentScore], findings: list[Evidence], reassurances: list[Evidence],
) -> Explanation:
    noun = _INPUT_NOUN.get(input_type, "content")
    summary = _summary(level, noun, components, findings)

    if not findings:
        # Nothing suspicious: say what was checked; don't pad with unrelated scam guidance.
        why = ["SENTINEL checked for urgency, payment or fee requests, requests for OTPs or PINs, "
               "impersonation and risky links, and found none of them."]
        why.extend(f"{e.label}. {e.detail}" if e.detail else e.label for e in reassurances[:2])
        passages: list = []
    else:
        # "Why this matters" = retrieved guidance about the tactics that were found.
        # The evidence itself (with its own rationale) is listed separately, so it isn't repeated here.
        codes = [e.code for e in findings]
        passages = retrieve(_query(findings, input_type, channel), codes, k=3, require_tag_match=True)
        why = [chunk.lead for chunk, _ in passages if chunk.lead]
    sources = [SourceRef(slug=c.slug, title=c.title, section=c.section, score=s) for c, s in passages]
    explanation = Explanation(summary=summary, why_it_matters=why, sources=sources, generated_by="template+rag")

    llm = get_llm()
    if llm is None:
        return explanation
    evidence_lines = "\n".join(f"- {e.label}" + (f" (\"{e.excerpt}\")" if e.excerpt else "") for e in findings[:8]) or "- none"
    reassure_lines = "\n".join(f"- {e.label}" for e in reassurances[:4]) or "- none"
    passage_lines = "\n\n".join(f"[{c.title} — {c.section}]\n{c.text}" for c, _ in passages)
    prompt = (
        f"Verdict (fixed): {level.value} risk, score {score}/100, for a {noun}.\n\n"
        f"Evidence found by SENTINEL:\n{evidence_lines}\n\nReassuring signals:\n{reassure_lines}\n\n"
        f"Trusted guidance passages:\n{passage_lines}\n\n"
        "Write the summary and why_it_matters points for this user."
    )
    out = llm.explain(SYSTEM_PROMPT, prompt)
    if out is None or not out.summary.strip():
        return explanation
    return Explanation(summary=out.summary.strip(), why_it_matters=[w.strip() for w in out.why_it_matters if w.strip()][:5],
                       sources=sources, generated_by=f"llm:{llm.name}+rag")
