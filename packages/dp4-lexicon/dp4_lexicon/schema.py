"""Strict, JSON-friendly schemas for DP4 candidate vocabulary records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .errors import SchemaError


LEXICON_FIELDS = (
    "term",
    "match_mode",
    "include_patterns",
    "exclude_patterns",
    "target_cell",
    "case_policy",
    "test_fixture_ids",
)

MATCH_MODES = frozenset(
    {"literal", "regex", "context_any", "context_all", "context_2_of"}
)
CASE_POLICIES = frozenset({"sensitive", "insensitive"})


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SchemaError(f"{field} must be a list of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise SchemaError(f"{field}[{index}] must be a non-empty string")
        result.append(item)
    return result


@dataclass(frozen=True)
class LexiconEntry:
    """One candidate record using the seven-field DP4 schema.

    ``include_patterns`` and ``exclude_patterns`` are executable Python regular
    expressions.  The entry is a candidate regardless of whether its golden
    fixtures pass; this object carries no approval state.
    """

    term: str
    match_mode: str
    include_patterns: tuple[str, ...]
    exclude_patterns: tuple[str, ...]
    target_cell: str
    case_policy: str
    test_fixture_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, record: Mapping[str, Any]) -> "LexiconEntry":
        if not isinstance(record, Mapping):
            raise SchemaError("each lexicon record must be an object")
        keys = set(record)
        missing = [field for field in LEXICON_FIELDS if field not in keys]
        extra = sorted(keys.difference(LEXICON_FIELDS))
        if missing:
            raise SchemaError(f"missing lexicon fields: {', '.join(missing)}")
        if extra:
            raise SchemaError(f"unknown lexicon fields: {', '.join(extra)}")

        term = _string(record["term"], "term")
        match_mode = _string(record["match_mode"], "match_mode")
        if match_mode not in MATCH_MODES:
            allowed = ", ".join(sorted(MATCH_MODES))
            raise SchemaError(f"match_mode {match_mode!r} is not one of: {allowed}")
        include_patterns = tuple(_string_list(record["include_patterns"], "include_patterns"))
        exclude_patterns = tuple(_string_list(record["exclude_patterns"], "exclude_patterns"))
        target_cell = _string(record["target_cell"], "target_cell")
        case_policy = _string(record["case_policy"], "case_policy")
        if case_policy not in CASE_POLICIES:
            allowed = ", ".join(sorted(CASE_POLICIES))
            raise SchemaError(f"case_policy {case_policy!r} is not one of: {allowed}")
        test_fixture_ids = tuple(_string_list(record["test_fixture_ids"], "test_fixture_ids"))
        if match_mode.startswith("context_") and not include_patterns:
            raise SchemaError(f"{term!r}: {match_mode} requires include_patterns")
        if match_mode == "context_2_of" and len(include_patterns) < 2:
            raise SchemaError(f"{term!r}: context_2_of requires at least two include_patterns")
        return cls(
            term=term,
            match_mode=match_mode,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            target_cell=target_cell,
            case_policy=case_policy,
            test_fixture_ids=test_fixture_ids,
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the exact seven-field interchange representation."""

        return {
            "term": self.term,
            "match_mode": self.match_mode,
            "include_patterns": list(self.include_patterns),
            "exclude_patterns": list(self.exclude_patterns),
            "target_cell": self.target_cell,
            "case_policy": self.case_policy,
            "test_fixture_ids": list(self.test_fixture_ids),
        }


def load_json_records(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSON array or JSONL object list using only the standard library."""

    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
        value = json.loads(text)
    except json.JSONDecodeError:
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SchemaError(f"{source}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(item, dict):
                raise SchemaError(f"{source}:{line_number}: JSONL record must be an object")
            records.append(item)
        return records
    if not isinstance(value, list):
        raise SchemaError(f"{source}: top-level JSON value must be an array or JSONL")
    if not all(isinstance(item, dict) for item in value):
        raise SchemaError(f"{source}: every record must be an object")
    return value


def load_lexicon(path: str | Path) -> list[LexiconEntry]:
    """Load candidate entries; compilation and namespace checks are separate gates."""

    entries = [LexiconEntry.from_mapping(record) for record in load_json_records(path)]
    return entries


def entries_to_json(entries: Iterable[LexiconEntry]) -> str:
    return json.dumps([entry.as_dict() for entry in entries], ensure_ascii=False, indent=2) + "\n"
