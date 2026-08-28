"""Machine-readable command line interface for DP7."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .validation import validate_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DP7 human-authored casebook validator")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", help="validate a DP7 JSON document")
    check.add_argument("--input", required=True, help="casebook JSON input")
    check.add_argument("--output", help="write JSON report to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        document = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "input_error": str(exc)}, ensure_ascii=False))
        return 2
    report = validate_document(document)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if report["valid"] else 1
