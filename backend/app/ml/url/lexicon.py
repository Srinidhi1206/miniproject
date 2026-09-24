"""Curated reference lists used by URL rules. Plain data — easy to review and extend."""

# Brand keyword -> registered domains the brand genuinely uses.
BRANDS: dict[str, set[str]] = {
    "sbi": {"sbi.co.in", "onlinesbi.sbi", "sbi.bank.in", "sbicard.com", "sbilife.co.in", "onlinesbi.com"},
    "hdfc": {"hdfcbank.com", "hdfc.com", "hdfclife.com", "hdfcergo.com", "hdfcbank.bank.in"},
    "icici": {"icicibank.com", "icicidirect.com", "iciciprulife.com", "icicilombard.com"},
    "axis": {"axisbank.com", "axisdirect.in"},
    "kotak": {"kotak.com", "kotaksecurities.com"},
    "paytm": {"paytm.com", "paytmbank.com", "paytmmoney.com"},
    "phonepe": {"phonepe.com"},
    "gpay": {"google.com", "pay.google.com"},
    "googlepay": {"google.com"},
    "bhim": {"bhimupi.org.in", "npci.org.in"},
    "npci": {"npci.org.in"},
    "amazon": {"amazon.in", "amazon.com", "amazon.co.uk", "amazonpay.in", "aws.amazon.com", "amazon.jobs"},
    "flipkart": {"flipkart.com"},
    "myntra": {"myntra.com"},
    "netflix": {"netflix.com"},
    "paypal": {"paypal.com", "paypal.me"},
    "apple": {"apple.com", "icloud.com"},
    "appleid": {"apple.com"},
    "microsoft": {"microsoft.com", "live.com", "office.com", "microsoftonline.com", "outlook.com"},
    "office365": {"office.com", "microsoft.com"},
    "outlook": {"outlook.com", "live.com", "office.com"},
    "google": {"google.com", "google.co.in", "youtube.com", "gmail.com"},
    "gmail": {"google.com", "gmail.com"},
    "whatsapp": {"whatsapp.com", "wa.me"},
    "instagram": {"instagram.com"},
    "facebook": {"facebook.com", "fb.com"},
    "metamask": {"metamask.io"},
    "binance": {"binance.com"},
    "indiapost": {"indiapost.gov.in"},
    "irctc": {"irctc.co.in"},
    "uidai": {"uidai.gov.in"},
    "aadhaar": {"uidai.gov.in"},
    "epfo": {"epfindia.gov.in"},
    "incometax": {"incometax.gov.in"},
    "parivahan": {"parivahan.gov.in"},
    "echallan": {"parivahan.gov.in"},
    "fastag": {"npci.org.in", "ihmcl.co.in"},
    "digilocker": {"digilocker.gov.in"},
    "lic": {"licindia.in"},
    "airtel": {"airtel.in", "airtel.com"},
    "jio": {"jio.com"},
    "bescom": {"bescom.karnataka.gov.in", "bescom.co.in"},
    "dhl": {"dhl.com", "dhl.co.in"},
    "fedex": {"fedex.com"},
    "bluedart": {"bluedart.com"},
    "swiggy": {"swiggy.com"},
    "zomato": {"zomato.com"},
    "naukri": {"naukri.com"},
    "linkedin": {"linkedin.com"},
    "zerodha": {"zerodha.com"},
}

# Registered domains treated as well-known and legitimate. Only exact
# registered-domain matches count, so "sbi.co.in.evil.com" never qualifies.
ALLOWLIST: set[str] = {d for domains in BRANDS.values() for d in domains} | {
    "youtube.com", "wikipedia.org", "github.com", "gov.in", "nic.in", "rbi.org.in", "cybercrime.gov.in",
    "x.com", "twitter.com", "reddit.com", "stackoverflow.com", "bing.com", "yahoo.com", "zoom.us",
    "slack.com", "dropbox.com", "adobe.com", "cloudflare.com", "wa.me", "t.me", "telegram.org",
    "hotstar.com", "jiocinema.com", "bookmyshow.com", "makemytrip.com", "ola.com", "olacabs.com", "uber.com",
    "rapido.bike", "bigbasket.com", "blinkit.com", "zeptonow.com", "nykaa.com", "ajio.com", "meesho.com",
    "tatacliq.com", "croma.com", "reliancedigital.in", "infosys.com", "tcs.com", "wipro.com", "coursera.org",
    "udemy.com", "nptel.ac.in", "swayam.gov.in", "google.co.in", "bankofbaroda.in", "pnbindia.in",
    "canarabank.com", "unionbankofindia.co.in", "bankofindia.co.in", "yesbank.in", "indusind.com",
    "idfcfirstbank.com", "federalbank.co.in", "groww.in", "upstox.com", "cred.club", "mobikwik.com",
}

OFFICIAL_SUFFIXES = ("gov.in", "nic.in", "gov", "edu", "ac.in", "edu.in", "bank.in")
# Messaging deep-link domains: legitimate services, but links to them hand you
# to an unknown account — flagged as info, never allowlist-discounted.
MESSAGING_DOMAINS = {"wa.me", "t.me", "chat.whatsapp.com"}

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy", "ow.ly", "shorturl.at",
    "s.id", "tiny.cc", "buff.ly", "rebrand.ly", "bl.ink", "short.io", "v.gd", "shorte.st", "adf.ly",
    "tinylink.in", "u.to", "qr.ae", "lnkd.in", "surl.li", "t.ly", "shorturl.asia",
}

FREE_HOSTING = {
    "firebaseapp.com", "web.app", "repl.co", "replit.app", "glitch.me", "surge.sh", "godaddysites.com",
    "weebly.com", "wixsite.com", "webflow.io", "netlify.app", "vercel.app", "pages.dev", "github.io",
    "blogspot.com", "000webhostapp.com", "ngrok.io", "ngrok-free.app", "herokuapp.com", "azurewebsites.net",
    "sites.google.com", "square.site", "carrd.co", "wordpress.com", "ipfs.io", "cloudflare-ipfs.com",
    "workers.dev", "onrender.com", "firebasestorage.googleapis.com", "r2.dev", "framer.website",
}

SUSPICIOUS_TLDS = {
    "xyz", "top", "online", "site", "shop", "click", "live", "buzz", "icu", "tk", "ml", "ga", "cf", "gq",
    "loan", "work", "help", "support", "rest", "cam", "monster", "fit", "cyou", "sbs", "cfd", "bond",
    "quest", "zip", "mov", "country", "kim", "men", "win", "download", "racing", "review", "stream",
}

SENSITIVE_KEYWORDS = [
    "login", "log-in", "signin", "sign-in", "verify", "verification", "kyc", "update", "secure", "account",
    "wallet", "refund", "reward", "claim", "bonus", "otp", "password", "banking", "confirm", "suspend",
    "unlock", "recover", "validate", "billing", "payment", "prize", "gift", "free", "lucky", "winner",
    "support", "helpdesk", "customs", "redelivery", "challan", "invoice",
]

RISKY_EXTENSIONS = (".apk", ".exe", ".scr", ".bat", ".msi", ".cmd", ".jar", ".vbs", ".ps1", ".dmg", ".xapk")
