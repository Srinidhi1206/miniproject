"""Deterministic 'What you should do' actions, derived from evidence codes.

Advice is selected by what was actually found — never generated freely — so
it can't contradict the verdict or invent facts.
"""

from __future__ import annotations

from app.schemas.analysis import Evidence, Recommendation, RiskLevel

_CATALOG: dict[str, Recommendation] = {r.id: r for r in [
    Recommendation(id="no_otp", priority="critical", title="Don't share any OTP, PIN or code",
                   detail="No bank, app, courier or official will ever ask for it. Sharing it hands over your account."),
    Recommendation(id="no_pin_receive", priority="critical", title="Never enter your UPI PIN to 'receive' money",
                   detail="Your PIN is only for sending money. Receiving money needs no PIN, no QR scan and no approval."),
    Recommendation(id="no_pay", priority="critical", title="Don't send money or pay any 'fee'",
                   detail="Genuine jobs, loans, prizes and refunds never require you to pay first."),
    Recommendation(id="no_click", priority="critical", title="Don't open the link",
                   detail="If you already opened it, don't enter any details. Close the page and clear the tab."),
    Recommendation(id="no_install", priority="critical", title="Don't install any app they suggest",
                   detail="Remote-access or .apk apps let criminals control your phone. If installed, uninstall it and "
                          "change your banking passwords from a different device."),
    Recommendation(id="hang_up_authority", priority="critical", title="Hang up — real police don't arrest over video calls",
                   detail="'Digital arrest' is not a legal procedure. Call 1930 or your local police station directly."),
    Recommendation(id="dont_scan", priority="critical", title="Don't scan this QR code to receive money",
                   detail="Scanning a UPI QR code always pays the owner of the code."),
    Recommendation(id="verify_official", priority="important", title="Verify through an official channel",
                   detail="Contact the organisation using the number on your card, their official app or website — "
                          "not a number or link from the message."),
    Recommendation(id="call_family", priority="important", title="Call the person on their known number",
                   detail="Before helping a 'relative' or 'boss' with money, call them on the number you already have."),
    Recommendation(id="no_details", priority="important", title="Don't share personal or banking details",
                   detail="Passwords, card numbers, CVV, Aadhaar or PAN should never be sent over chat, SMS or unknown links."),
    Recommendation(id="dont_reply", priority="important", title="Don't reply or engage",
                   detail="Replying confirms your number is active and invites more scam attempts. Block the sender."),
    Recommendation(id="report", priority="general", title="Report it",
                   detail="Report on SENTINEL to warn others, and at cybercrime.gov.in or helpline 1930 (India) — "
                          "especially if money was lost. Reporting within hours improves the chance of recovery."),
    Recommendation(id="already_paid", priority="general", title="If you already paid or shared details",
                   detail="Call 1930 immediately, then your bank to block cards/UPI. Change passwords and enable 2-step verification."),
    Recommendation(id="stay_alert", priority="general", title="Stay alert anyway",
                   detail="No automated check is perfect. If anything later asks for money, codes or urgency — stop and verify."),
    Recommendation(id="pay_only_if_intended", priority="important", title="Only scan to pay someone you intended to pay",
                   detail="Check the payee name and amount on your UPI app's confirmation screen before entering your PIN."),
    # Scenario-specific advice (see rag/scenarios.py): chosen from what the content is about, never from guesses.
    Recommendation(id="renew_official", priority="important", title="Renew only through the official app or website",
                   detail="Open the provider's app or type its website address yourself, or call the number on your bill "
                          "or device. Don't use a number or link sent in a message."),
    Recommendation(id="kyc_official", priority="important", title="Do KYC only in your bank's app or branch",
                   detail="Banks never complete KYC through a link, a call or a message. Never send documents, OTPs or "
                          "passwords to 'update KYC'."),
    Recommendation(id="qr_check_destination", priority="important", title="Don't open where this QR code leads",
                   detail="SENTINEL checked the link inside the QR code without opening it. If you need the service, go to "
                          "the organisation's official website or app yourself."),
]}

# Scenario advice that supersedes the generic "verify through an official channel" (it says the same, more precisely).
_SCENARIO_RECS = {"renewal": "renew_official", "kyc": "kyc_official"}

_BY_CODE: dict[str, list[str]] = {
    "OTP_REQUEST": ["no_otp"],
    "PIN_REQUEST": ["no_pin_receive", "no_otp"],
    "RECEIVE_MONEY_TRICK": ["no_pin_receive", "dont_scan"],
    "SENSITIVE_DATA": ["no_details"],
    "DIGITAL_ARREST": ["hang_up_authority"],
    "AUTHORITY_CLAIM": ["verify_official"],
    "ACCOUNT_THREAT": ["verify_official"],
    "UPFRONT_FEE": ["no_pay"],
    "PAYMENT_REQUEST": ["no_pay"],
    "PRIZE": ["no_pay", "dont_reply"],
    "UNREALISTIC_RETURNS": ["no_pay"],
    "TASK_JOB": ["no_pay"],
    "REMOTE_ACCESS": ["no_install"],
    "GIFT_CARDS": ["no_pay", "call_family"],
    "MISDIRECTED_MONEY": ["verify_official", "no_pay"],
    "FAMILY_EMERGENCY": ["call_family"],
    "THREAT_EXPOSURE": ["dont_reply"],
    "SECRECY": ["call_family"],
    "BRAND_IMPERSONATION": ["no_click", "verify_official"],
    "TYPOSQUAT": ["no_click", "verify_official"],
    "RISKY_DOWNLOAD": ["no_install", "no_click"],
    "REPUTATION_MALICIOUS": ["no_click"],
    "IP_HOST": ["no_click"],
    "SHORTENER": ["no_click"],
    "UPI_BAIT_NOTE": ["dont_scan", "no_pin_receive"],
    "UPI_PRESET_AMOUNT": ["pay_only_if_intended"],
    "UPI_PAYMENT_QR": ["pay_only_if_intended"],
}
_PRIORITY = {"critical": 0, "important": 1, "general": 2}


def recommend(level: RiskLevel, findings: list[Evidence], has_risky_url: bool,
              scenarios: set[str] | None = None) -> list[Recommendation]:
    """`scenarios` (what the content is about, see rag/scenarios.py) only selects more specific advice."""
    scenarios = scenarios or set()
    ids: list[str] = []

    def add(*rids: str) -> None:
        ids.extend(r for r in rids if r not in ids)

    if level != RiskLevel.LOW:  # protective "don't ..." steps only when there is something to protect against
        for e in sorted(findings, key=lambda e: -e.weight):
            add(*_BY_CODE.get(e.code, []))
        if has_risky_url:
            add("no_click")
        if "qr_link" in scenarios and has_risky_url:
            add("qr_check_destination")
    elif any(e.code in ("UPI_PAYMENT_QR", "UPI_PRESET_AMOUNT") for e in findings):
        add("pay_only_if_intended")  # a genuine payment QR still deserves a payee check
    add(*(_SCENARIO_RECS[s] for s in ("kyc", "renewal") if s in scenarios))

    tactics = [e for e in findings if e.weight > 0 and e.severity in ("medium", "high", "critical")]
    if level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        add("dont_reply", "report", "already_paid")
    elif level == RiskLevel.MEDIUM:
        add("verify_official")
        if tactics:  # reporting a probably-genuine reminder with no tactic would be poor advice
            add("report")
    else:
        add("stay_alert")
    if any(rid in ids for rid in _SCENARIO_RECS.values()):
        ids = [r for r in ids if r != "verify_official"]
    recs = [_CATALOG[i] for i in ids]
    return sorted(recs, key=lambda r: _PRIORITY[r.priority])[:7]
