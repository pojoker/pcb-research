"""Command line entry points for offline DP4 validation and measurement."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .corpus import CorpusScanner, load_corpus_jsonl
from .fixtures import load_fixtures, run_golden_fixtures
from .schema import load_lexicon
from .validation import compile_gate, validate_entries


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON = PACKAGE_ROOT / "data" / "candidate_lexicon.json"
DEFAULT_FIXTURES = PACKAGE_ROOT / "fixtures" / "golden.json"


def _load_compiled(lexicon_path: str | Path, fixture_path: str | Path = DEFAULT_FIXTURES):
    entries = load_lexicon(lexicon_path)
    fixture_index = {fixture.fixture_id: fixture for fixture in load_fixtures(str(fixture_path))}
    validate_entries(entries, fixture_index)
    return entries, compile_gate(entries)


def cmd_validate(args: argparse.Namespace) -> int:
    entries, compiled = _load_compiled(args.lexicon, args.fixtures)
    fixtures = load_fixtures(str(args.fixtures))
    results = run_golden_fixtures(compiled, fixtures)
    payload = {
        "status": "pending_review",
        "entry_count": len(entries),
        "regex_compiled": True,
        "golden_fixture_count": len(results),
        "golden_failures": [result.as_dict() for result in results if not result.passed],
        "review_note": "Validation is mechanical; candidate status remains待核.",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not payload["golden_failures"] else 1


def cmd_measure(args: argparse.Namespace) -> int:
    _, compiled = _load_compiled(args.lexicon)
    documents = load_corpus_jsonl(str(args.corpus))
    scan = CorpusScanner(compiled).scan(documents, scope=args.scope, date=args.date)
    output = scan.as_json()
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    from .selftest import run

    return run(verbose=not args.quiet)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DP4 offline candidate lexicon validator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="run schema, regex and golden fixture gates")
    validate.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    validate.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    validate.set_defaults(func=cmd_validate)

    measure = subparsers.add_parser("measure", help="record four-key corpus measurements and collisions")
    measure.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    measure.add_argument("--corpus", required=True, help="JSONL rows with id and text")
    measure.add_argument("--scope", required=True)
    measure.add_argument("--date", required=True)
    measure.add_argument("--output")
    measure.set_defaults(func=cmd_measure)

    selftest = subparsers.add_parser("selftest", help="run offline standard-library selftests")
    selftest.add_argument("--quiet", action="store_true")
    selftest.set_defaults(func=cmd_selftest)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # CLI should fail closed with a useful one-line error.
        print(f"dp4-lexicon: ERROR: {exc}", file=sys.stderr)
        return 2
