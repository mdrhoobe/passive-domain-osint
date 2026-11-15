# Security & ethical scope

Passive Domain OSINT is a **metadata research application**. It is not a vulnerability scanner, penetration-test platform, credential collector, or evidence that a domain is safe or compromised.

## Sources and network traffic

- **IANA** RDAP bootstrap (`data.iana.org`), then the advertised public RDAP provider over HTTPS.
- Your **configured recursive DNS resolver** for one hostname's A, AAAA, MX, NS and TXT records.
- **crt.sh** public certificate transparency JSON endpoint.
- No direct HTTP request to the *target* website, no port scanning, SSH, authentication, enumeration of people or internal addresses, or TLS probing.

RDAP/CT providers receive the queried domain. DNS resolvers can log DNS queries. No credentials, API tokens, or private information are requested by the program. No contact vCards from RDAP are retained. Public DNS TXT strings may contain sensitive operational clues; avoid redistributing exports without review.

## Input constraints and URL safety

- One ASCII domain per query; Unicode domains require explicit IDNA/Punycode A-labels.
- URLs may contain `http://` or `https://` plus hostname and optional terminal `/`, but **not** paths, ports, credentials, or query strings.
- The user cannot supply a custom RDAP endpoint. HTTPS bootstrap targets are selected from IANA, reject IP literals and local hostnames, and redirects are not followed.
- HTTP response sizes are capped at 3 MB; timeouts are bounded to 30 seconds per request.
- CSV exports sanitize formula-like raw cells; reviews of public TXT data before sharing remain recommended.

## Limitations

- This is a learning project, not an independently audited service.
- crt.sh is rate-limited/best-effort and may return large or delayed data; the client may report an error.
- DNS and RDAP are public and potentially incomplete or stale; missing information does not confirm safety or risk.
- The application neither encrypts nor stores exports; downloaded data is controlled by the user's filesystem.
- A Streamlit deployment must be reviewed and configured before exposure to the public internet.

## Reporting an issue

Please open a GitHub issue in the project repository, without posting passwords, tokens, private targets, or private identities. Do not commit personal data or collected production target results.
