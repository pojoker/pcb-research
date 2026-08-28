from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .errors import NonFiniteNumber
from .rendering import render_json, render_text
from .validation import validate_document


def _constant(token: str) -> NonFiniteNumber:
    return NonFiniteNumber(token)


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=_constant)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DP6 three-state publication gate")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="validate one DP6 payload")
    validate.add_argument("--input", required=True)
    validate.add_argument("--tolerance-adr", help="required for quantitative rows; omission keeps them indeterminate")
    validate.add_argument("--output")
    validate.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        document = _load(args.input)
        adr = _load(args.tolerance_adr) if args.tolerance_adr else None
    except (OSError, json.JSONDecodeError) as exc:
        print(f"DP6 input error: {exc}")
        return 2
    report = validate_document(document, adr)
    output = render_json(report) if args.format == "json" else render_text(report)
    if args.output:
        Path(args.output).write_text(output + ("\n" if args.format == "json" else ""), encoding="utf-8")
    else:
        print(output)
    return 0 if report["overall_status"] == "pass" else 1
