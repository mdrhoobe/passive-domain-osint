"""Command-line interface for passive domain metadata research."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from src import DomainCollector, normalize_domain
from src.exceptions import ValidationError
from src.output import export_json, export_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Passive Domain OSINT: public RDAP, DNS and CT metadata for one domain.")
    subs = parser.add_subparsers(dest="command", required=True)
    val = subs.add_parser("validate", help="Check a domain without making any network requests")
    val.add_argument("domain")
    collect = subs.add_parser("collect", help="Collect public metadata (makes public API/DNS requests)")
    collect.add_argument("domain")
    collect.add_argument("--timeout", type=float, default=5.0, help="Per-request timeout in seconds (default: 5)")
    collect.add_argument("--format", choices=("summary", "json", "csv"), default="summary")
    collect.add_argument("--output", type=Path, help="Optional path to write formatted output; never writes by default")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        domain = normalize_domain(args.domain)
        if args.command == "validate":
            print(f"Valid domain: {domain} (format only; no DNS or network check)")
            return 0
        if not 0 < args.timeout <= 30:
            raise ValidationError("Timeout must be greater than 0 and at most 30 seconds.")
        result = DomainCollector(timeout=args.timeout).run(domain)
        if args.format == "json":
            content = export_json(result)
        elif args.format == "csv":
            content = export_csv(result)
        else:
            content = "\n".join([f"Domain: {domain}", f"Collected at: {result['collected_at']}",
                                 *[f"{key.upper()}: {result[key]['status']} ({result[key]['note'] or result[key]['error'] or 'Public metadata'})"
                                   for key in ("rdap", "dns", "cert")],
                                 "Note: Public metadata is not a vulnerability assessment."])
        if args.output:
            args.output.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")
            print(f"Saved: {args.output}")
        else:
            print(content)
        return 0 if (result["summary"]["error"] + result["summary"]["partial"]) == 0 else 2
    except (ValidationError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
