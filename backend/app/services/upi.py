"""UPI payment-intent analysis (upi://pay?...).

A UPI QR code is always an instruction to PAY the payee. The single most
common QR scam in India is "scan this to receive money" — which is
impossible. This analyzer states that fact deterministically.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

from app.schemas.analysis import Evidence

_VPA_RE = re.compile(r"^[a-z0-9._-]{2,256}@[a-z][a-z0-9.-]{1,64}$", re.I)
_PERSONAL_HANDLES = {"ybl", "ibl", "axl", "okaxis", "okhdfcbank", "okicici", "oksbi", "paytm", "apl", "upi"}


def parse_upi(payload: str) -> dict | None:
    parts = urlsplit(payload.strip())
    if parts.scheme.lower() != "upi":
        return None
    q = {k.lower(): v[0] for k, v in parse_qs(parts.query).items() if v}
    amount = None
    if "am" in q:
        try:
            amount = round(float(q["am"]), 2)
        except ValueError:
            amount = None
    return {
        "action": (parts.netloc or parts.path.strip("/")).lower() or "pay",
        "payee_vpa": q.get("pa"),
        "payee_name": q.get("pn"),
        "amount": amount,
        "currency": q.get("cu", "INR"),
        "note": q.get("tn"),
        "merchant_code": q.get("mc"),
    }


def upi_evidence(upi: dict) -> list[Evidence]:
    ev: list[Evidence] = []

    def add(code, label, severity, weight, detail=None, excerpt=None):
        ev.append(Evidence(code=code, label=label, severity=severity, weight=weight, source="upi_analyzer",
                           detail=detail, excerpt=excerpt))

    payee = upi.get("payee_vpa") or "unknown"
    add("UPI_PAYMENT_QR", "This QR code sends money FROM you to " + payee, "info", 0,
        "Every UPI QR code is a payment request. Scanning it can never put money into your account.")
    if upi.get("amount"):
        add("UPI_PRESET_AMOUNT", f"Amount pre-filled: ₹{upi['amount']:,.2f}", "high", 14,
            "A pre-filled amount is normal at a shop counter — but if someone sent you this QR to 'receive' "
            "money, a refund or a prize, it is a scam: you would be paying them.")
    if payee != "unknown" and not _VPA_RE.match(payee):
        add("UPI_MALFORMED_PAYEE", "Payee UPI ID looks malformed", "medium", 8, excerpt=payee)
    handle = payee.split("@")[-1].lower() if "@" in payee else ""
    if handle in _PERSONAL_HANDLES and not upi.get("merchant_code"):
        add("UPI_PERSONAL_PAYEE", "Pays a personal UPI ID, not a registered merchant", "low", 5,
            "Businesses usually have merchant QR codes. Payments to personal IDs are hard to dispute.", payee)
    note = (upi.get("note") or "").lower()
    if re.search(r"refund|cashback|prize|reward|receive|kyc|verify|lottery|bonus", note):
        add("UPI_BAIT_NOTE", "Payment note uses refund/prize wording", "critical", 18,
            "The note suggests you'll receive money, but scanning this QR would send money out.", upi.get("note"))
    return ev
