"""Offline test fixtures: no external HTTP or DNS requests are permitted."""
import json
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError("Real network access is forbidden during tests")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def rdap_bootstrap(fixtures_dir):
    return json.loads((fixtures_dir / "bootstrap.json").read_text(encoding="utf-8"))


@pytest.fixture
def rdap_response(fixtures_dir):
    return json.loads((fixtures_dir / "rdap.json").read_text(encoding="utf-8"))


@pytest.fixture
def ct_response(fixtures_dir):
    return json.loads((fixtures_dir / "ct.json").read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, data, status_code=200, *, raw=None):
        self.status_code = status_code
        self.raw = raw if raw is not None else json.dumps(data).encode("utf-8")
        self.headers = {"Content-Length": str(len(self.raw))}
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def iter_content(self, chunk_size=65536):
        for offset in range(0, len(self.raw), chunk_size):
            yield self.raw[offset:offset + chunk_size]


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.get(url)
        if response is None:
            raise AssertionError(f"Unexpected URL: {url}")
        if isinstance(response, Exception):
            raise response
        return response


class FakeResolver:
    def __init__(self, *, error=None):
        self.lifetime = 5
        self.timeout = 3
        self.calls = []
        self.error = error
    def resolve(self, domain, record_type, **kwargs):
        from dns.resolver import NoAnswer
        self.calls.append((domain, record_type, kwargs))
        if self.error is not None:
            raise self.error
        data = {
            "A": [type("ARecord", (), {"__str__": lambda self: "192.0.2.10"})()],
            "AAAA": [],
            "MX": [SimpleNamespace(preference=10, exchange="mail.example.com.")],
            "NS": [],
            "TXT": [SimpleNamespace(strings=[b"v=spf1 -all"])],
        }
        if not data.get(record_type):
            raise NoAnswer()
        return data[record_type]


@pytest.fixture
def fake_clients(rdap_bootstrap, rdap_response, ct_response):
    from src.collector import IANA_RDAP_BOOTSTRAP, CRT_SH_ENDPOINT
    session = FakeSession({
        IANA_RDAP_BOOTSTRAP: FakeResponse(rdap_bootstrap),
        "https://rdap.example.test/domain/example.com": FakeResponse(rdap_response),
        CRT_SH_ENDPOINT: FakeResponse(ct_response),
    })
    return session, FakeResolver()
