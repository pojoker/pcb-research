"""Offline CLI for the DP3 tree contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from .errors import DP3Error, SchemaError
from .rendering import render_coverage
from .schema import load_tree
from .validation import validate_process_equipment_map, validate_samples, validate_tree


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SchemaError(f"input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SchemaError(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_record_list(path: Path, label: str) -> list[dict[str, Any]]:
    payload = _read_json(path)
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise SchemaError(f"{label} must be a JSON array of objects")
    return payload


def _validate_tree(args: argparse.Namespace) -> int:
    tree = load_tree(args.tree)
    report = validate_tree(tree)
    _write_json(args.output, report.as_dict())
    return 0 if report.ok else 1


def _validate_samples(args: argparse.Namespace) -> int:
    tree = load_tree(args.tree)
    report = validate_samples(_load_record_list(args.input, "samples"), tree)
    _write_json(args.output, report.as_dict())
    return 0 if report.ok else 1


def _validate_map(args: argparse.Namespace) -> int:
    tree = load_tree(args.tree)
    report = validate_process_equipment_map(_load_record_list(args.input, "process_equipment_map"), tree)
    _write_json(args.output, report.as_dict())
    return 0 if report.ok else 1


def _render(args: argparse.Namespace) -> int:
    tree = load_tree(args.tree)
    payload = _read_json(args.input)
    if not isinstance(payload, dict) or set(payload) != {"attachments", "coverage"}:
        raise SchemaError("render input must contain exactly attachments and coverage")
    if not isinstance(payload["attachments"], list) or not isinstance(payload["coverage"], list):
        raise SchemaError("render attachments and coverage must be lists")
    report, rows = render_coverage(tree, payload["attachments"], payload["coverage"])
    _write_json(args.output, {"validation": report.as_dict(), "cells": rows})
    return 0 if report.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline-first DP3 PCB tree contract validator")
    subparsers = parser.add_subparsers(dest="command", required=True)
    tree = subparsers.add_parser("validate-tree", help="validate the canonical tree.yaml")
    tree.add_argument("--tree", type=Path, required=True)
    tree.add_argument("--output", type=Path, required=True)
    tree.set_defaults(handler=_validate_tree)
    for command, handler, label in (
        ("validate-samples", _validate_samples, "board/capability sample JSON"),
        ("validate-map", _validate_map, "process_equipment_map JSON"),
    ):
        subparser = subparsers.add_parser(command, help=f"validate {label}")
        subparser.add_argument("--tree", type=Path, required=True)
        subparser.add_argument("--input", type=Path, required=True)
        subparser.add_argument("--output", type=Path, required=True)
        subparser.set_defaults(handler=handler)
    render = subparsers.add_parser("render", help="render all 30 cells with explicit empty spaces")
    render.add_argument("--tree", type=Path, required=True)
    render.add_argument("--input", type=Path, required=True)
    render.add_argument("--output", type=Path, required=True)
    render.set_defaults(handler=_render)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except DP3Error as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
