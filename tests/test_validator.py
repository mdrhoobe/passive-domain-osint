"""Input validation: strict and offline, with no destructive sanitizing."""
import pytest
from src.exceptions import ValidationError
from src.validator import DomainValidator, normalize_domain, validate_domain


@pytest.mark.parametrize("raw,expected", [
    ("example.com", "example.com"),
    ("EXAMPLE.COM", "example.com"),
    (" sub.Example.org ", "sub.example.org"),
    ("example.com.", "example.com"),
    ("https://example.com", "example.com"),
    ("http://example.com/", "example.com"),
    ("www.example.net", "www.example.net"),
    ("xn--e1afmkfd.xn--p1ai", "xn--e1afmkfd.xn--p1ai"),
])
def test_accepted_domains(raw, expected):
    assert normalize_domain(raw) == expected
    assert validate_domain(raw) == expected
    assert DomainValidator.validate(raw) == expected


@pytest.mark.parametrize("invalid", [
    "", "  ", "example", ".example.com", "example..com", "example.com..",
    "-example.com", "example-.com", "exa_mple.com", "exam.c",
    "192.168.0.1", "[::1]", "http://127.0.0.1", "http://example.com:443",
    "https://example.com/path", "https://example.com/?q=1", "https://example.com#part",
    "https://user@example.com", "ftp://example.com", "example.com:443",
    "admin@example.com", "example.com/path", "examπle.кom", "例子.测试",
    "example.com<script>", "evil.example.com\\file", None,
    "a" * 64 + ".com", "example.123", "example.com\nother.com",
])
def test_rejected_domains(invalid):
    with pytest.raises(ValidationError):
        normalize_domain(invalid)


def test_format_validation_is_network_free(monkeypatch):
    import socket
    def bad(*args, **kwargs):
        raise AssertionError("Network access attempted")
    monkeypatch.setattr(socket.socket, "connect", bad)
    assert normalize_domain("https://example.com") == "example.com"
