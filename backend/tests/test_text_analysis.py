import pytest

from app.ml.text.indicators import detect_indicators
from app.ml.text.model import get_text_detector
from app.ml.text.preprocess import extract_urls, normalise


def codes(text):
    return {e.code for e in detect_indicators(text, normalise(text))}


@pytest.mark.parametrize("text,expected", [
    ("Please share the OTP you received to cancel the transaction", "OTP_REQUEST"),
    ("Enter your UPI PIN to receive Rs 2,000 cashback", "PIN_REQUEST"),
    ("Scan this QR code to receive your refund of Rs 500", "RECEIVE_MONEY_TRICK"),
    ("You are under digital arrest. Do not disconnect the video call", "DIGITAL_ARREST"),
    ("Your account will be blocked today, update KYC", "ACCOUNT_THREAT"),
    ("Pay Rs 2,999 registration fee to get the offer letter", "UPFRONT_FEE"),
    ("Install AnyDesk so our engineer can fix your account", "REMOTE_ACCESS"),
    ("Earn Rs 5000 daily from home, guaranteed", "UNREALISTIC_RETURNS"),
    ("Hi Mom, I lost my phone, this is my new number", "FAMILY_EMERGENCY"),
])
def test_rules_fire_on_scam_tactics(text, expected):
    assert expected in codes(text)


def test_negated_otp_warning_is_not_a_request():
    found = codes("482913 is your OTP for login. Do not share this OTP with anyone.")
    assert "OTP_REQUEST" not in found
    assert "SAFETY_ADVICE" in found


def test_casual_message_has_no_indicators():
    assert {c for c in codes("Are we still meeting at 7 near the cafe?")} == set()


def test_normalise_replaces_entities():
    n = normalise("Pay Rs 2,999 at http://x-pay.xyz or call 9876543210")
    assert "moneytoken" in n and "urltoken" in n and "phonetoken" in n


def test_extract_urls_ignores_emails_and_dedupes():
    urls = extract_urls("Mail hr@company.com or visit http://a-b.xyz/x, again http://a-b.xyz/x and bit.ly/abc")
    assert urls == ["http://a-b.xyz/x", "bit.ly/abc"]


def test_text_model_separates_scam_from_benign():
    d = get_text_detector()
    scam = d.predict("URGENT: your SBI account is blocked. Update KYC now at http://sbi-kyc.xyz to avoid suspension")
    benign = d.predict("Hey, can you send me the notes from today's lecture?")
    assert scam.probability > 0.8 > 0.2 > benign.probability
    assert scam.label == "scam" and benign.label == "legit"
    assert all(f.weight > 0 for f in scam.top_features)
