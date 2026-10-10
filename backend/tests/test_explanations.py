"""Explanations and advice must be specific to the analysed content and consistent with the verdict.

Covers renewal reminders, safety warnings, OTP-sharing scams, KYC phishing, job-fee scams, suspicious URLs,
screenshots (OCR) and QR codes (link and UPI), and guards against the bugs that motivated this layer:
unrelated guidance (an SBI link example on a Sun Direct reminder), duplicated advice, and claims about
checks that didn't run.
"""

import re

import pytest

from app.agents.orchestrator import get_agent
from app.rag.index import retrieve
from app.rag.knowledge import load_knowledge
from app.rag.section_tags import SECTION_TAGS
from app.schemas.analysis import InputType
from app.services import reputation

from .fixtures import chat_screenshot_png, qr_png

SUN_DIRECT = ("Dear Customer, your Sun Direct 82141058287 expires on 2026-10-06. Please renew in time to continue "
              "uninterrupted services.")
QR_WARNING = ("Do not scan any QR code received from any unidentified resources. It may lead to unauthorised debit "
              "of money from your bank account.")
OTP_SCAM = "Don't worry, just share the OTP to complete your refund."
KYC_PHISHING = "Dear customer your SBI account will be blocked today. Update KYC at http://sbi-kyc-verify.co/update"
JOB_FEE = "Congratulations! You are selected for a work from home job. Pay Rs 1500 registration fee to confirm your seat."
PAYPAL_URL = "http://paypa1-resolution.com/login/verify"


def run(input_type, payload):
    return get_agent().run(input_type, payload)


def user_text(r) -> str:
    """Everything a user reads about the verdict (summary, why, advice)."""
    return " ".join([r.explanation.summary, *r.explanation.why_it_matters,
                     *[f"{x.title} {x.detail}" for x in r.recommendations]])


def rec_ids(r):
    return [x.id for x in r.recommendations]


def assert_well_formed(r):
    """Invariants for every result: something to read, no duplicates, no contradictions."""
    assert r.explanation.why_it_matters, "the 'Why this matters' card must never be empty"
    assert len(set(r.explanation.why_it_matters)) == len(r.explanation.why_it_matters)
    assert len(set(rec_ids(r))) == len(rec_ids(r))
    assert not ({"verify_official", "renew_official"} <= set(rec_ids(r)))  # same advice twice
    if r.risk_level.value == "LOW":
        assert "doesn't guarantee it's safe" in r.explanation.summary
        assert not {"no_click", "no_otp", "no_pay", "dont_reply", "report", "already_paid"} & set(rec_ids(r))
        assert not any(f.code.endswith("MODEL_MATCH") for f in r.findings)


# --------------------------------------------------------------------- renewal
def test_renewal_reminder_is_explained_as_uncertain_with_renewal_advice():
    r = run(InputType.TEXT, SUN_DIRECT)
    assert_well_formed(r)
    s = r.explanation.summary
    assert r.risk_level.value == "MEDIUM"
    assert "no specific scam tactic" in s and "may be genuine" in s and "who really sent it" in s
    assert "official app or website" in s
    assert rec_ids(r) == ["renew_official"]  # no "report it" for a probably-genuine reminder
    assert any("renewal reminders" in w for w in r.explanation.why_it_matters)


def test_renewal_reminder_shows_no_unrelated_guidance():
    """Regression: the Sun Direct result showed the phishing guide's SBI link example."""
    r = run(InputType.TEXT, SUN_DIRECT)
    text = user_text(r).lower()
    for unrelated in ("sbi", "verify-kyc", "paypa1", "hdfc", "upi pin", "urgency", "within 24 hours", "the link"):
        assert unrelated not in text, unrelated
    assert r.explanation.sources == []


# --------------------------------------------------------------- safety warning
def test_safety_warning_says_no_warning_signs_without_guarantee():
    r = run(InputType.TEXT, QR_WARNING)
    assert_well_formed(r)
    assert r.risk_level.value == "LOW" and r.findings == []
    assert r.explanation.summary.startswith("SENTINEL didn't find warning signs in this message.")
    assert rec_ids(r) == ["stay_alert"]
    assert r.limitations == []


# ------------------------------------------------------------------ OTP scam
def test_otp_scam_names_the_request_and_gives_otp_advice():
    r = run(InputType.TEXT, OTP_SCAM)
    assert_well_formed(r)
    assert r.risk_level.value in {"HIGH", "CRITICAL"}
    assert "share an OTP" in r.explanation.summary and "a pattern" in r.explanation.summary
    assert rec_ids(r)[0] == "no_otp"
    assert {s.slug for s in r.explanation.sources} == {"otp-pin-safety"}
    lowered = " ".join(r.explanation.why_it_matters).lower()
    assert "password manager" not in lowered and "upi pin" not in lowered  # previously shown, unrelated


# --------------------------------------------------------------- KYC phishing
def test_kyc_phishing_explains_the_link_and_where_kyc_is_really_done():
    r = run(InputType.TEXT, KYC_PHISHING)
    assert_well_formed(r)
    assert r.risk_level.value == "CRITICAL"
    s = r.explanation.summary
    assert "Main warning signs:" in s and "sbi" in s.lower() and "link that looks dangerous" in s
    assert rec_ids(r)[:2] == ["no_click", "kyc_official"]
    assert "verify_official" not in rec_ids(r)  # superseded by the KYC-specific advice
    why = " ".join(r.explanation.why_it_matters)
    assert "registered domain" in why
    assert "sbi.co.in.verify-kyc.xyz" not in why  # canned guide example, not the user's link


def test_job_fee_scam_gets_job_guidance_not_upi():
    r = run(InputType.TEXT, JOB_FEE)
    assert_well_formed(r)
    assert "upfront fee" in r.explanation.summary
    assert {s.slug for s in r.explanation.sources} == {"job-scams"}
    assert "no_pay" in rec_ids(r)
    assert "upi pin" not in user_text(r).lower()


# -------------------------------------------------------------- suspicious URL
def test_suspicious_url_has_no_examples_about_other_brands():
    r = run(InputType.URL, PAYPAL_URL)
    assert_well_formed(r)
    assert r.risk_level.value in {"HIGH", "CRITICAL"}
    why = " ".join(r.explanation.why_it_matters).lower()
    for other in ("sbi", "hdfc", "amaz0n", "amazon"):
        assert other not in why, other
    assert "no_click" in rec_ids(r)


# ---------------------------------------------------------------- screenshot
def test_screenshot_advice_follows_extracted_text(client):
    body = client.post("/api/analyze/image",
                       files={"file": ("r.png", chat_screenshot_png(SUN_DIRECT, sender="SUNDTH"), "image/png")}).json()
    assert body["extracted"]["text_source"] == "ocr"
    assert "renew_official" in [x["id"] for x in body["recommendations"]]
    assert "sbi" not in " ".join(body["explanation"]["why_it_matters"]).lower()
    assert "screenshot" in body["explanation"]["summary"]


def test_scam_screenshot_gets_protective_steps_for_its_threat(client):
    png = chat_screenshot_png("URGENT: Your Paytm KYC has expired. Your wallet will be blocked today. "
                              "Share the OTP sent to your phone with our executive to reactivate.")
    body = client.post("/api/analyze/image", files={"file": ("s.png", png, "image/png")}).json()
    ids = [x["id"] for x in body["recommendations"]]
    assert body["risk_level"] in {"HIGH", "CRITICAL"}
    assert ids[0] == "no_otp" and "kyc_official" in ids and "already_paid" in ids
    assert "renew_official" not in ids  # "KYC has expired" is not a subscription renewal


# ------------------------------------------------------------------------ QR
def test_qr_link_explains_it_was_not_opened(client):
    body = client.post("/api/analyze/qr", files={"file": ("q.png", qr_png("http://sbi-kyc-verify.co/update"), "image/png")}).json()
    ids = [x["id"] for x in body["recommendations"]]
    assert body["risk_level"] in {"HIGH", "CRITICAL"}
    assert "qr_check_destination" in ids
    assert "no_click" not in ids  # would repeat "don't open" (found in live review)
    assert any("without opening it" in w for w in body["explanation"]["why_it_matters"])


@pytest.mark.parametrize("text", [
    "URGENT: Your Paytm KYC has expired. Your wallet will be blocked today. Share the OTP sent to your phone.",
    "Your SBI card ending 1234 will expire on 31/10/2026. A replacement card has been dispatched to your registered address.",
])
def test_expiry_alone_is_not_a_renewal(text):
    """Found in live review: 'KYC has expired' and a card-replacement notice were told to 'renew via the official app'."""
    assert "renew_official" not in rec_ids(run(InputType.TEXT, text))


def test_plan_expiry_is_a_renewal():
    r = run(InputType.TEXT, "Your Jio plan expires on 12 Oct. Recharge to continue enjoying unlimited calls.")
    assert "renew_official" in rec_ids(r)


def test_upi_qr_explains_payment_direction(client):
    payload = "upi://pay?pa=refund.desk4521@ybl&pn=Refund%20Desk&am=4999&tn=Refund%20for%20cancelled%20order"
    body = client.post("/api/analyze/qr", files={"file": ("u.png", qr_png(payload), "image/png")}).json()
    assert body["risk_level"] in {"HIGH", "CRITICAL"}
    assert any("UPI payment request" in w for w in body["explanation"]["why_it_matters"])
    assert "dont_scan" in [x["id"] for x in body["recommendations"]]


def test_safe_website_qr_is_not_given_destination_warnings(client):
    body = client.post("/api/analyze/qr", files={"file": ("s.png", qr_png("https://www.irctc.co.in/"), "image/png")}).json()
    assert body["risk_level"] == "LOW"
    ids = [x["id"] for x in body["recommendations"]]
    assert "qr_check_destination" not in ids and "no_click" not in ids
    assert not any("without opening" in w for w in body["explanation"]["why_it_matters"])


# ----------------------------------------------------- claims about checks
def test_no_safe_browsing_claim_when_lookup_not_configured(monkeypatch):
    monkeypatch.setattr(reputation, "is_configured", lambda: False)
    r = run(InputType.URL, PAYPAL_URL)
    everything = user_text(r) + " ".join(e.label for e in r.reassurances + r.context)
    assert "Safe Browsing" not in everything
    assert any("not configured" in lim for lim in r.limitations)


def test_no_safe_browsing_claim_when_lookup_fails(monkeypatch):
    monkeypatch.setattr(reputation, "is_configured", lambda: True)
    monkeypatch.setattr(reputation, "check_url", lambda url, timeout=4.0: reputation.ReputationResult(
        checked=False, note="URL reputation service unavailable right now."))
    r = run(InputType.URL, PAYPAL_URL)
    assert not any("Safe Browsing" in e.label for e in r.reassurances + r.findings)
    assert "URL reputation service unavailable right now." in r.limitations


def test_safe_browsing_clean_is_reported_only_as_not_proof(monkeypatch):
    monkeypatch.setattr(reputation, "is_configured", lambda: True)
    monkeypatch.setattr(reputation, "check_url", lambda url, timeout=4.0: reputation.ReputationResult(checked=True))
    r = run(InputType.URL, PAYPAL_URL)
    clean = [e for e in r.reassurances if e.code == "REPUTATION_CLEAN"]
    assert clean and "not proof of safety" in clean[0].detail
    assert r.risk_level.value in {"HIGH", "CRITICAL"}  # a clean lookup never overrides the evidence


# ------------------------------------------------------ retrieval guardrails
def test_section_tag_map_matches_the_guides():
    """Fails if a guide heading is renamed, so the explanation map can't silently go stale."""
    sections = {(c.slug, c.section) for d in load_knowledge() for c in d.chunks}
    missing = [k for k in SECTION_TAGS if k not in sections]
    assert not missing, missing


def test_explanation_retrieval_has_no_similarity_fallback():
    assert retrieve("dear customer renew subscription", ["GENERIC_GREETING", "TEXT_MODEL_MATCH"],
                    k=3, require_tag_match=True) == []
    hits = retrieve("share the OTP", ["OTP_REQUEST"], k=3, require_tag_match=True)
    assert hits and all("OTP_REQUEST" in SECTION_TAGS[(c.slug, c.section)] for c, _ in hits)


@pytest.mark.parametrize("text", [SUN_DIRECT, QR_WARNING, OTP_SCAM, KYC_PHISHING, JOB_FEE,
                                  "Your Airtel postpaid bill of Rs 499 is due on 12 Oct. Pay via the Airtel Thanks app.",
                                  "Hi, is this you in this video?? lol check it out bit.ly/3xVidz0"])
def test_guidance_never_names_a_brand_absent_from_the_content(text):
    from app.rag.explainer import _brands_in
    r = run(InputType.TEXT, text)
    assert_well_formed(r)
    present = _brands_in(text)
    for w in r.explanation.why_it_matters:
        assert _brands_in(w) <= present, (w, present)
    assert not re.search(r"\bseveral patterns\b", r.explanation.summary) or len(
        [f for f in r.findings if f.weight > 0]) > 1
