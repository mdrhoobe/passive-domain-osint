"""Strict, deterministic, network-free domain input normalization.

The MVP intentionally accepts ASCII domain names (including already-punycoded
IDNs). It rejects Unicode rather than silently altering the queried identity.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

from .exceptions import ValidationError

_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.ASCII)
_ASCII_TLD = re.compile(r"^[a-z]{2,63}$", re.ASCII)
_PUNYCODE_TLD = re.compile(r"^xn--[a-z0-9-]{2,59}$", re.ASCII)


def normalize_domain(value: str) -> str:
    """Return a normalized ASCII domain or raise ValidationError.

    Allowed: example.com, EXAMPLE.COM., https://example.com, http://example.com/.
    Not allowed: URL paths, query/fragment, ports, userinfo, IPs, Unicode, or
    extra characters that could change the identity of the domain.
    """
    if not isinstance(value, str):
        raise ValidationError("A domain must be entered as text.")
    value = value.strip()
    if not value:
        raise ValidationError("Enter a domain, such as example.com.")
    if not value.isascii():
        raise ValidationError("Unicode domains are not supported in this version. Enter the ASCII IDNA/Punycode form.")
    if "://" in value:
        try:
            parts = urlsplit(value)
        except ValueError as exc:
            raise ValidationError("Invalid URL.") from exc
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            raise ValidationError("Only HTTP or HTTPS URLs containing a domain are supported.")
        if parts.username is not None or parts.password is not None:
            raise ValidationError("Credentials in URLs are not permitted.")
        try:
            port = parts.port
        except ValueError as exc:
            raise ValidationError("Invalid URL port.") from exc
        if port is not None:
            raise ValidationError("Ports are not permitted. Enter only the domain.")
        if parts.path not in {"", "/"} or parts.query or parts.fragment:
            raise ValidationError("Enter only a domain, without a URL path, query or fragment.")
        domain = parts.hostname or ""
    else:
        domain = value
        if any(char in domain for char in ("/", "\\", "@", ":", "?", "#")):
            raise ValidationError("Enter a domain only, without paths, ports or special URL characters.")

    if domain.endswith(".."):
        raise ValidationError("Multiple trailing dots are not permitted.")
    domain = domain.removesuffix(".").lower()
    if len(domain) > 253 or not domain or domain.startswith(".") or ".." in domain:
        raise ValidationError("Invalid domain length or empty label.")
    try:
        ipaddress.ip_address(domain)
    except ValueError:
        pass
    else:
        raise ValidationError("IP addresses are not supported; enter a domain name.")
    labels = domain.split(".")
    if len(labels) < 2 or any(not _LABEL.fullmatch(label) for label in labels):
        raise ValidationError("Invalid domain label. Only letters, numbers and internal hyphens are permitted.")
    if not (_ASCII_TLD.fullmatch(labels[-1]) or _PUNYCODE_TLD.fullmatch(labels[-1])):
        raise ValidationError("A domain must end with a supported alphabetic TLD of at least two characters.")
    return domain


def validate_domain(value: str) -> str:
    """Alias for normalize_domain; performs no network access."""
    return normalize_domain(value)


class DomainValidator:
    """Stable facade for use by UI/CLI code."""

    @staticmethod
    def validate(value: str) -> str:
        return normalize_domain(value)
