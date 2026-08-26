"""Small offline CLI for DP2 registry checks and opt-in probe recordings."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .accessibility import probe_t1_sources
from .customs8534 import check_8534_freeze
from .echoes import EchoMention, cluster_numeric_echoes
from .schema import validate_ledger_record


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_ledger(args: argparse.Namespace) -> int:
    results = []
    for index, row in enumerate(_read_csv(args.input), start=2):
        result = validate_ledger_record(row)
        results.append({"line": index, "valid": result.valid, "errors": result.errors, "warnings": result.warnings})
    _write_json(args.output, results)
    return 0 if all(item["valid"] for item in results) else 1


def _probe_t1(args: argparse.Namespace) -> int:
    results = probe_t1_sources(_read_csv(args.input), enable_network=args.enable_network, timeout_seconds=args.timeout)
    _write_json(args.output, [result.as_dict() for result in results])
    return 0


def _check_8534(args: argparse.Namespace) -> int:
    rows = _read_csv(args.input)
    if len(rows) != 1:
        raise SystemExit("8534 template must contain exactly one scope row")
    result = check_8534_freeze(rows[0])
    _write_json(args.output, asdict(result))
    return 0 if not result.missing_fields and not result.errors else 1


def _echoes(args: argparse.Namespace) -> int:
    with args.input.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    mentions = [EchoMention(**row) for row in payload]
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
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
