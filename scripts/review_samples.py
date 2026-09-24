"""Manual-review sample set: realistic, clearly labelled, fictional inputs sent
through the RUNNING API (real pipelines, no mocks).

    backend/.venv/Scripts/python scripts/review_samples.py [--api http://localhost:8000]

Images (QR codes, screenshots) are generated into samples/ so they can also be
used for live demos by uploading them in the UI. Every message, domain, UPI ID
and phone number here is fictional or a well-known public site.

"expect" is the reviewer's judgement of a sensible outcome, NOT a model output:
  safe       -> LOW
  suspicious -> MEDIUM or higher
  scam       -> HIGH or CRITICAL
  error:CODE -> a friendly error with that code
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from tests.fixtures import blank_png, chat_screenshot_png, qr_png  # noqa: E402

SAMPLES = ROOT / "samples"

MESSAGES = [
    ("safe", "Personal message", "Hey, are we still meeting at 7 near the cafe? Let me know if you're running late."),
    ("safe", "Informational notice", "Society notice: Water supply will be interrupted on Saturday 9 AM to 1 PM due to tank cleaning."),
    ("safe", "Genuine bank OTP", "482913 is your OTP for login to HDFC Bank NetBanking. Do not share this OTP with anyone."),
    ("safe", "Genuine delivery update", "Your Amazon order of 'USB-C cable' has been shipped and will arrive by Thursday. Track it in the Amazon app."),
    ("scam", "Urgent payment request", "Hi Mom, I lost my phone, this is my new number. I need to pay an urgent hospital bill, please send Rs 15,000 to this account right now."),
    ("scam", "Fake KYC", "Dear customer, your SBI account will be blocked today due to pending KYC. Update PAN immediately at http://sbi-kyc-verify.co/update"),
    ("scam", "Fake job offer", "Congratulations! You are selected for a work from home job. Earn Rs 5000 daily by liking YouTube videos. Pay Rs 499 registration fee to start."),
    ("scam", "UPI scam", "I am buying your bike on OLX. I will pay via QR code. Scan it and enter your UPI PIN to receive Rs 25,000."),
    ("suspicious", "Unexpected delivery link", "Your parcel could not be delivered. Reschedule here: http://parcel-reschedule-now.xyz"),
]

URLS = [
    ("safe", "Legitimate bank site", "https://www.onlinesbi.sbi/"),
    ("safe", "Legitimate government site", "https://cybercrime.gov.in/"),
    ("safe", "Legitimate everyday site", "https://en.wikipedia.org/wiki/Phishing"),
    ("scam", "Brand look-alike", "http://paypa1-resolution.com/login/verify"),
    ("scam", "KYC phishing on cheap TLD", "https://hdfc-netbanking-update.xyz/kyc"),
    ("suspicious", "Shortened link", "https://bit.ly/3xVidz0"),
    ("scam", "APK download", "http://quick-loan-app.online/download/loan.apk"),
    ("error:INVALID_URL", "Not a URL", "javascript:alert(1)"),
]


def build_images() -> list[tuple[str, str, str, str]]:
    SAMPLES.mkdir(exist_ok=True)
    files = {
        "qr_safe_website.png": qr_png("https://www.irctc.co.in/"),
        "qr_suspicious_url.png": qr_png("http://sbi-rewards-claim.xyz/kyc/login"),
        "qr_upi_refund_bait.png": qr_png("upi://pay?pa=refund.desk@ybl&pn=Refund%20Desk&am=4999&tn=Cashback%20refund%20receive"),
        "qr_undecodable_blank.png": blank_png(),
        "screenshot_scam_text.png": chat_screenshot_png(
            "URGENT: Your Paytm KYC has expired. Your wallet will be blocked today. "
            "Share the OTP sent to your phone with our executive to reactivate."),
        "screenshot_with_url.png": chat_screenshot_png(
            "Dear customer, your electricity will be disconnected tonight at 9.30pm because your bill was not "
            "updated. Pay now at http://bill-update-power.online"),
        "screenshot_safe_chat.png": chat_screenshot_png("Reached home safely. Thanks for dropping me at the station!", sender="Ananya"),
        "image_no_text.png": blank_png(color=(210, 225, 235), size=(640, 480)),
    }
    for name, data in files.items():
        (SAMPLES / name).write_bytes(data)
    return [
        ("safe", "QR: safe website", "qr", "qr_safe_website.png"),
        ("scam", "QR: suspicious URL", "qr", "qr_suspicious_url.png"),
        ("scam", "QR: UPI refund bait", "qr", "qr_upi_refund_bait.png"),
        ("error:QR_NOT_FOUND", "QR: cannot be decoded", "qr", "qr_undecodable_blank.png"),
        ("scam", "Screenshot: scam text", "image", "screenshot_scam_text.png"),
        ("scam", "Screenshot: scam text + URL", "image", "screenshot_with_url.png"),
        ("safe", "Screenshot: normal chat", "image", "screenshot_safe_chat.png"),
        ("error:NO_CONTENT", "Image with no readable text", "image", "image_no_text.png"),
    ]


def verdict_ok(expect: str, body: dict, status: int) -> bool:
    if expect.startswith("error:"):
        return status >= 400 and body.get("error", {}).get("code") == expect.split(":", 1)[1]
    level = body.get("risk_level")
    return {"safe": level == "LOW", "suspicious": level in {"MEDIUM", "HIGH", "CRITICAL"},
            "scam": level in {"HIGH", "CRITICAL"}}[expect]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    args = ap.parse_args()
    client = httpx.Client(base_url=args.api, timeout=60, headers={"X-Sentinel-Client": "review-samples-0001"})
    rows = []

    for expect, name, text in MESSAGES:
        r = client.post("/api/analyze/text", json={"text": text, "channel": "sms"})
        rows.append((expect, "message", name, r.status_code, r.json()))
    for expect, name, url in URLS:
        r = client.post("/api/analyze/url", json={"url": url})
        rows.append((expect, "url", name, r.status_code, r.json()))
    for expect, name, kind, fname in build_images():
        with open(SAMPLES / fname, "rb") as f:
            r = client.post(f"/api/analyze/{kind}", files={"file": (fname, f, "image/png")})
        rows.append((expect, kind, name, r.status_code, r.json()))

    ok = 0
    for expect, kind, name, status, body in rows:
        good = verdict_ok(expect, body, status)
        ok += good
        if "error" in body:
            outcome = f"{status} {body['error']['code']}: {body['error']['message']}"
        else:
            outcome = (f"{body['risk_level']:8} {body['risk_score']:3}  "
                       + ", ".join(f["code"] for f in body["findings"][:4]))
        print(f"{'OK ' if good else 'CHECK'} [{kind:7}] {name:30} expect={expect:18} -> {outcome}")
    print(f"\n{ok}/{len(rows)} outcomes matched the reviewer's expectation.")
    (SAMPLES / "review_results.json").write_text(json.dumps(
        [{"expect": e, "kind": k, "name": n, "status": s, "risk_level": b.get("risk_level"),
          "risk_score": b.get("risk_score"), "findings": [f["code"] for f in b.get("findings", [])],
          "error": b.get("error")} for e, k, n, s, b in rows], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
