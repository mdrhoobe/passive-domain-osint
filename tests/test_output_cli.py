"""Offline export, CSV injection, and CLI checks."""
import csv
import io
import json

from src.output import export_csv, export_json
from cli import main


def test_json_and_csv_exports(fake_clients):
    from src.collector import DomainCollector
    result = DomainCollector(session=fake_clients[0], resolver=fake_clients[1]).run("example.com")
    decoded = json.loads(export_json(result))
    assert decoded["rdap"]["status"] == "ok"
    assert decoded["domain"] == "example.com"
    rows = list(csv.DictReader(io.StringIO(export_csv(result))))
    assert {r["source"] for r in rows} == {"rdap", "dns", "cert"}
    assert all(r["domain"] == "example.com" for r in rows)


def test_csv_formula_injection():
    result = {"domain": "example.com", "collected_at": "2026-01-01T00:00:00Z",
              "dns": {"status": "ok", "note": None,
                      "data": {"records": {"TXT": ["=HYPERLINK(\"evil\")"]}}}}
    body = export_csv(result)
    assert "'=HYPERLINK" not in body  # JSON quoted field, not formula at beginning
    parsed = list(csv.DictReader(io.StringIO(body)))
    assert next(row for row in parsed if row["source"] == "dns")["value"].startswith('{')


def test_csv_formula_injection_raw_cell():
    from src.output import _safe_cell
    assert _safe_cell("=1+1") == "'=1+1"
    assert _safe_cell(" +cmd") == "' +cmd"


def test_cli_validate_valid_and_invalid(capsys):
    assert main(["validate", "https://EXAMPLE.COM"]) == 0
    assert "example.com" in capsys.readouterr().out
    assert main(["validate", "https://example.com/admin"]) == 1
    assert "path" in capsys.readouterr().err.lower()


def test_cli_collect_offline(monkeypatch, fake_clients, capsys):
    from cli import DomainCollector as Collector
    monkeypatch.setattr("cli.DomainCollector", lambda **kwargs: Collector(session=fake_clients[0], resolver=fake_clients[1], **kwargs))
    assert main(["collect", "example.com", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["summary"] == {"ok": 3, "partial": 0, "no_data": 0, "error": 0}


def test_cli_timeout_rejection(capsys):
    assert main(["collect", "example.com", "--timeout", "-1"]) == 1
    assert "timeout" in capsys.readouterr().err.lower()
