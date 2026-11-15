"""RDAP/DNS/CT source behavior with deterministic offline fixtures."""
import json
import pytest
import requests
import dns.exception

from src.collector import (
    DomainCollector, find_rdap_endpoint, _small_json_response,
    IANA_RDAP_BOOTSTRAP, CRT_SH_ENDPOINT, MAX_HTTP_RESPONSE_BYTES,
)
from src.exceptions import ValidationError, SourceResponseError, SourceUnavailable
from conftest import FakeResponse, FakeSession, FakeResolver


def test_rdap_longest_suffix_and_https(rdap_bootstrap):
    assert find_rdap_endpoint(rdap_bootstrap, "example.com") == "https://rdap.example.test/"
    assert find_rdap_endpoint(rdap_bootstrap, "test.net") == "https://rdap.example.test/"
    assert find_rdap_endpoint(rdap_bootstrap, "test.edu") is None


def test_bootstrap_rejects_local_or_insecure_endpoints():
    doc = {"services": [[ ["com"], ["http://bad.example/", "https://127.0.0.1/", "https://localhost/"] ]]}
    assert find_rdap_endpoint(doc, "example.com") is None


def test_full_collection(fake_clients):
    session, resolver = fake_clients
    result = DomainCollector(session=session, resolver=resolver).run("https://EXAMPLE.COM")
    assert result["domain"] == "example.com"
    assert result["summary"] == {"ok": 3, "partial": 0, "no_data": 0, "error": 0}
    assert result["rdap"]["data"]["name"] == "EXAMPLE.COM"
    assert result["rdap"]["data"]["events"][0]["action"] == "registration"
    assert "private@example.test" not in json.dumps(result)
    assert result["dns"]["data"]["records"]["A"] == ["192.0.2.10"]
    assert result["dns"]["data"]["records"]["MX"] == ["10 mail.example.com"]
    assert result["dns"]["data"]["records"]["TXT"] == ["v=spf1 -all"]
    assert result["cert"]["data"]["matched_entries"] == 2
    assert len(result["cert"]["data"]["entries"]) == 2
    assert "admin.example.com" not in json.dumps(result)
    assert [c[0] for c in session.calls] == [IANA_RDAP_BOOTSTRAP, "https://rdap.example.test/domain/example.com", CRT_SH_ENDPOINT]
    assert all(c[1]["allow_redirects"] is False for c in session.calls)
    assert len(resolver.calls) == 5
    assert all(call[0] == "example.com" for call in resolver.calls)


def test_no_bootstrap_endpoint_causes_no_data(rdap_bootstrap):
    s = FakeSession({IANA_RDAP_BOOTSTRAP: FakeResponse({"services": []}), CRT_SH_ENDPOINT: FakeResponse([])})
    r = DomainCollector(session=s, resolver=FakeResolver()).run("example.com")
    assert r["rdap"]["status"] == "no_data"
    assert r["cert"]["status"] == "no_data"


def test_rdap_404_is_no_data(fake_clients):
    s, resolver = fake_clients
    s.responses["https://rdap.example.test/domain/example.com"] = FakeResponse(None, 404)
    r = DomainCollector(session=s, resolver=resolver).run("example.com")
    assert r["rdap"]["status"] == "no_data"
    assert r["summary"]["ok"] == 2


def test_network_failure_is_source_error_not_fake_success(fake_clients):
    s, resolver = fake_clients
    s.responses[IANA_RDAP_BOOTSTRAP] = requests.Timeout()
    r = DomainCollector(session=s, resolver=resolver).run("example.com")
    assert r["rdap"]["status"] == "error"
    assert "timed out" in r["rdap"]["error"]
    assert r["summary"]["error"] == 1
    assert r["dns"]["status"] == "ok"


def test_invalid_domain_prevents_all_outbound_calls(fake_clients):
    s, resolver = fake_clients
    with pytest.raises(ValidationError):
        DomainCollector(session=s, resolver=resolver).run("https://example.com/admin")
    assert s.calls == [] and resolver.calls == []


def test_invalid_json_reported_as_source_error(fake_clients):
    s, resolver = fake_clients
    s.responses[CRT_SH_ENDPOINT] = FakeResponse(None, raw=b"<html>not JSON</html>")
    r = DomainCollector(session=s, resolver=resolver).run("example.com")
    assert r["cert"]["status"] == "error"
    assert "invalid JSON" in r["cert"]["error"]


def test_bounded_http_response(fake_clients):
    s, resolver = fake_clients
    s.responses[CRT_SH_ENDPOINT] = FakeResponse(None, raw=b"x" * (MAX_HTTP_RESPONSE_BYTES + 1))
    r = DomainCollector(session=s, resolver=resolver).run("example.com")
    assert r["cert"]["status"] == "error"
    assert "size limit" in r["cert"]["error"]


def test_http_redirect_is_not_followed(fake_clients):
    s, resolver = fake_clients
    s.responses[CRT_SH_ENDPOINT] = FakeResponse(None, 302)
    r = DomainCollector(session=s, resolver=resolver).run("example.com")
    assert r["cert"]["status"] == "error"
    assert "302" in r["cert"]["error"]


def test_no_dns_and_dns_timeout_are_distinct(fake_clients):
    s, resolver = fake_clients
    r = DomainCollector(session=s, resolver=FakeResolver(error=dns.exception.Timeout())).run("example.com")
    assert r["dns"]["status"] == "error"
    assert "A: Timeout" in r["dns"]["error"]
    s, resolver = fake_clients
    from dns.resolver import NXDOMAIN
    r2 = DomainCollector(session=s, resolver=FakeResolver(error=NXDOMAIN())).run("example.com")
    assert r2["dns"]["status"] == "no_data"


def test_invalid_timeouts():
    for timeout in (-1, 0, 31):
        with pytest.raises(ValueError):
            DomainCollector(timeout=timeout)


def test_rdap_bad_response_is_not_success(fake_clients):
    s, resolver = fake_clients
    s.responses["https://rdap.example.test/domain/example.com"] = FakeResponse([1,2,3])
    r = DomainCollector(session=s, resolver=resolver).run("example.com")
    assert r["rdap"]["status"] == "error"


def test_rdap_empty_object_is_no_data(fake_clients):
    s, resolver = fake_clients
    s.responses["https://rdap.example.test/domain/example.com"] = FakeResponse({})
    result = DomainCollector(session=s, resolver=resolver).run("example.com")
    assert result["rdap"]["status"] == "no_data"


def test_partial_dns_is_not_misreported_as_full_success(fake_clients):
    from dns.resolver import NoAnswer
    s, resolver = fake_clients
    original = resolver.resolve
    def resolve(domain, kind, **kwargs):
        if kind == "TXT":
            raise dns.exception.Timeout()
        return original(domain, kind, **kwargs)
    resolver.resolve = resolve
    result = DomainCollector(session=s, resolver=resolver).run("example.com")
    assert result["dns"]["status"] == "partial"
    assert result["summary"]["partial"] == 1
    assert result["dns"]["data"]["records"]["A"] == ["192.0.2.10"]
