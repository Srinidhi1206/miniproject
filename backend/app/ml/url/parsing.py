"""Safe URL parsing. Nothing here performs network I/O.

The public-suffix list comes from tldextract's bundled snapshot
(`suffix_list_urls=()`), so parsing never reaches the network either.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

import tldextract

from app.core.errors import SentinelError

_extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)
_HOST_RE = re.compile(r"^[a-z0-9.\-_]+$")
MAX_URL_LEN = 2048


@dataclass(frozen=True)
class ParsedURL:
    original: str
    normalised: str
    scheme: str
    host: str
    port: int | None
    path: str
    query: str
    subdomain: str
    domain: str  # registrable label, e.g. "sbi" in onlinesbi.sbi.co.in? -> "sbi"
    suffix: str
    is_ip: bool
    has_explicit_scheme: bool

    @property
    def registered_domain(self) -> str:
        if self.is_ip:
            return self.host
        return f"{self.domain}.{self.suffix}" if self.suffix else self.domain

    @property
    def host_for_model(self) -> str:
        return self.host[4:] if self.host.startswith("www.") else self.host


def invalid_url(reason: str) -> SentinelError:
    return SentinelError("INVALID_URL", f"That doesn't look like a valid web address — {reason}.", 400,
                         hint="Paste the full link, for example https://example.com/page")


def parse_url(raw: str) -> ParsedURL:
    text = (raw or "").strip().strip("<>\"'")
    if not text:
        raise invalid_url("it's empty")
    if len(text) > MAX_URL_LEN:
        raise invalid_url(f"it's longer than {MAX_URL_LEN} characters")
    if re.search(r"\s", text):
        raise invalid_url("it contains spaces")

    has_scheme = bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text))
    if not has_scheme:
        if re.match(r"^(javascript|data|vbscript|file):", text, re.I):
            raise invalid_url("scripts and local files can't be analysed as web links")
        text = "http://" + text
    parts = urlsplit(text)
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise invalid_url(f"'{scheme}://' links aren't web pages")

    try:
        port = parts.port
    except ValueError:
        raise invalid_url("the port number is invalid")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise invalid_url("there's no website name")
    try:
        host = host.encode("idna").decode("ascii") if not host.isascii() else host
    except UnicodeError:
        raise invalid_url("the website name contains invalid characters")
    if not _HOST_RE.match(host):
        raise invalid_url("the website name contains invalid characters")

    is_ip = False
    try:
        ipaddress.ip_address(host.strip("[]"))
        is_ip = True
    except ValueError:
        if "." not in host:
            raise invalid_url("the website name has no domain ending like .com or .in")

    ext = _extract(host)
    if not is_ip and not ext.suffix:
        raise invalid_url(f"'{host}' doesn't end in a recognised domain extension")

    return ParsedURL(
        original=raw.strip(), normalised=text, scheme=scheme, host=host, port=port,
        path=unquote(parts.path or ""), query=unquote(parts.query or ""),
        subdomain=ext.subdomain, domain=ext.domain, suffix=ext.suffix,
        is_ip=is_ip, has_explicit_scheme=has_scheme,
    )
