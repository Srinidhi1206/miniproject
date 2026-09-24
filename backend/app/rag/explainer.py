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


def _summary(level: RiskLevel, score: int, noun: str, components: list[ComponentScore], findings: list[Evidence]) -> str:
    text_c = next((c for c in components if c.component == "text" and c.model), None)
    url_cs = [c for c in components if c.component == "url"]
    parts: list[str] = []
    if level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        parts.append(f"This {noun} shows strong signs of a scam ({score}/100).")
    elif level == RiskLevel.MEDIUM:
        parts.append(f"This {noun} has some warning signs ({score}/100). It may be genuine, but verify before acting.")
    else:
        parts.append(f"SENTINEL found no strong scam signals in this {noun} ({score}/100).")
    if text_c and text_c.model:
        pct = round(text_c.model.probability * 100)
        parts.append(f"The text classifier rates its wording {pct}% similar to known scam messages.")
    risky_urls = [c for c in url_cs if c.score >= 60]
    if noun == "link":
        pass  # the link IS the input; the opening sentence already covers it
    elif risky_urls:
        parts.append(f"{len(risky_urls)} link{'s' if len(risky_urls) > 1 else ''} in it look{'' if len(risky_urls) > 1 else 's'} dangerous.")
    elif url_cs and all(c.score < 30 for c in url_cs):
        parts.append("The link it contains did not show risky patterns.")
    if findings:
        n = len(findings)
        parts.append(f"{n} warning sign{'s' if n != 1 else ''} {'were' if n != 1 else 'was'} identified.")
    elif level == RiskLevel.LOW:
        parts.append("That doesn't guarantee it's safe — stay alert to any request for money, codes or urgency.")
    return " ".join(parts)


def _query(findings: list[Evidence], input_type: InputType, channel: str | None) -> str:
    bits = [e.label for e in findings[:6]] + [e.detail or "" for e in findings[:3]]
    if input_type == InputType.QR:
        bits.append("QR code scan payment")
    if channel == "job_offer":
        bits.append("job offer recruitment fee")
    if not findings:
        bits.append("how to recognise scams stay safe verify official channel")
    return " ".join(bits)


def explain(
    *, input_type: InputType, channel: str | None, level: RiskLevel, score: int,
    components: list[ComponentScore], findings: list[Evidence], reassurances: list[Evidence],
) -> Explanation:
    codes = [e.code for e in findings + reassurances]
    passages = retrieve(_query(findings, input_type, channel), codes, k=3 if findings else 2)
    noun = _INPUT_NOUN.get(input_type, "content")
    summary = _summary(level, score, noun, components, findings)

    # Template: pair each top finding with its own rule rationale, then add
    # the retrieved guidance passages (deduplicated).
    why: list[str] = []
    for e in findings[:3]:
        if e.detail:
            why.append(f"{e.label}: {e.detail}")
    if not findings:
        # Nothing suspicious: say what was checked instead of padding with unrelated guidance.
        why.append("SENTINEL's rules found no specific scam tactics — no urgency, payment or fee requests, "
                   "requests for OTPs/PINs, or risky links.")
        why.extend(f"{e.label}. {e.detail}" if e.detail else e.label for e in reassurances[:2])
        passages = passages[:1]
    sources = [SourceRef(slug=c.slug, title=c.title, section=c.section, score=s) for c, s in passages]
    for chunk, _ in passages:
        if len(why) >= 5:
            break
        lead = chunk.lead
        if lead and lead not in why:
            why.append(lead)
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
