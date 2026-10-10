"""False-positive calibration and scam-detection regressions.

Benign messages (service reminders, safety warnings, informational notices) must not
be called HIGH/CRITICAL just because they mention QR codes, money, banks, expiry dates
or renewal. Known scams must keep their HIGH/CRITICAL verdicts. Both are checked
end-to-end through the agent, and across the Message, Screenshot (OCR) and QR flows.
"""

import pytest

from app.agents.orchestrator import get_agent
from app.ml.text.indicators import has_call_to_action
from app.risk import engine as risk
from app.schemas.analysis import Evidence, InputType, ModelOutput

from .fixtures import chat_screenshot_png, qr_png


def run_text(text):
    return get_agent().run(InputType.TEXT, text)


def found(result):
    return {f.code for f in result.findings}


# --------------------------------------------------------------------- benign
BENIGN_SAFETY_WARNINGS = [
    "Do not scan any QR code received from any unidentified resources. It may lead to unauthorised debit "
    "of money from your bank account.",
    "Beware of fraudsters asking you to scan a QR code to receive money. Scanning a QR code is only for paying.",
    "Beware of fraudsters asking you to install AnyDesk or share your OTP.",
    "Never share your OTP, PIN or CVV with anyone. Bank officials will never ask for these details.",
    "RBI never asks for your account details. Report fraud on 1930.",
]
# The text model rates this advisory 0.93 "scam-like" (shared vocabulary: links, unknown senders, report).
# With no tactic and no call to action it is capped well below HIGH, but it can still land at the bottom of
# MEDIUM. Known limitation, addressed by retraining with more benign advisories, not by rule tuning.
BORDERLINE_ADVISORY = "Never click on links from unknown senders. Report suspicious messages at cybercrime.gov.in."

BENIGN_SERVICE_NOTICES = [
    "Dear Customer, your Sun Direct 82141058287 expires on 2026-10-06. Please renew in time to continue "
    "uninterrupted services.",
    "Your SBI card ending 1234 will expire on 31/10/2026. A replacement card has been dispatched to your "
    "registered address.",
    "Your Netflix membership will expire on 15 Oct. Renew from the official app to keep watching.",
    "Dear customer, your Airtel postpaid bill of Rs 499 is due on 12 Oct. Pay via the Airtel Thanks app to "
    "avoid late fees.",
    "Your Tata Play subscription 1234567890 is due for renewal on 2026-11-01. Thank you for being with us.",
    "Your LIC policy premium of Rs 12,450 is due on 15/11/2026.",
]


@pytest.mark.parametrize("text", BENIGN_SAFETY_WARNINGS)
def test_general_safety_warnings_are_low_risk(text):
    r = run_text(text)
    assert r.risk_level.value == "LOW", (r.risk_score, found(r))
    assert not any(f.severity == "critical" for f in r.findings)


def test_borderline_advisory_is_never_high():
    r = run_text(BORDERLINE_ADVISORY)
    assert r.risk_level.value in {"LOW", "MEDIUM"} and r.risk_score <= 35, r.risk_score


@pytest.mark.parametrize("text", BENIGN_SERVICE_NOTICES)
def test_service_reminders_are_never_high(text):
    r = run_text(text)
    assert r.risk_level.value in {"LOW", "MEDIUM"}, (r.risk_score, found(r))
    assert "ACCOUNT_THREAT" not in found(r)  # an expiry/renewal date is not a threat


def test_uncertain_reminder_is_medium_with_honest_wording():
    """Formal wording that resembles scams, but no tactic and no way to act: uncertain, not 'safe', not 'scam'."""
    r = run_text(BENIGN_SERVICE_NOTICES[0])
    assert r.risk_level.value == "MEDIUM" and r.classification.value == "SUSPICIOUS"
    model_match = next(f for f in r.findings if f.code == "TEXT_MODEL_MATCH")
    assert model_match.severity == "medium" and "not proof" in model_match.detail
    assert any("can't confirm whether it is genuine" in lim for lim in r.limitations)
    text_comp = next(c for c in r.breakdown.components if c.component == "text")
    assert any("model weight 45" in o for o in text_comp.overrides)


# ------------------------------------------------------------ scam regressions
SCAMS = [
    ("KYC phishing", "Dear customer your SBI account will be blocked today. Update KYC at http://sbi-kyc-verify.co/update"),
    ("Account-block threat", "Your electricity will be disconnected tonight at 9.30pm because your bill was not "
                             "updated. Call 9876543210 immediately."),
    ("KYC expiry pretext", "Your KYC has expired. Update it now or your account will be blocked."),
    ("Look-alike renewal link", "Your Sun Direct subscription has expired. Pay Rs 299 now at "
                                "http://sundirect-renew.xyz to avoid disconnection."),
    ("Look-alike URL", "PayPal: unusual activity. Your account is limited. Log in to restore access "
                       "http://paypa1-resolution.com/login"),
    ("QR receive-money trick", "Scan this QR code to receive Rs 5000 cashback in your account."),
    ("OTP request", "Please share the OTP you received with our executive to cancel the transaction."),
    ("Refund callback", "Norton Subscription renewed for $399.99. If you did not authorise this, call our "
                        "billing department on +1 808 555 0199."),
    ("Premium SMS spam", "I don't know u and u don't know me. Send CHAT to 86688 now and let's find each other! "
                         "Only 150p/Msg rcvd. HG/Suite342/2Lands/Row/W1J6HL LDN. 18 years or over."),
    ("Warning-wrapped scam", "Beware of fake agents. Our officer will call you; share the OTP to verify your account."),
    # Scams that borrow cautionary words must not be mistaken for warnings.
    ("'Be alert' opener", "Be alert: share the OTP sent to you with our officer to secure your account."),
    ("'Fraudsters may' opener", "Fraudsters may target you; share the OTP with our executive to secure your account."),
    ("'Be careful' threat", "Be careful, your account will be blocked today. Update KYC now."),
    ("'Beware of fraud' then PIN", "Beware of fraud. Enter your UPI PIN to receive the cashback of Rs 2000."),
    # Negation must not cross a comma ("Don't worry, just ...").
    ("Reassurance then QR trick", "Don't worry, just scan this QR code to receive Rs 500 refund."),
    ("Reassurance then OTP", "Don't worry, just share the OTP to complete your refund."),
]


@pytest.mark.parametrize("name,text", SCAMS, ids=[s[0] for s in SCAMS])
def test_known_scams_stay_high_or_critical(name, text):
    r = run_text(text)
    assert r.risk_level.value in {"HIGH", "CRITICAL"}, (name, r.risk_score, found(r))
    assert r.classification.value == "SCAM"


def test_benign_wording_does_not_hide_a_malicious_link():
    """A polite, legitimate-looking reminder still gets flagged by its look-alike link."""
    r = run_text("Dear Customer, your Sun Direct 82141058287 expires on 2026-10-06. Renew at "
                 "http://sundirect-renew-kyc.xyz/login to continue uninterrupted services.")
    assert r.risk_level.value in {"HIGH", "CRITICAL"}
    assert any(c.component == "url" and c.score >= 60 for c in r.breakdown.components)


# ------------------------------------------------------- screenshot and QR flows
def test_screenshot_of_safety_warning_is_not_high(client):
    png = chat_screenshot_png(BENIGN_SAFETY_WARNINGS[0], sender="BANK ALERT")
    body = client.post("/api/analyze/image", files={"file": ("w.png", png, "image/png")}).json()
    assert body["extracted"]["text_source"] == "ocr"
    assert body["risk_level"] in {"LOW", "MEDIUM"}, (body["risk_score"], [f["code"] for f in body["findings"]])


def test_screenshot_of_service_reminder_is_not_high(client):
    png = chat_screenshot_png(BENIGN_SERVICE_NOTICES[0], sender="SUNDTH")
    body = client.post("/api/analyze/image", files={"file": ("r.png", png, "image/png")}).json()
    assert body["risk_level"] in {"LOW", "MEDIUM"}, (body["risk_score"], [f["code"] for f in body["findings"]])


def test_phishing_screenshot_still_critical(client):
    png = chat_screenshot_png("Dear customer, your electricity will be disconnected tonight at 9.30pm because your "
                              "bill was not updated. Pay now at http://bill-update-power.online")
    body = client.post("/api/analyze/image", files={"file": ("p.png", png, "image/png")}).json()
    assert body["risk_level"] in {"HIGH", "CRITICAL"}


def test_qr_with_safety_text_is_not_high(client):
    body = client.post("/api/analyze/qr", files={"file": ("q.png", qr_png(BENIGN_SAFETY_WARNINGS[0]), "image/png")}).json()
    assert body["risk_level"] in {"LOW", "MEDIUM"}, body["risk_score"]


def test_suspicious_qr_payloads_stay_high(client):
    for payload in ("Scan to receive Rs 5000 cashback. Enter your UPI PIN to claim.",
                    "upi://pay?pa=refund.desk4521@ybl&pn=Refund%20Desk&am=4999&tn=Refund%20for%20cancelled%20order",
                    "http://sbi-kyc-verify.co/update"):
        body = client.post("/api/analyze/qr", files={"file": ("q.png", qr_png(payload), "image/png")}).json()
        assert body["risk_level"] in {"HIGH", "CRITICAL"}, (payload, body["risk_score"])


# ------------------------------------------------------------- unit: engine/rules
def _model(p):
    return ModelOutput(name="m", version="1", target="text", probability=p, label="scam" if p >= .5 else "legit")


def test_model_alone_cannot_reach_high_without_tactic_or_action():
    low_rule = Evidence(code="GENERIC_GREETING", label="g", severity="low", weight=3, source="t")
    c = risk.score_text("x", _model(1.0), [low_rule], actionable=False)
    assert c.score < 60 and c.model_points == 45.0


def test_full_model_weight_when_actionable_or_tactic_present():
    assert risk.score_text("x", _model(1.0), [], actionable=True).model_points == 70.0
    tactic = Evidence(code="URGENCY", label="u", severity="medium", weight=8, source="t")
    assert risk.score_text("x", _model(1.0), [tactic], actionable=False).model_points == 70.0


def test_critical_tactic_floor_still_applies_without_call_to_action():
    otp = Evidence(code="OTP_REQUEST", label="o", severity="critical", weight=18, source="t")
    assert risk.score_text("x", _model(0.05), [otp], actionable=False).score >= 60


@pytest.mark.parametrize("text,expected", [
    ("Do not scan any QR code received from unknown sources.", False),
    ("Never click links in messages like this one.", False),
    ("Beware of fraudsters asking you to scan a QR code.", False),
    ("Your plan expires on 2026-10-06. Please renew in time.", False),
    ("If you did not authorise this, call our billing team.", True),
    ("Scan the QR code at the counter to pay.", True),
    ("Reply YES to confirm.", True),
    ("Details at http://example.com/offer", True),
    ("Report suspicious messages at cybercrime.gov.in", False),  # official domain: not a scammer's channel
])
def test_call_to_action_detection(text, expected):
    assert has_call_to_action(text) is expected
