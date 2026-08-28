"""Machine-readable CLI for the offline DP5 ledger contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from .errors import DP5Error
from .schema import load_active_cells, load_json
from .validation import validate_ledger


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate(args: argparse.Namespace) -> int:
    try:
        report = validate_ledger(load_json(args.input), load_active_cells(args.tree))
        _write(args.output, report.as_dict())
        return 0 if report.ok else 1
    except DP5Error as exc:
        _write(args.output, {"ok": False, "errors": [str(exc)], "warnings": [], "details": {}})
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline DP5 PCB evidence/outsourcing ledger validator")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate-ledger", help="validate a complete strict DP5 ledger JSON document")
    validate.add_argument("--tree", type=Path, required=True, help="read-only canonical JSON-compatible tree.yaml")
    validate.add_argument("--input", type=Path, required=True, help="DP5 ledger JSON")
    validate.add_argument("--output", type=Path, required=True, help="machine-readable validation report JSON")
    validate.set_defaults(handler=_validate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
