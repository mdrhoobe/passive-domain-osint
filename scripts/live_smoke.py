"""Run one real, passive collector request for the reserved example.com domain.

Print only per-source statuses; never write collected records to the repository.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import DomainCollector  # noqa: E402
from src.output import export_csv, export_json  # noqa: E402


def main() -> int:
    domain = "example.com"
    result = DomainCollector(timeout=12).run(domain)
    assert result["domain"] == domain and not result.get("demo")
    valid = {"ok", "partial", "no_data", "error"}
    assert all(result[key]["status"] in valid for key in ("rdap", "dns", "cert"))

    restored = json.loads(export_json(result))
    assert restored["domain"] == domain
    assert restored["summary"] == result["summary"]

    rows = list(csv.DictReader(io.StringIO(export_csv(result))))
    assert rows and {r["source"] for r in rows} == {"rdap", "dns", "cert"}
    assert all(row["domain"] == domain for row in rows)

    print("LIVE collection via public RDAP, DNS and CT sources:")
    for key in ("rdap", "dns", "cert"):
        entry = result[key]
        print(f"  {key.upper()}: {entry['status']}")
        if entry.get("error"):
            print(f"    provider error: {entry['error']}")
    print(f"JSON export: PASS; CSV export: PASS ({len(rows)} rows)")

    if not any(result[k]["status"] in {"ok", "partial"} for k in ("rdap", "dns", "cert")):
        print("INCONCLUSIVE: No provider returned data; check network, timeouts or rate limits.")
        return 2
    if any(result[k]["status"] == "error" for k in ("rdap", "dns", "cert")):
        print("PARTIAL: some public providers failed; this is not full live-source verification.")
    else:
        print("Live provider responses observed; missing data is not a security conclusion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
