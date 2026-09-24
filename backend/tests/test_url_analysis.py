import pytest

from app.core.errors import SentinelError
from app.ml.url.analyzer import analyze_url
from app.ml.url.parsing import parse_url


def codes(url):
    return {e.code for e in analyze_url(parse_url(url)).evidence}


@pytest.mark.parametrize("bad", ["", "javascript:alert(1)", "ftp://files.example.com", "not a url", "localhost",
                                 "http://exa mple.com", "http://nodot"])
def test_invalid_urls_raise_friendly_error(bad):
    with pytest.raises(SentinelError) as exc:
        parse_url(bad)
    assert exc.value.code == "INVALID_URL"


def test_parse_adds_scheme_and_extracts_registered_domain():
    u = parse_url("Secure.Login.sbi-kyc.xyz/update?x=1")
    assert u.scheme == "http" and not u.has_explicit_scheme
    assert u.registered_domain == "sbi-kyc.xyz"
    assert u.subdomain == "secure.login"


def test_known_domain_is_trusted_even_with_login_path():
    a = analyze_url(parse_url("https://accounts.google.com/signin/v2"))
    assert a.trusted
    assert "KNOWN_DOMAIN" in {e.code for e in a.evidence}
    assert "SENSITIVE_KEYWORDS" not in {e.code for e in a.evidence}


def test_lookalike_domain_on_trusted_name_is_not_trusted():
    a = analyze_url(parse_url("http://sbi.co.in.verify-kyc.xyz/login"))
    assert not a.trusted
    assert {"BRAND_IMPERSONATION", "SUSPICIOUS_TLD"} <= {e.code for e in a.evidence}


@pytest.mark.parametrize("url,expected", [
    ("http://paypa1-resolution.com", "BRAND_IMPERSONATION"),
    ("https://flipkrat.com/offer", "TYPOSQUAT"),
    ("http://192.168.10.5/bank/login", "IP_HOST"),
    ("https://bit.ly/3xYz", "SHORTENER"),
    ("https://metamask-restore.web.app", "FREE_HOSTING"),
    ("https://example-shop.com/app/update.apk", "RISKY_DOWNLOAD"),
    ("https://xn--pple-43d.com", "PUNYCODE"),
    ("https://good.example.com@evil.xyz/", "AT_SYMBOL"),
])
def test_url_rules(url, expected):
    assert expected in codes(url)


def test_url_model_ranks_phishing_above_legit():
    legit = analyze_url(parse_url("https://www.wikipedia.org")).model
    phish = analyze_url(parse_url("http://hdfc-netbanking-update.xyz")).model
    assert legit is not None and phish is not None
    assert phish.probability > legit.probability
