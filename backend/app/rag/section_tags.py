"""Which evidence each knowledge-base *section* explains.

Guide-level tags (front matter) say what a whole guide is about, which is right for
linking to the Safety Center but too coarse for "Why this matters": a weak signal
such as a generic greeting made every section of the phishing guide eligible, so a
renewal reminder with no link was shown the guide's SBI link-checking example.

Explanations therefore only use sections listed here, and only when one of the
section's codes was actually found. Sections not listed here (warning-sign lists,
"what to do" lists, password or SIM hygiene ...) are for reading in the Safety
Center, not for explaining a specific result. Keys must match `## ` headings
exactly; tests/test_explanations.py fails if a guide heading changes.
"""

from __future__ import annotations

SECTION_TAGS: dict[tuple[str, str], tuple[str, ...]] = {
    ("upi-safety", "The one rule that stops most UPI fraud"):
        ("PIN_REQUEST", "RECEIVE_MONEY_TRICK", "UPI_BAIT_NOTE", "UPI_PRESET_AMOUNT"),
    ("upi-safety", "How collect-request scams work"): ("RECEIVE_MONEY_TRICK",),
    ("upi-safety", 'The "sent by mistake" trick'): ("MISDIRECTED_MONEY",),

    ("otp-pin-safety", "Why scammers want your OTP"): ("OTP_REQUEST",),
    ("otp-pin-safety", "Who can legitimately ask for it"): ("OTP_REQUEST", "PIN_REQUEST", "SENSITIVE_DATA"),

    ("phishing", "How phishing works"): ("ACCOUNT_THREAT", "SENSITIVE_DATA"),
    ("phishing", "Why urgency is the main tactic"): ("URGENCY", "ACCOUNT_THREAT"),
    # "Checking a link safely" is deliberately absent: it is illustrated with a fixed SBI look-alike address,
    # which isn't the user's link. Results explain their own link instead (explainer._specific_lines).

    ("fake-websites", "Look-alike domains"): ("BRAND_IMPERSONATION", "TYPOSQUAT", "PUNYCODE", "HYPHENATED_HOST"),
    ("fake-websites", "The padlock myth"): ("NO_HTTPS",),
    ("fake-websites", "Free hosting and cheap domain endings"): ("FREE_HOSTING", "SUSPICIOUS_TLD"),
    ("fake-websites", "Links that download apps"): ("RISKY_DOWNLOAD",),

    ("job-scams", "Fee-based fake job offers"): ("UPFRONT_FEE",),
    ("job-scams", "How task scams work"): ("TASK_JOB",),

    ("qr-scams", '"Scan to receive" is always a lie'): ("RECEIVE_MONEY_TRICK", "UPI_BAIT_NOTE"),

    ("social-engineering", "Impersonating people you trust"): ("FAMILY_EMERGENCY",),
    ("social-engineering", "Fear, greed and secrecy"): ("SECRECY",),
    ("social-engineering", "Remote-access apps"): ("REMOTE_ACCESS",),
    ("social-engineering", "Prizes you never entered"): ("PRIZE",),
    ("social-engineering", "Extortion threats"): ("THREAT_EXPOSURE",),

    ("digital-arrest", "How the scam unfolds"): ("DIGITAL_ARREST",),
    ("digital-arrest", "Why it is always fake"): ("DIGITAL_ARREST", "AUTHORITY_CLAIM"),

    ("investment-scams", "Too good to be true"): ("UNREALISTIC_RETURNS",),
    ("investment-scams", "How trading-group scams work"): ("CRYPTO_INVEST",),
}
