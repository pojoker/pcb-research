#!/usr/bin/env python3
"""Command line entry point for the offline-first DP1 registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters import fetch_draft, fetch_twse_listed_company_draft
from .registry import (
    FROZEN_FIELDS,
    INCLUSION_DECISION_FIELDS,
    build_snapshot_metadata,
    diff_snapshots,
    load_csv,
    merge_decisions,
    report_text,
    validate_frozen,
    validate_inclusion_decisions,
    write_csv,
)


DIFF_FIELDS = (
    "change",
    "entity_id",
    "before_snapshot_id",
    "after_snapshot_id",
    "name",
    "triage_required",
)


def _validate(args: argparse.Namespace) -> int:
    frozen = load_csv(args.frozen, FROZEN_FIELDS)
    decisions = load_csv(args.decisions, INCLUSION_DECISION_FIELDS)
    frozen_report = validate_frozen(frozen, decisions)
    print(report_text(frozen_report))
    decision_report = validate_inclusion_decisions(decisions, frozen)
    print(report_text(decision_report))
    return 0 if frozen_report.ok and decision_report.ok else 1


def _snapshot(args: argparse.Namespace) -> int:
    rows = load_csv(args.frozen, FROZEN_FIELDS)
    report = validate_frozen(rows)
    if not report.ok:
        print(report_text(report))
        return 1
    metadata = build_snapshot_metadata(
        rows,
        source_name=args.source_name,
        source_kind=args.source_kind,
        source_url=args.source_url,
        query_date=args.query_date,
        adapter_name=args.adapter_name,
        input_path=args.frozen,
        freeze_status=args.freeze_status,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


def _diff(args: argparse.Namespace) -> int:
    before = load_csv(args.before, FROZEN_FIELDS)
    after = load_csv(args.after, FROZEN_FIELDS)
    existing = load_csv(args.existing_decisions, INCLUSION_DECISION_FIELDS) if args.existing_decisions else []
    diff_rows, triage_rows = diff_snapshots(
        before,
        after,
        before_snapshot_id=args.before_snapshot_id,
        after_snapshot_id=args.after_snapshot_id,
        query_date=args.query_date,
        existing_decisions=existing,
    )
    out_dir = Path(args.out_dir)
    write_csv(out_dir / "diff.csv", DIFF_FIELDS, diff_rows)
    write_csv(out_dir / "triage.csv", INCLUSION_DECISION_FIELDS, triage_rows)
    write_csv(out_dir / "inclusion_decision.csv", INCLUSION_DECISION_FIELDS, merge_decisions(existing, triage_rows))
    print(f"diff rows: {len(diff_rows)}; generated triage rows: {len(triage_rows)}")
    return 0


def _draft(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    fixture_path = config.get("fixture_path")
    if fixture_path and not Path(str(fixture_path)).is_absolute():
        config["fixture_path"] = str(config_path.parent / str(fixture_path))
    rows = fetch_draft(config)
    write_csv(args.output, FROZEN_FIELDS, rows)
    print(f"draft rows: {len(rows)}; status forced to 待核")
    return 0


def _twse_draft(args: argparse.Namespace) -> int:
    rows = fetch_twse_listed_company_draft(
        query_date=args.query_date,
        fixture_path=args.fixture,
        timeout_seconds=args.timeout_seconds,
    )
    write_csv(args.output, FROZEN_FIELDS, rows)
    print(f"TWSE listed-company draft rows: {len(rows)}; status forced to 待核")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PCB DP1 denominator registry")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--frozen", required=True)
    validate.add_argument("--decisions", required=True)
    validate.set_defaults(func=_validate)

    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--frozen", required=True)
    snapshot.add_argument("--output", required=True)
    snapshot.add_argument("--source-name", required=True)
    snapshot.add_argument("--source-kind", required=True)
    snapshot.add_argument("--source-url", required=True)
    snapshot.add_argument("--query-date", required=True)
    snapshot.add_argument("--adapter-name", required=True)
    snapshot.add_argument("--freeze-status", default="待核")
    snapshot.set_defaults(func=_snapshot)

    diff = sub.add_parser("diff")
    diff.add_argument("--before", required=True)
    diff.add_argument("--after", required=True)
    diff.add_argument("--before-snapshot-id", required=True)
    diff.add_argument("--after-snapshot-id", required=True)
    diff.add_argument("--query-date", required=True)
    diff.add_argument("--existing-decisions")
    diff.add_argument("--out-dir", required=True)
    diff.set_defaults(func=_diff)

    draft = sub.add_parser("fetch-draft")
    draft.add_argument("--config", required=True)
    draft.add_argument("--output", required=True)
    draft.set_defaults(func=_draft)

    twse_draft = sub.add_parser("fetch-twse-listed-draft")
    twse_draft.add_argument("--query-date", required=True)
    twse_draft.add_argument("--fixture")
    twse_draft.add_argument("--timeout-seconds", type=float, default=20)
    twse_draft.add_argument("--output", required=True)
    twse_draft.set_defaults(func=_twse_draft)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
