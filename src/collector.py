"""Single-domain, public-metadata collection with per-source status reporting.

RDAP: IANA bootstrap selects the authoritative advertised domain RDAP base URL.
DNS: only the requested hostname's A, AAAA, MX, NS and TXT records.
CT: crt.sh public JSON; exact/wildcard domain only, no subdomain listing.
No scanning, service connections to the target, or credential collection.
"""
from __future__ import annotations

import ipaddress
from datetime import datetime, timezone
from urllib.parse import urlsplit
from typing import Any, Callable

import dns.exception
import dns.resolver
import requests

from .exceptions import CollectorError, SourceResponseError, SourceUnavailable
from .validator import normalize_domain

IANA_RDAP_BOOTSTRAP = "https://data.iana.org/rdap/dns.json"
CRT_SH_ENDPOINT = "https://crt.sh/"
DNS_TYPES = ("A", "AAAA", "MX", "NS", "TXT")
CT_LIMIT = 40
MAX_HTTP_RESPONSE_BYTES = 3_000_000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def source_record(source: str, status: str, data: dict | None = None,
                  error: str | None = None, note: str | None = None) -> dict:
    return {"source": source, "status": status, "data": data or {}, "error": error, "note": note}


def _https_public_url(url: str) -> bool:
    """Reject unexpected bootstrap targets and non-HTTPS or IP literal endpoints."""
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port:
            return False
        host = parsed.hostname.lower()
        if host == "localhost" or host.endswith((".local", ".internal")) or "." not in host:
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            return True
    except ValueError:
        return False


def find_rdap_endpoint(bootstrap: dict, domain: str) -> str | None:
    """Select the most specific advertised suffix, not a hard-coded RDAP host."""
    matches = []
    for service in bootstrap.get("services", []):
        if not isinstance(service, list) or len(service) != 2:
            continue
        suffixes, endpoints = service
        if not isinstance(suffixes, list) or not isinstance(endpoints, list):
            continue
        for suffix in suffixes:
            if not isinstance(suffix, str):
                continue
            suffix = suffix.strip(".").lower()
            if domain == suffix or domain.endswith("." + suffix):
                for url in endpoints:
                    if isinstance(url, str) and _https_public_url(url):
                        matches.append((len(suffix), url))
    if not matches:
        return None
    return sorted(matches, key=lambda pair: pair[0], reverse=True)[0][1].rstrip("/") + "/"


def _small_json_response(session: requests.Session, url: str, *, timeout: float,
                         params: dict | None = None) -> Any:
    """Limit response size and reject redirects; no implicit connections to new hosts."""
    try:
        with session.get(url, params=params, timeout=timeout, stream=True,
                         allow_redirects=False, headers={"User-Agent": "Passive-Domain-OSINT/0.2 (educational)"}) as response:
            if response.status_code == 404:
                return None
            if response.status_code == 429:
                raise SourceUnavailable("Public source rate-limited the request (HTTP 429).")
            if response.status_code != 200:
                raise SourceUnavailable(f"Source returned HTTP {response.status_code}.")
            length = response.headers.get("Content-Length")
            if length and length.isdecimal() and int(length) > MAX_HTTP_RESPONSE_BYTES:
                raise SourceResponseError("Response exceeds the safety size limit.")
            raw = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                raw.extend(chunk)
                if len(raw) > MAX_HTTP_RESPONSE_BYTES:
                    raise SourceResponseError("Response exceeds the safety size limit.")
            try:
                import json
                return json.loads(raw)
            except (ValueError, UnicodeError) as exc:
                raise SourceResponseError("Source returned invalid JSON.") from exc
    except requests.exceptions.Timeout as exc:
        raise SourceUnavailable("Request timed out.") from exc
    except requests.exceptions.RequestException as exc:
        raise SourceUnavailable("Could not contact the public source.") from exc


def _rdap_summary(data: dict) -> dict:
    # Do not export vCard contact details or personal registrant data.
    events = []
    for event in data.get("events", []):
        if isinstance(event, dict) and event.get("eventAction") in {"registration", "expiration", "last changed"}:
            events.append({"action": event.get("eventAction"), "date": event.get("eventDate")})
    nameservers = [entry.get("ldhName") for entry in data.get("nameservers", [])
                   if isinstance(entry, dict) and isinstance(entry.get("ldhName"), str)]
    registrars = []
    for entity in data.get("entities", []):
        if isinstance(entity, dict) and "registrar" in entity.get("roles", []):
            # Only public organizational identity, no contact data or email.
            registrars.append(entity.get("handle") or "Registrar entity listed")
    return {
        "name": data.get("ldhName") or data.get("unicodeName"),
        "handle": data.get("handle"),
        "status": data.get("status", [])[:12] if isinstance(data.get("status", []), list) else [],
        "events": events[:12],
        "nameservers": nameservers[:20],
        "registrar_handles": registrars[:5],
    }


def _dns_text(record: Any, rdtype: str) -> str:
    if rdtype == "MX":
        return f"{record.preference} {str(record.exchange).rstrip('.')}"
    if rdtype == "TXT":
        # TXT can be multiple byte strings; decoding errors must not crash the UI.
        raw = b"".join(record.strings)
        return raw.decode("utf-8", errors="replace")[:300]
    return str(record).rstrip(".")[:300]


class DomainCollector:
    """Collector uses injectable HTTP and DNS clients for deterministic offline tests."""

    def __init__(self, timeout: float = 5, *, session: requests.Session | None = None,
                 resolver: dns.resolver.Resolver | None = None):
        if timeout <= 0 or timeout > 30:
            raise ValueError("timeout must be between 0 and 30 seconds")
        self.timeout = float(timeout)
        self.session = session or requests.Session()
        self.resolver = resolver or dns.resolver.Resolver(configure=True)
        self.resolver.lifetime = self.timeout
        self.resolver.timeout = min(self.timeout, 3)

    def run(self, domain: str) -> dict:
        domain = normalize_domain(domain)
        results = {
            "domain": domain,
            "collected_at": utc_now(),
            "rdap": self._safe(self.collect_rdap, "IANA RDAP bootstrap → domain RDAP server", domain),
            "dns": self._safe(self.collect_dns, "System recursive DNS resolver", domain),
            "cert": self._safe(self.collect_ct, "crt.sh public certificate transparency", domain),
            "disclaimer": "Public metadata only. Records may be incomplete, delayed, or inconsistent; no security assessment was performed.",
        }
        counts = {s: sum(results[k]["status"] == s for k in ("rdap", "dns", "cert"))
                  for s in ("ok", "partial", "no_data", "error")}
        results["summary"] = counts
        return results

    @staticmethod
    def _safe(action: Callable[[str], dict], source: str, domain: str) -> dict:
        try:
            return action(domain)
        except (CollectorError, ValueError, KeyError, TypeError) as exc:
            return source_record(source, "error", error=str(exc), note="Source unavailable or response could not be interpreted.")
        except Exception as exc:
            # Keep each source independent; avoid presenting Python internals in the UI.
            return source_record(source, "error", error=f"Unexpected {type(exc).__name__}",
                                 note="Could not complete this source; other results may still be available.")

    def collect_rdap(self, domain: str) -> dict:
        bootstrap = _small_json_response(self.session, IANA_RDAP_BOOTSTRAP, timeout=self.timeout)
        if not isinstance(bootstrap, dict):
            raise SourceResponseError("IANA bootstrap response was not a JSON object.")
        endpoint = find_rdap_endpoint(bootstrap, domain)
        if not endpoint:
            return source_record(IANA_RDAP_BOOTSTRAP, "no_data", note="No RDAP service found for this domain suffix.")
        query_url = endpoint + "domain/" + domain
        response = _small_json_response(self.session, query_url, timeout=self.timeout)
        if response is None:
            return source_record(query_url, "no_data", note="RDAP returned HTTP 404.")
        if not isinstance(response, dict):
            raise SourceResponseError("RDAP response must be a JSON object.")
        summary = _rdap_summary(response)
        if not any(summary.values()):
            return source_record(query_url, "no_data", note="RDAP returned no usable public domain fields.")
        return source_record(query_url, "ok", summary,
                             note="Registrar contact details are deliberately excluded.")

    def collect_dns(self, domain: str) -> dict:
        records: dict[str, list[str]] = {}
        errors: list[str] = []
        for kind in DNS_TYPES:
            try:
                answer = self.resolver.resolve(domain, kind, lifetime=self.timeout, search=False)
                records[kind] = sorted(set(_dns_text(record, kind) for record in answer))[:20]
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                records[kind] = []
            except (dns.exception.Timeout, dns.resolver.NoNameservers) as exc:
                records[kind] = []
                errors.append(f"{kind}: {type(exc).__name__}")
            except Exception as exc:
                records[kind] = []
                errors.append(f"{kind}: {type(exc).__name__}")
        any_records = any(records.values())
        status = ("partial" if errors else "ok") if any_records else ("error" if errors else "no_data")
        note = "Maximum 20 results/type; TXT values truncated to 300 chars."
        if errors:
            note += " Some DNS types failed: " + ", ".join(errors)
        return source_record("System recursive DNS resolver", status, {"records": records},
                             error="; ".join(errors) if errors else None, note=note)

    def collect_ct(self, domain: str) -> dict:
        raw = _small_json_response(self.session, CRT_SH_ENDPOINT,
                                   params={"q": domain, "output": "json"}, timeout=self.timeout)
        if raw is None or raw == []:
            return source_record("https://crt.sh/?output=json", "no_data",
                                 note="No public CT records returned (or HTTP 404).")
        if not isinstance(raw, list):
            raise SourceResponseError("Certificate Transparency response must be a JSON array.")
        exact_names = {domain, "*." + domain}
        selected = []
        dedup = set()
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            matching_names = [n.strip().lower() for n in str(entry.get("name_value", "")).splitlines()
                              if n.strip().lower() in exact_names]
            if not matching_names:
                continue
            key = (entry.get("id"), entry.get("entry_timestamp"))
            if key in dedup:
                continue
            dedup.add(key)
            selected.append({
                "id": entry.get("id"),
                "names": matching_names,
                "issuer_name": str(entry.get("issuer_name", ""))[:250],
                "entry_timestamp": entry.get("entry_timestamp"),
                "not_before": entry.get("not_before"),
                "not_after": entry.get("not_after"),
            })
        selected.sort(key=lambda x: str(x.get("entry_timestamp") or ""), reverse=True)
        if not selected:
            return source_record("https://crt.sh/?output=json", "no_data",
                                 note="No entries matched the requested domain exactly or with a wildcard.")
        return source_record("https://crt.sh/?output=json", "ok",
                             {"entries": selected[:CT_LIMIT], "matched_entries": len(selected),
                              "display_limit": CT_LIMIT},
                             note="Historical issuance data, not live TLS. Exact/wildcard name matches only; max 40 displayed.")
