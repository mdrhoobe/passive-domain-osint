"""Streamlit interface; run: streamlit run app.py."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from src import DomainCollector, normalize_domain
from src.exceptions import ValidationError
from src.output import export_json, export_csv

st.set_page_config(
    page_title="Passive Domain OSINT",
    page_icon="🌐",
    layout="wide",
)

css_path = Path(__file__).resolve().parent / "assets" / "ui.css"
if css_path.is_file():
    st.markdown(
        "<style>" + css_path.read_text(encoding="utf-8") + "</style>",
        unsafe_allow_html=True,
    )

st.markdown("""
<div class="product-header">
    <div class="brand-symbol">
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#007A71"
        stroke-width="1.7"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
    >
        <circle cx="12" cy="12" r="9"/>
        <path d="M3 12h18"/>
        <path d="M12 3a15 15 0 0 1 0 18"/>
        <path d="M12 3a15 15 0 0 0 0 18"/>
    </svg>
</div>
    <div class="brand-copy">
        <strong>Passive Domain OSINT</strong>
        <span>DOMAIN INTELLIGENCE STUDIO</span>
    </div>
    <div class="brand-version">RESEARCH / V0.2</div>
</div>
<div class="palette-line">
  <span></span><span></span><span></span>
  <span></span><span></span><span></span>
</div>
<div class="workspace-intro">
    <div class="eyebrow">PUBLIC-SOURCE RESEARCH</div>
    <h1>Investigate a domain.</h1>
    <p>Explore registry information, DNS records and certificate
    transparency history from independent public sources.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Research workspace")
    st.caption("Passive Domain Intelligence · v0.2")
    st.divider()
    st.markdown("**Available sources**")
    st.write("RDAP | DNS | Certificate Transparency")
    with st.expander("Scope and limitations"):
        st.write(
            "One domain per search. Public sources only. "
            "No port scanning or credential testing."
        )
        st.caption(
            "CT records are historical. RDAP may redact personal "
            "details. DNS results depend on resolver and time."
        )
    st.divider()
    load_demo = st.button(
        "Load synthetic demo (offline)",
        width="stretch",
        help="Uses local demonstration fixtures; no network request.",
    )
    st.caption("Academic research project | Python 3.11+")

st.markdown("#### Domain lookup")
st.caption("Enter one domain to collect publicly available metadata.")

with st.form("domain_search", clear_on_submit=False):
    col_domain, col_timeout = st.columns([4, 1])
    with col_domain:
        domain_input = st.text_input(
            "Domain",
            placeholder="example.com",
            help="ASCII domain or bare HTTP(S) URL; no paths, ports or IP addresses",
        )
    with col_timeout:
        timeout = st.number_input(
            "Timeout (seconds)",
            min_value=2,
            max_value=20,
            value=5,
        )
    submitted = st.form_submit_button(
        "Collect public metadata",
        type="primary",
        width="stretch",
    )

if "result" not in st.session_state:
    st.session_state.result = None
if "input_error" not in st.session_state:
    st.session_state.input_error = None

if load_demo:
    st.session_state.input_error = None
    st.session_state.result = json.loads((Path(__file__).parent / "examples" / "synthetic_example.json").read_text(encoding="utf-8"))

if submitted:
    st.session_state.input_error = None
    st.session_state.result = None
    try:
        domain = normalize_domain(domain_input)
    except ValidationError as exc:
        st.session_state.input_error = str(exc)
    else:
        with st.spinner("Requesting public metadata; sources may be unavailable or rate-limited..."):
            st.session_state.result = DomainCollector(timeout=timeout).run(domain)

if st.session_state.input_error:
    st.error(st.session_state.input_error)

result = st.session_state.result
if result is None and not st.session_state.input_error:
    st.markdown("#### What this workspace collects")
    features = st.columns(3)
    for column, name, description in zip(
        features,
        ("RDAP", "DNS", "Certificate Transparency"),
        (
            "Public registry metadata",
            "Records from your DNS resolver",
            "Historical public certificate logs",
        ),
    ):
        with column:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(description)

elif result:
    st.subheader(result["domain"])
    if result.get("demo"):
        st.warning("SYNTHETIC EXAMPLE · No network was queried. Values are demonstration fixtures, not real domain findings.")
    else:
        st.caption("Checked at " + result["collected_at"] + " · Public metadata snapshot, not a security assessment.")
    values = result["summary"]
    st.markdown("#### Source coverage")

    source_columns = st.columns(3)
    sources = (
        ("rdap", "RDAP", "Registry metadata"),
        ("dns", "DNS", "Public DNS records"),
        ("cert", "CT Logs", "Certificate history"),
    )
    labels = {
        "ok": "Data available",
        "partial": "Partial data",
        "no_data": "No data found",
        "error": "Source unavailable",
    }

    for column, (key, title, description) in zip(source_columns, sources):
        status = result[key].get("status")
        with column:
            with st.container(border=True):
                st.caption(description)
                st.markdown(f"**{title}**")
                st.write(labels.get(status, "Unknown status"))

    if values["error"] or values["partial"]:
        st.warning("Some sources or record types could not be queried. Other results remain available.")
    if not values["ok"] and not values["error"]:
        st.info("No public metadata was returned for this domain.")
    tabs = st.tabs(["RDAP", "DNS", "Certificate Transparency", "Export / Methodology"])
    for tab, key in zip(tabs[:3], ("rdap", "dns", "cert")):
        with tab:
            item = result[key]
            st.caption(f"Source: {item['source']} · Status: {item['status']}")
            if item["status"] == "error":
                st.error(item["error"] or "Source failed")
            elif item["status"] == "no_data":
                st.info(item["note"] or "No data found")
            else:
                if item["status"] == "partial":
                    st.warning("Partial result: " + (item["error"] or "Some record types failed"))
                if key == "dns":
                    records = item["data"].get("records", {})
                    for kind, values in records.items():
                        with st.expander(
                            f"{kind} — {len(values)} records",
                            expanded=kind in {"A", "MX"},
                        ):
                            if values:
                                st.code(chr(10).join(map(str, values)), language=None)
                            else:
                                st.caption("No records returned")

                elif key == "cert":
                    cert_data = item["data"]
                    entries = cert_data.get("entries", [])
                    st.caption(
                        f"{cert_data.get('matched_entries', 0)} matching entries; "
                        f"up to {cert_data.get('display_limit', 40)} shown"
                    )
                    st.dataframe(
                        entries,
                        hide_index=True,
                        width="stretch",
                    )

                elif key == "rdap":
                    rdap_data = item["data"]

                    st.write(
                        f"**Domain Name:** {rdap_data.get('name') or 'N/A'}"
                    )
                    st.write(
                        f"**Registration Handle:** {rdap_data.get('handle') or 'N/A'}"
                    )

                    statuses = rdap_data.get("status") or []
                    st.markdown("**Domain Statuses**")
                    if isinstance(statuses, list) and statuses:
                        for status in statuses:
                            st.write(f"- {status}")
                    else:
                        st.caption("No domain statuses returned.")

                    with st.expander("Nameservers"):
                        nameservers = rdap_data.get("nameservers") or []
                        if nameservers:
                            for nameserver in nameservers:
                                st.write(f"- {nameserver}")
                        else:
                            st.caption("No nameservers returned.")

                    with st.expander("Registrar Information"):
                        handles = rdap_data.get("registrar_handles") or []
                        if handles:
                            for handle in handles:
                                st.write(f"- {handle}")
                        else:
                            st.caption("No registrar information available.")

                    with st.expander("Registration Events"):
                        events = rdap_data.get("events") or []
                        if events:
                            for event in events:
                                if isinstance(event, dict):
                                    action = event.get("action", "Unknown")
                                    date = event.get("date", "N/A")
                                    st.write(f"- {action}: {date}")
                        else:
                            st.caption("No registration events returned.")

                    with st.expander("Raw RDAP data"):
                        st.json(rdap_data, expanded=False)
            if item.get("note"):
                st.caption(item["note"])
    with tabs[3]:
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button("Download JSON" + (" (synthetic)" if result.get("demo") else ""), data=export_json(result).encode("utf-8"),
                               file_name=f"{result['domain']}-public-osint.json", mime="application/json", width="stretch")
        with col_b:
            st.download_button("Download CSV" + (" (synthetic)" if result.get("demo") else ""), data=export_csv(result).encode("utf-8-sig"),
                               file_name=f"{result['domain']}-public-osint.csv", mime="text/csv", width="stretch")
        st.markdown("**Interpretation**: records are third-party observations. A missing record does not imply risk or safety. Exported data contains no contact vCards or person-level profiling.")
        st.json({k: {"source": result[k]["source"], "status": result[k]["status"], "note": result[k]["note"]}
                 for k in ("rdap", "dns", "cert")})
