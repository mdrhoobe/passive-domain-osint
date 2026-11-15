# Passive Domain OSINT

**A small, reproducible, defensive domain-metadata research project built with Python and Streamlit.**

This project demonstrates input validation, public-source discovery, independent error handling, reproducible offline testing, and responsible reporting. It is designed as an **intermediate-level master's scholarship portfolio project**, not a vulnerability scanner or identity investigation tool.

**Status:** v0.2.0 — implemented CLI, RDAP/DNS/CT collectors, exports, Streamlit UI, synthetic offline demo, and automated tests. **Live end-to-end API reliability is not guaranteed**: networks and public services can change or rate-limit requests.

## Features

| Feature | Implementation | Key limitation |
| --- | --- | --- |
| Input validation | One ASCII domain or bare HTTP(S) domain URL; deterministic, rejects malformed/Unicode inputs | Unicode IDNs must be supplied in punycode form |
| RDAP | Retrieves IANA's official `dns.json` bootstrap file to select a registry's advertised HTTPS RDAP endpoint | No endpoint, redaction, 404, 3xx, or rate-limiting may prevent results |
| DNS | `dnspython` queries A / AAAA / MX / NS / TXT from your configured resolver | No port scans or target TCP services; resolver responses vary |
| Certificate Transparency | crt.sh JSON search, displaying only exact and `*.` wildcard matches | Historical issuance records, not an audit of live TLS; large responses are rejected |
| Output | JSON and standards-oriented CSV, with timestamp, data provenance, status and error fields | No inferred risk score; CSV may contain public DNS TXT strings |
| Dashboard | Streamlit with empty, loading, success, partial failure, no-data and synthetic-demo states | Browser and UI must be smoke-tested in your environment |
| Privacy | RDAP vCard and contacts omitted; no persistent query database | Queries still reach public providers and your DNS resolver |

## Getting started (Windows PowerShell)

Requirements: Python 3.11+; internet access for dependency installation and *live* collection.

```powershell
cd "$HOME\Documents\Scholarship-Projects\passive-domain-osint"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m streamlit run app.py
```

If `py -3.11` is unavailable, use your installed Python 3.12/3.13: `python -m venv .venv`. If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` instead of `python` in each command; activation is not mandatory.

On a desktop, Streamlit usually opens its local URL (typically `http://localhost:8501`). **Use `Load synthetic demo (offline)`** in the sidebar to preview the UI without querying public providers. This demo is explicitly labeled and is *not* real research output.

## CLI

```powershell
python cli.py validate example.com
python cli.py validate https://example.com
python cli.py collect example.com
python cli.py collect example.com --format json
python cli.py collect example.com --format csv --output "example-public.csv"
```

The `validate` command never queries DNS or HTTP. The `collect` command makes public DNS/HTTPS requests (typically 1 bootstrap, 1 RDAP, 1 CT and 5 DNS record type lookups), and can take time or return partial errors. The CLI exits with 0 for no source errors, 2 for partial source errors and 1 for an invalid input or output error.

## Architecture

```text
Single domain input
        |
  src/validator.py  -- strict, network-free normalization
        |
 src/collector.py  -- independent source calls
    |       |       |
  IANA -> RDAP   DNS resolver   crt.sh JSON
    |       |       |
    +---- source status, note, data/error ----+
                         |
                  src/output.py
                 JSON / RFC CSV
                         |
                 app.py / cli.py
```

RDAP: **IANA RDAP DNS Bootstrap Service Registry** (`https://data.iana.org/rdap/dns.json`) selects the most specific matching suffix and advertised HTTPS base URL, following [RFC 9224](https://www.rfc-editor.org/rfc/rfc9224.html). RDAP fields are reduced to status, dates/events, nameservers and registrar handles. VCards and contact addresses are not retained.

DNS: `dnspython` queries the configured recursive resolver for the **single input hostname**. Missing record types are not classified as risks. Up to 20 values/type are returned; TXT values are truncated at 300 characters.

CT: `https://crt.sh/?q=<domain>&output=json` may return broad results. The application only retains entries for the exact domain or its direct `*.` wildcard and caps displayed entries to 40. Queries fetching more than 3 MB of JSON raise a source-specific error rather than exhausting memory. Data is historical and can include duplicate or delayed entries.

All HTTP requests use HTTPS, timeouts, a response-size limit, and **do not follow HTTP redirects**. Network failures, invalid JSON, missing results and provider rate limits are presented separately per source; one source failing does not invent data for another source. RDAP is supplied by IANA-listed HTTPS endpoints, not URLs typed by the user.

## Data structure and uncertainty

Each source returns:

```json
{
  "source": "... provider or resolver ...",
  "status": "ok | no_data | error",
  "data": {},
  "error": null,
  "note": "... interpretation or limitations ..."
}
```

`ok` means public data was returned, **not** that a domain is owned by a specific person or is secure. `partial` indicates that some record types returned data but others failed. `no_data` means there was no matching public response; `error` means that the lookup could not be completed/reliably interpreted. The export includes a timestamp and a disclaimer. There is no risk score or claim of vulnerability detection.

### Reproducible synthetic example

`examples/synthetic_example.json` is a **fabricated fixture** for UI inspection only. It uses RFC 5737 documentation IP address space (`192.0.2.0/24`) and explicitly labels all sources as synthetic. Never cite synthetic fixture content as observed DNS/RDAP/CT findings. Live screenshots should be taken only after running the dashboard yourself.

## Testing and verification

```powershell
python -m compileall -q src cli.py app.py tests
python -m pytest -q
python -m pytest --cov=src --cov=cli --cov-report=term-missing -q
python cli.py --help
```

Tests use deterministic JSON fixtures and an autouse fixture that blocks raw socket connections. They substitute fake HTTP sessions and DNS resolvers; **no real network requests are needed or allowed during tests**. Test scenarios cover bad URL input, source errors, malformed JSON, HTTP redirects, oversized responses, DNS timeouts, missing results, confidentiality, exporting and offline CLI use.

**Verified in the preparation environment:** 60 tests passed and 92% combined coverage for CLI/core code under Python 3.13. See `docs/REVIEW-AR.md` for details and limitations. This is *not* a live service integration benchmark and does not measure Streamlit layout across browsers.

## Known limitations / research questions

- A default HTTP timeout of 5 seconds may be too short for crt.sh, and its JSON endpoint is best-effort, not a guaranteed SLA. Increase timeout up to 30 seconds if necessary.
- Some RDAP operators use redirects; this version intentionally does **not** follow them for endpoint security. A redirect is reported as an error.
- RDAP registration events and DNS data may be incomplete or redacted.
- Domain verification is **format-only**, not proof of registration or DNS availability.
- This application does not support batch domains, user account mapping, email enumeration, subdomain crawling or active target probes.
- Public TXT records can expose service-configuration strings. Review exports before sharing publicly.
- There is no live-data database or scheduled monitoring. A collected report stays in the current Streamlit session only; JSON/CSV are created on demand.
- No cross-platform browser screenshot or live-source success benchmark is claimed.

## Responsible use

Only query domains you have permission or a legitimate, lawful reason to investigate, observe public data provider terms and rate limits, and do not publish accidental personal information. Read [SECURITY.md](SECURITY.md). This tool makes HTTPS requests to **public metadata providers**, not HTTP probes against the target host.

## Suggested Conventional Commits

Use commit subjects only after you have reviewed the corresponding code changes. An honest single commit for the current reviewed snapshot is acceptable; do not manufacture historical commits.

```text
fix: replace broken RDAP and CT placeholders with public-source collectors
feat: add deterministic domain validator and structured exports
feat(ui): add Streamlit dashboard and clearly labeled offline demo
test: add isolated fixtures and offline regression tests
docs: document methodology, limitations and reproducible setup
```

## License

MIT — see [LICENSE](LICENSE). Project authored and maintained as part of a cybersecurity learning and graduate-study portfolio.
