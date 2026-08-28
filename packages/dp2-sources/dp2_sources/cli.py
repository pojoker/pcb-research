"""Small offline CLI for DP2 registry checks and opt-in probe recordings."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Sequence

from .accessibility import T1_PROBE_FIELDS, probe_t1_sources
from .customs8534 import FREEZE_TEMPLATE_FIELDS, check_8534_freeze
from .echoes import ECHO_MENTION_FIELDS, EchoMention, cluster_numeric_echoes
from .input_schema import InputSchemaError, load_json, parse_exact_json_records, read_csv_records
from .schema import LEDGER_FIELDS, validate_ledger_record


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_ledger(args: argparse.Namespace) -> int:
    results = []
    for index, row in enumerate(read_csv_records(args.input, LEDGER_FIELDS, "source ledger"), start=2):
        result = validate_ledger_record(row)
        results.append({"line": index, "valid": result.valid, "errors": result.errors, "warnings": result.warnings})
    _write_json(args.output, results)
    return 0 if all(item["valid"] for item in results) else 1


def _probe_t1(args: argparse.Namespace) -> int:
    records = read_csv_records(args.input, T1_PROBE_FIELDS, "T1 probe")
    results = probe_t1_sources(records, enable_network=args.enable_network, timeout_seconds=args.timeout)
    _write_json(args.output, [result.as_dict() for result in results])
    return 0


def _check_8534(args: argparse.Namespace) -> int:
    rows = read_csv_records(args.input, FREEZE_TEMPLATE_FIELDS, "8534 freeze")
    if len(rows) != 1:
        raise InputSchemaError("8534 freeze CSV must contain exactly one scope row after its header.")
    result = check_8534_freeze(rows[0])
    _write_json(args.output, asdict(result))
    return 0 if not result.missing_fields and not result.errors else 1


def _echoes(args: argparse.Namespace) -> int:
    payload = load_json(args.input, "detect-echoes input")
    records = parse_exact_json_records(payload, ECHO_MENTION_FIELDS, "detect-echoes input")
    mentions = [EchoMention(**row) for row in records]
    _write_json(args.output, [asdict(cluster) for cluster in cluster_numeric_echoes(mentions)])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline-first DP2 source registry tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ledger = subparsers.add_parser("validate-ledger", help="validate a source-ledger CSV")
    ledger.add_argument("input", type=Path)
    ledger.add_argument("output", type=Path)
    ledger.set_defaults(handler=_validate_ledger)

    probe = subparsers.add_parser("probe-t1", help="record endpoint reachability; network is off by default")
    probe.add_argument("input", type=Path)
    probe.add_argument("output", type=Path)
    probe.add_argument("--enable-network", action="store_true", help="explicitly allow HTTP HEAD requests")
    probe.add_argument("--timeout", type=float, default=10.0)
    probe.set_defaults(handler=_probe_t1)

    freeze = subparsers.add_parser("check-8534", help="check one 8534 scope-freeze template row")
    freeze.add_argument("input", type=Path)
    freeze.add_argument("output", type=Path)
    freeze.set_defaults(handler=_check_8534)

    echoes = subparsers.add_parser("detect-echoes", help="cluster supplied same-claim numeric echoes")
    echoes.add_argument("input", type=Path)
    echoes.add_argument("output", type=Path)
    echoes.set_defaults(handler=_echoes)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except InputSchemaError as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
