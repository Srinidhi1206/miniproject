"""Deterministic scam-indicator rules for text.

Each rule is a named, weighted regular expression. Rules are the
*explainable* half of text analysis: the ML model estimates how much the
message resembles known scams overall; rules name the specific tactics.

Weights feed the risk engine (see docs/ml-pipeline.md → Risk engine). They are
deliberately small integers so the score can be audited by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ml.text.preprocess import EMAIL_RE, extract_urls
from app.schemas.analysis import Evidence, Severity

# Negation must not reach across clause punctuation: in "Don't worry, just share the OTP" the request is
# NOT negated.
_NEGATION = re.compile(r"(?:never|not|n't|dont|don't|do not)[^\w,;:.!?]+(?:\w+[^\w,;:.!?]+){0,2}$", re.I)
_NEGATION_INSIDE = re.compile(r"\b(?:never|do not|don't|dont)\s+(?:share|send|tell|give|forward)\b", re.I)
# A sentence that *describes* what scammers do ("Beware of fraudsters asking you to scan a QR code to
# receive money") is a warning, not a request, so tactic rules must not fire on it. Deliberately narrow:
# the tactic must be the object of a describing verb whose subject is the scammer. A bare "Be alert:" or
# "Fraudsters may target you; share the OTP ..." does not qualify, because scammers write those too.
_WARNING_FRAME = re.compile(
    r"\b(?:fraudsters?|scammers?|criminals?|cheats?|fake\s+(?:callers?|agents?|officials?|apps?|websites?))\b"
    r"(?:\s+who)?\s+(?:(?:may|might|will|often|can|usually)\s+)?"
    r"(?:ask\w*|tell\w*|urg\w+|pressur\w+|trick\w*|convinc\w+|offer\w*|claim\w*|pretend\w*|send\w*|lure\w*)"
    r"(?:\s+(?:you|people|victims|customers|users))?(?:\s+to)?(?:\s+\w+){0,4}\s+$",
    re.I)
# Ways a message can get the reader to act through a channel the sender controls. A message with none of
# these and no named tactic cannot defraud anyone by itself, so the risk engine gives model similarity
# less weight (see risk/engine.py, "uncorroborated text").
_CALL_TO_ACTION = re.compile(
    r"\b(?:click|tap|visit|open|log\s*-?\s*in|login|sign\s*-?\s*in|download|install|scan|call|dial|ring|sms|text|txt|"
    r"texting|txting|rply|chat\s+(?:now|to)|whatsapp|reply|respond|send|pay|transfer|deposit|purchase|buy|order|"
    r"register|apply|claim|redeem|verify|validate|update|confirm|share|submit|enter|contact|activate|unlock|join)\b",
    re.I)
# Negation for a call to action must sit directly on the verb ("do not scan", "never click any") and must not
# reach across punctuation: in "If you did not authorise this, call us" the call is NOT negated.
_CTA_NEGATION = re.compile(r"\b(?:never|not|n't|dont|don't|do\s+not|avoid)\s+(?:\w+\s+)?$", re.I)


@dataclass(frozen=True)
class Rule:
    code: str
    label: str
    severity: Severity
    weight: int
    pattern: re.Pattern
    detail: str
    negatable: bool = False  # ignore matches preceded by "never/do not ..."


def _r(p: str) -> re.Pattern:
    return re.compile(p, re.I | re.S)


RULES: list[Rule] = [
    Rule("OTP_REQUEST", "Asks you to share an OTP or verification code", "critical", 18,
         _r(r"\b(?:share|send|tell|give|forward|read\s*out|provide|reply\s+with|say)\b[^.\n]{0,40}\b(?:otp|one[\s-]?time\s+password|verification\s+code|\d[\s-]?digit\s+code|the\s+code)\b"
            r"|\b(?:otp|verification\s+code)\b[^.\n]{0,25}\b(?:share|send|tell|forward)\b(?!\s+(?:it\s+)?with\s+anyone)"),
         "Banks, apps and officials never need your OTP. Anyone holding it can take over your account or approve payments.",
         negatable=True),
    Rule("PIN_REQUEST", "Asks you to enter or share your UPI PIN / card PIN", "critical", 18,
         _r(r"\b(?:enter|share|tell|give|type|input|provide)\b[^.\n]{0,30}\b(?:upi\s+)?(?:pin|mpin|cvv)\b"),
         "A UPI PIN is only ever used to SEND money. You never need it to receive money or a refund.",
         negatable=True),
    Rule("RECEIVE_MONEY_TRICK", "Claims you'll receive money by scanning a QR or approving a request", "critical", 16,
         _r(r"\b(?:scan|approve|accept)\b[^.\n]{0,50}\b(?:receive|get|credit|claim)\b[^.\n]{0,30}\b(?:money|amount|payment|cashback|refund|reward|rs|moneytoken|\d)"
            r"|\b(?:receive|get|credit)\b[^.\n]{0,40}\b(?:money|amount|payment|cashback|refund|reward)\b[^.\n]{0,40}\b(?:scan|enter[^.\n]{0,10}pin|approve|accept\s+the\s+(?:collect\s+)?request)"
            r"|\b(?:accept|approve)\b[^.\n]{0,20}\bcollect\s+request"),
         "Scanning a QR code or approving a UPI 'collect' request moves money OUT of your account, never in."),
    Rule("SENSITIVE_DATA", "Requests passwords, card or identity details", "high", 12,
         _r(r"\b(?:send|share|submit|update|enter|provide|verify|tell|confirm|give)\b[^.\n]{0,40}\b(?:password|cvv|card\s+(?:number|details)|\d{2}[\s-]?digit\s+(?:card\s+)?number|net\s*banking|login\s+details|bank\s+(?:account\s+)?details|account\s+details|aadhaar|pan(?:\s+card|\s+number)?|credentials|policy\s+number)\b"),
         "Legitimate organisations never collect passwords or full card details over messages or links.",
         negatable=True),
    Rule("DIGITAL_ARREST", "Threatens arrest or a police/legal case", "critical", 16,
         _r(r"\bdigital\s+arrest\b|\barrest\s+warrant\b|\bmoney\s+laundering\b|\b(?:fir|case)\s+(?:is\s+)?(?:registered|filed)\b|\bunder\s+arrest\b|\billegal\s+(?:items|activity|parcel)|\bdrugs?\b[^.\n]{0,30}\b(?:seized|parcel)"),
         "Police and agencies never arrest people over video calls or demand money to 'clear your name'. 'Digital arrest' does not exist."),
    Rule("AUTHORITY_CLAIM", "Claims to be from police, a regulator or the government", "high", 10,
         _r(r"\b(?:cbi|cyber\s*(?:cell|police|crime\s+branch)|customs\s+(?:department|officer)|income\s+tax\s+(?:department|officer)|rbi\b|trai\b|narcotics|enforcement\s+directorate|police\s+officer|investigation\s+officer|mumbai\s+police|delhi\s+police)"),
         "Scammers impersonate authorities because fear makes people act without checking."),
    Rule("ACCOUNT_THREAT", "Threatens to block, suspend or disconnect your account or service", "high", 10,
         # A plain expiry or renewal date is ordinary service information, not a threat. Only KYC "expiry"
         # (a common scam pretext: KYC does not expire) is treated as one.
         _r(r"\b(?:account|a/c|card|sim|number|connection|wallet|kyc|fastag|netbanking|power|electricity|mailbox|membership|policy|service)\b[^.\n]{0,50}\b(?:block(?:ed)?|suspend(?:ed)?|deactivat\w*|frozen|freez\w*|clos(?:ed|e)|disconnect\w*|lock(?:ed)?|terminat\w*|blacklist\w*|delet(?:ed|e)|cut)\b"
            r"|\bkyc\b[^.\n]{0,30}\b(?:expir(?:ed|e|es)|lapsed)\b"),
         "Threats of losing access create panic so you act before verifying. Real providers give written notice through official channels."),
    Rule("URGENCY", "Uses urgency or a tight deadline", "medium", 8,
         _r(r"\burgent(?:ly)?\b|\bimmediately\b|\bwithin\s+(?:numtoken|\d+|one|two|24|48)\s*(?:hours?|hrs?|minutes?|mins?)\b|\bin\s+(?:\d+|one|two)\s+(?:hours?|hrs?|minutes?)\b|\btoday\s+only\b|\blast\s+(?:warning|chance|notice|date)\b|\bfinal\s+(?:notice|warning|step)\b|\bbefore\s+midnight\b|\bact\s+now\b|\bright\s+now\b|\bhurry\b|\btonight\b|\bexpires?\s+today\b|\blimited\s+(?:seats|time|offer)\b|\bvalid\s+today\b"),
         "Pressure to act 'now' is the most common scam tactic — it stops you from pausing to check."),
    Rule("UPFRONT_FEE", "Demands an upfront fee, deposit or charge", "high", 12,
         _r(r"\b(?:registration|processing|verification|clearance|security|refundable|joining|training|shipping|release|insurance|customs|gst)\s+(?:fee|fees|charge|charges|deposit|amount|tax)\b|\bpay\b[^.\n]{0,25}\b(?:fee|charges|deposit|tax)\b"),
         "Real employers, lenders and prize-givers never ask you to pay first to receive a job, loan or prize."),
    Rule("PAYMENT_REQUEST", "Asks you to pay or transfer money", "high", 10,
         _r(r"\b(?:pay|transfer|send|deposit|remit)\b[^.\n]{0,30}(?:moneytoken|\brs\.?\s?\d|₹\s?\d|\binr\b|\$\s?\d|\bmoney\b|\bamount\b|\badvance\b|\bfine\b|\bfees?\b)|\bsend\s+me\b[^.\n]{0,20}\b(?:\d|money)"),
         "Unexpected requests to send money — especially to a new account or UPI ID — are how most scam losses happen."),
    Rule("PRIZE", "Promises an unexpected prize, reward or cashback", "medium", 8,
         _r(r"\b(?:you\s+(?:have\s+)?won|winner|lucky\s+draw|lottery|jackpot|prize|cashback|reward\s+points|scratch\s+card|free\s+recharge|bonanza|you\s+are\s+(?:the\s+)?(?:selected|chosen)\s+(?:for\s+)?(?:a\s+)?(?:prize|reward|gift))\b"),
         "You can't win a lottery or draw you never entered. 'Prizes' are bait for fees or personal details."),
    Rule("UNREALISTIC_RETURNS", "Promises unrealistic earnings or guaranteed returns", "high", 10,
         _r(r"\bguaranteed\b|\bdouble\s+your\b|\b\d{2,3}\s?%\s+(?:returns?|profit|daily)|\bdaily\s+(?:profit|interest|income|payout)\b|\bearn\b[^.\n]{0,20}(?:moneytoken|rs\.?\s?\d|₹\s?\d|\d[\d,]*)[^.\n]{0,15}(?:per\s+day|daily|/\s?day|a\s+day|per\s+week|per\s+review)|\brisk[\s-]free\b|\b100\s?%\s+safe\b|\b\d+x\s+returns\b|\binsider\s+tips?\b"),
         "No legitimate investment or job guarantees high, fast returns. This is the core promise of investment and task scams."),
    Rule("TASK_JOB", "Easy online 'task' or part-time job offer", "medium", 8,
         _r(r"\b(?:part[\s-]?time|work\s+from\s+home|online\s+(?:job|work)|daily\s+payout|like\s+(?:youtube\s+)?videos|rate\s+(?:hotels|products)|(?:simple|prepaid|online)\s+tasks?|product\s+review\s+job|forwarding\s+messages)\b"),
         "'Like videos / rate hotels / complete tasks' jobs start with small payouts, then ask you to deposit money to 'unlock' larger tasks."),
    Rule("REMOTE_ACCESS", "Asks you to install a remote-access or unknown app", "critical", 16,
         _r(r"\b(?:anydesk|teamviewer|quick\s*support|rustdesk|airdroid|screen\s*shar\w*)\b|\.apk\b|\bnot\s+on\s+play\s*store\b|\ballow\s+(?:contacts|sms)\s+access\b|\bdownload\b[^.\n]{0,30}\bcleaner\s+app\b"),
         "Remote-access and side-loaded apps let criminals see your screen, read your OTPs and operate your banking apps."),
    Rule("SECRECY", "Asks you to keep it secret or stay on the call", "high", 10,
         _r(r"\b(?:don'?t|do\s+not|dont)\s+(?:tell|inform|share\s+this\s+with)\s+(?:anyone|your\s+family|family|anybody)\b|\b(?:don'?t|do\s+not)\s+disconnect\b|\bkeep\s+(?:this|it)\s+(?:secret|confidential)\b"),
         "Isolating you from family or friends is a hallmark of 'digital arrest' and romance scams."),
    Rule("GIFT_CARDS", "Asks for gift cards or voucher codes", "high", 12,
         _r(r"\bgift\s+cards?\b|\b(?:itunes|google\s+play|amazon)\s+(?:gift\s+)?(?:cards?|vouchers?)\b|\bsend\s+(?:me\s+)?the\s+codes\b"),
         "Gift card codes are untraceable cash. No company, boss or official asks to be paid in gift cards."),
    Rule("MISDIRECTED_MONEY", "Claims money was sent to you by mistake", "high", 10,
         _r(r"\b(?:sent|transferred|credited)\b[^.\n]{0,40}\b(?:by\s+mistake|wrongly|accidentally|mistakenly)\b|\bby\s+mistake\b[^.\n]{0,40}\b(?:return|send\s+(?:it\s+)?back)\b"),
         "Check your own bank app — 'wrong transfer' messages are usually fake, and the 'refund' goes to the scammer."),
    Rule("FAMILY_EMERGENCY", "Emergency appeal from a 'new number' or relative", "high", 10,
         _r(r"\b(?:lost\s+my\s+phone|this\s+is\s+my\s+new\s+number|new\s+number)\b|\b(?:had\s+an\s+accident|in\s+(?:the\s+)?hospital)\b[^.\n]{0,60}\b(?:send|transfer|pay)\b"),
         "Call the person on their known number before sending anything. Scammers impersonate family to trigger panic."),
    Rule("THREAT_EXPOSURE", "Threatens to leak photos, videos or personal data", "critical", 16,
         _r(r"\b(?:upload|leak|send|share|post)\b[^.\n]{0,40}\b(?:video|photos?|pictures?)\b[^.\n]{0,40}\b(?:family|contacts|friends|youtube|social)|\bmorphed\b"),
         "Extortion threats escalate if you pay. Don't pay — save evidence and report to cybercrime.gov.in or 1930."),
    Rule("CRYPTO_INVEST", "Crypto or trading investment pitch", "medium", 6,
         _r(r"\b(?:bitcoin|usdt|crypto(?:currency)?|forex|trading\s+bot|mining\s+pool|ipo\s+allotment|block\s+trades?)\b"),
         "Unregulated crypto and 'VIP trading group' offers are a leading cause of large scam losses."),
    Rule("CALL_UNKNOWN_NUMBER", "Pushes you to call or WhatsApp an unknown number", "low", 5,
         _r(r"\b(?:call|contact|whatsapp|dial|press\s+\d)\b[^.\n]{0,40}(?:phonetoken|\+?\d[\d\s-]{8,}\d|\d{4,5}x{2,}\d+)|\bpress\s+[0-9]\b"),
         "Always use the number printed on your card or the official website — not one given in a message."),
    Rule("MESSAGING_REDIRECT", "Moves the conversation to WhatsApp/Telegram groups", "low", 4,
         _r(r"\bwa\.me\b|\bt\.me\b|\btelegram\b|\bjoin\b[^.\n]{0,25}\b(?:group|channel)\b"),
         "Scammers move you to private chats to avoid platform moderation."),
    Rule("GENERIC_GREETING", "Generic greeting instead of your name", "low", 3,
         _r(r"^\s*(?:dear\s+(?:customer|user|consumer|sir|madam|candidate|member|winner|lucky\s+winner|valued\s+customer)|hello\s+(?:dear|sir|madam))\b"),
         "Your real bank or employer usually addresses you by name."),
]

REASSURING_RULES: list[Rule] = [
    Rule("PUBLIC_ADVISORY", "Reads like a safety advisory (warns about a risk or how to report fraud)", "positive", -6,
         # Not "be careful/alert": scammers open with those too ("Be careful, your account will be blocked").
         _r(r"\bbeware\s+of\b|\bmay\s+(?:lead\s+to|result\s+in)\b"
            r"|\b(?:report|complain)\w*\b[^.\n]{0,40}(?:\b1930\b|cybercrime\.gov\.in|cyber\s*crime\s+portal)"),
         "General warnings and advice on reporting fraud are typical of genuine safety notices, not of scams."),
    Rule("SAFETY_ADVICE", "Contains standard safety advice (e.g. 'never share your OTP')", "positive", -6,
         _r(r"\b(?:do\s+not|never|don'?t)\s+share\b[^.\n]{0,25}\b(?:otp|pin|cvv|password)\b|\bnever\s+asks?\s+for\b"
            r"|\b(?:do\s+not|never|don'?t|avoid)\s+(?:scan|click|open|download|install|respond\s+to|reply\s+to|pay|call\s+back)\b"
            r"[^.\n]{0,40}\b(?:unknown|unidentified|unverified|suspicious|unsolicited|untrusted|strangers?|random)\b"),
         "Genuine transactional messages usually warn you not to share codes."),
    Rule("OFFICIAL_CHANNEL", "Points you to the official app or website rather than a link", "positive", -4,
         _r(r"\b(?:in|via|from|using)\s+the\s+(?:official\s+)?(?:\w+\s+)?app\b|\bofficial\s+(?:website|portal|app)\b|\bcall\s+the\s+number\s+on\s+the\s+back\b"),
         "Directing you to the official app instead of a link is typical of legitimate messages."),
]


def _negated(text: str, start: int) -> bool:
    return bool(_NEGATION.search(text[max(0, start - 40):start]))


def _in_warning(text: str, start: int) -> bool:
    """True if the sentence leading up to `start` frames what follows as a warning about scammers."""
    sentence_start = max(text.rfind(ch, 0, start) for ch in ".!?\n") + 1
    return bool(_WARNING_FRAME.search(text[sentence_start:start]))


def _official_link(raw: str) -> bool:
    """A link to a recognised organisation or an official (gov.in, nic.in, ...) domain is not a channel a
    scammer controls. It is still scored separately by the URL analyzer."""
    from app.ml.url.analyzer import url_rules  # local import: the URL package is heavier and imports the model
    from app.ml.url.parsing import parse_url
    try:
        evidence, trusted = url_rules(parse_url(raw))
    except Exception:  # unparseable: treat as an ordinary link
        return False
    return trusted or any(e.code == "OFFICIAL_SUFFIX" for e in evidence)


def has_call_to_action(text: str) -> bool:
    """True if the message gives the reader a way to act through a channel the sender controls: a link that
    isn't an official domain, an e-mail address, or an instruction such as click / call / reply / pay / scan
    that isn't negated ("do not scan ...") or part of a warning."""
    if any(not _official_link(u) for u in extract_urls(text)) or EMAIL_RE.search(text):
        return True
    return any(not _CTA_NEGATION.search(text[max(0, m.start() - 30):m.start()]) and not _in_warning(text, m.start())
               for m in _CALL_TO_ACTION.finditer(text))


def _excerpt(text: str, m: re.Match, pad: int = 18) -> str:
    s, e = max(0, m.start() - pad), min(len(text), m.end() + pad)
    snippet = text[s:e].replace("\n", " ").strip()
    return ("…" if s > 0 else "") + snippet + ("…" if e < len(text) else "")


def detect_indicators(text: str, normalised: str | None = None) -> list[Evidence]:
    """Run all rules. Matches on the raw text first (better excerpts), then on
    the normalised text (catches placeholder patterns like `moneytoken`)."""
    found: list[Evidence] = []
    for rule in RULES + REASSURING_RULES:
        hit = None
        suppressed = False
        # Negatable rules only run on the raw text: normalisation strips sentence
        # punctuation, which would let "OTP for login. Do not share" match across sentences.
        candidates = (text,) if rule.negatable else (text, normalised or "")
        for candidate in candidates:
            if suppressed:  # every raw match was inside a warning; don't re-find it in the normalised text
                break
            for m in rule.pattern.finditer(candidate):
                if rule.negatable and (_negated(candidate, m.start()) or _NEGATION_INSIDE.search(m.group(0))):
                    continue
                # Tactics quoted inside a warning about scammers describe the scam; they don't request anything.
                if rule.weight > 0 and candidate is text and _in_warning(text, m.start()):
                    suppressed = True
                    continue
                hit = (candidate, m)
                break
            if hit:
                break
        if hit:
            src, m = hit
            found.append(Evidence(
                code=rule.code, label=rule.label, severity=rule.severity, weight=rule.weight,
                source="text_rules", detail=rule.detail,
                excerpt=_excerpt(src, m) if src is text else None,
            ))
    return found
