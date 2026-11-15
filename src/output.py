"""Download-ready, human-readable JSON and RFC 4180-style CSV exports."""
from __future__ import annotations
import csv
import io
import json

SOURCES = ("rdap", "dns", "cert")


def export_json(results: dict) -> str:
    return json.dumps(results, indent=2, ensure_ascii=False, sort_keys=True)


def _safe_cell(value: object) -> str:
    """Prevent spreadsheet formula execution on user-controlled/public TXT fields."""
    text = str(value if value is not None else "")
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def export_csv(results: dict) -> str:
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["domain", "collected_at", "source", "status", "field", "value", "note"])
    for source in SOURCES:
        item = results.get(source) or {}
        data = item.get("data") or {}
        if not data:
            writer.writerow([results.get("domain", ""), results.get("collected_at", ""),
                             source, item.get("status", "unknown"), "",
                             _safe_cell(item.get("error") or ""), item.get("note") or ""])
            continue
        for key, value in data.items():
            writer.writerow([results.get("domain", ""), results.get("collected_at", ""),
                             source, item.get("status", "unknown"), key,
                             _safe_cell(json.dumps(value, ensure_ascii=False)), item.get("note") or ""])
    return out.getvalue()


class OutputExporter:
    export_json = staticmethod(export_json)
    export_csv = staticmethod(export_csv)
