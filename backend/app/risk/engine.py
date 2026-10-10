"""RiskEngine — turns model probabilities + rule evidence into one 0–100 score.

The formula is intentionally simple enough to compute by hand in a viva:

  TEXT component   = 70 × P_text(scam)      + clamp(Σ rule weights, −15, +30)
                     (45 × P instead of 70 when the text is *uncorroborated*: no medium-or-stronger
                      tactic AND no call to action — no link, number, reply, payment or scan request)
  URL component    = 55 × P_url(phishing)   + clamp(Σ rule weights, −45, +45)
  UPI component    = 20 (baseline: every UPI QR is a payment) + Σ rule weights
  Overrides (floors, applied per component, each is listed in the result):
    • ≥1 critical text tactic → at least 60 ; ≥2 → at least 80
    • brand impersonation / typosquat / risky download URL → at least 70
    • UPI QR whose note promises a refund/prize/cashback → at least 75
    • reputation service lists the URL as malicious → at least 95
  FINAL = max(component scores) + 5 × (other components scoring ≥ 50), capped at +10
  Bands: 0–29 LOW · 30–59 MEDIUM · 60–79 HIGH · 80–100 CRITICAL

Why the uncorroborated weight: the text model measures resemblance to scam wording,
not intent. Formal notices ("Dear Customer, your subscription expires on …") share
vocabulary and number patterns with scams. Without a named tactic or any way for
the reader to act, model similarity alone can justify a MEDIUM caution but never
HIGH (45 + low-severity rules < 60) — mirroring the URL side, where the model alone
(max 55) also cannot reach HIGH.

Why max rather than average: one dangerous link inside an innocent-sounding
message is still dangerous. The corroboration bonus rewards independent
signals agreeing.
"""

from __future__ import annotations

from app.schemas.analysis import (
    Classification, ComponentScore, Evidence, ModelOutput, RiskBreakdown, RiskLevel,
)

TEXT_MODEL_MAX = 70
TEXT_MODEL_MAX_UNCORROBORATED = 45
TEXT_RULE_RANGE = (-15, 30)
URL_MODEL_MAX = 55
URL_RULE_RANGE = (-45, 45)
UPI_BASELINE = 20
CORROBORATION_STEP = 5
CORROBORATION_CAP = 10
CORROBORATION_MIN = 50

FORMULA = (
    "component: text = 70·P(scam) + rules[−15,+30] (45·P if no tactic and no call to action); url = 55·P(phishing) + rules[−45,+45]; "
    "upi = 20 + rules. final = max(components) + 5 per other component ≥50 (max +10)."
)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _rules_sum(evidence: list[Evidence], lo: int, hi: int) -> int:
    return int(_clamp(sum(e.weight for e in evidence), lo, hi))


def band(score: int) -> RiskLevel:
    if score >= 80:
        return RiskLevel.CRITICAL
    if score >= 60:
        return RiskLevel.HIGH
    if score >= 30:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def classify(level: RiskLevel) -> Classification:
    return {RiskLevel.LOW: Classification.SAFE, RiskLevel.MEDIUM: Classification.SUSPICIOUS}.get(
        level, Classification.SCAM)


VERDICTS = {
    # Wording strength follows the evidence: never "safe", never certain below CRITICAL.
    RiskLevel.LOW: "No warning signs found",
    RiskLevel.MEDIUM: "Potentially suspicious",
    RiskLevel.HIGH: "Potential scam",
    RiskLevel.CRITICAL: "Very likely a scam",
}


def is_corroborated(evidence: list[Evidence], actionable: bool) -> bool:
    """Text evidence beyond model similarity: a medium-or-stronger tactic, or a way for the reader to act."""
    return actionable or any(e.weight > 0 and e.severity in ("medium", "high", "critical") for e in evidence)


def score_text(subject: str, model: ModelOutput | None, evidence: list[Evidence],
               actionable: bool = True) -> ComponentScore:
    """`actionable`: the text contains a link or an un-negated instruction to click/call/reply/pay/scan…
    (see ml/text/indicators.has_call_to_action). Defaults to True, i.e. the full model weight."""
    rules = _rules_sum(evidence, *TEXT_RULE_RANGE)
    overrides = []
    if model is not None:
        if is_corroborated(evidence, actionable):
            model_points = TEXT_MODEL_MAX * model.probability
        else:
            model_points = TEXT_MODEL_MAX_UNCORROBORATED * model.probability
            overrides.append(f"No scam tactic and nothing asks you to act (no link, number, reply or payment) "
                             f"→ model weight {TEXT_MODEL_MAX_UNCORROBORATED} instead of {TEXT_MODEL_MAX}")
    else:  # model unavailable: rules alone, scaled so they can still reach HIGH
        model_points, rules = 0.0, int(_clamp(sum(e.weight for e in evidence) * 2, 0, 100))
    score = _clamp(model_points + rules, 0, 100)
    criticals = [e for e in evidence if e.severity == "critical"]
    if len(criticals) >= 2 and score < 80:
        score = 80
        overrides.append(f"Two or more critical tactics ({', '.join(e.code for e in criticals[:3])}) → floor 80")
    elif len(criticals) == 1 and score < 60:
        score = 60
        overrides.append(f"Critical tactic {criticals[0].code} → floor 60")
    return ComponentScore(component="text", subject=subject, score=round(score), model_points=round(model_points, 1),
                          rule_points=rules, overrides=overrides, model=model, evidence=evidence)


def score_url(subject: str, model: ModelOutput | None, evidence: list[Evidence]) -> ComponentScore:
    rules = _rules_sum(evidence, *URL_RULE_RANGE)
    model_points = URL_MODEL_MAX * model.probability if model else 0.0
    score = _clamp(model_points + rules, 0, 100)
    overrides = []
    codes = {e.code for e in evidence}
    if "REPUTATION_MALICIOUS" in codes and score < 95:
        score = 95
        overrides.append("Listed by URL reputation service → floor 95")
    for code in ("BRAND_IMPERSONATION", "TYPOSQUAT", "RISKY_DOWNLOAD"):
        if code in codes and score < 70:
            score = 70
            overrides.append(f"{code} → floor 70")
            break
    return ComponentScore(component="url", subject=subject, score=round(score), model_points=round(model_points, 1),
                          rule_points=rules, overrides=overrides, model=model, evidence=evidence)


def score_upi(subject: str, evidence: list[Evidence]) -> ComponentScore:
    rules = int(sum(e.weight for e in evidence))
    score = _clamp(UPI_BASELINE + rules, 0, 100)
    overrides = []
    if any(e.code == "UPI_BAIT_NOTE" for e in evidence) and score < 75:
        score = 75
        overrides.append("UPI_BAIT_NOTE (payment disguised as refund/prize) → floor 75")
    return ComponentScore(component="upi", subject=subject, score=round(score), model_points=0.0,
                          rule_points=rules, overrides=overrides, model=None, evidence=evidence)


def combine(components: list[ComponentScore]) -> RiskBreakdown:
    if not components:
        raise ValueError("combine() needs at least one component")
    ordered = sorted(components, key=lambda c: c.score, reverse=True)
    base = ordered[0].score
    bonus = min(CORROBORATION_CAP, CORROBORATION_STEP * sum(1 for c in ordered[1:] if c.score >= CORROBORATION_MIN))
    final = int(_clamp(base + bonus, 0, 100))
    return RiskBreakdown(components=ordered, base_score=base, corroboration_bonus=bonus, final_score=final,
                         formula=FORMULA)


def primary_confidence(components: list[ComponentScore]) -> float:
    """Confidence of the highest-scoring component's model in its own label."""
    for c in sorted(components, key=lambda c: c.score, reverse=True):
        if c.model is not None:
            p = c.model.probability
            return round(max(p, 1 - p), 3)
    return 0.6  # rules-only verdicts (e.g. UPI) — deterministic facts, moderate confidence
