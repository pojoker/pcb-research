"""Golden fixture loading and deterministic candidate checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .errors import FixtureError
from .schema import load_json_records
from .validation import CompiledEntry


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    kind: str
    text: str
    expected_matches: tuple[str, ...]
    notes: str = ""

    @classmethod
    def from_mapping(cls, record: Mapping[str, Any]) -> "Fixture":
        required = {"fixture_id", "kind", "text", "expected_matches"}
        missing = required.difference(record)
        if missing:
            raise FixtureError(f"fixture missing fields: {', '.join(sorted(missing))}")
        fixture_id = record["fixture_id"]
        kind = record["kind"]
        text = record["text"]
        expected = record["expected_matches"]
        if not all(isinstance(value, str) and value.strip() for value in (fixture_id, kind, text)):
            raise FixtureError("fixture_id, kind and text must be non-empty strings")
        if kind not in {"positive", "negative", "boundary"}:
            raise FixtureError(f"{fixture_id!r}: invalid fixture kind {kind!r}")
        if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
            raise FixtureError(f"{fixture_id!r}: expected_matches must be a list of strings")
        return cls(fixture_id, kind, text, tuple(expected), str(record.get("notes", "")))


@dataclass(frozen=True)
class GoldenResult:
    fixture_id: str
    kind: str
    expected: tuple[str, ...]
    actual: tuple[str, ...]
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "fixture_id": self.fixture_id,
            "kind": self.kind,
            "expected_matches": list(self.expected),
            "actual_matches": list(self.actual),
            "passed": self.passed,
        }


def load_fixtures(path: str) -> list[Fixture]:
    return [Fixture.from_mapping(record) for record in load_json_records(path)]


def run_golden_fixtures(
    entries: Iterable[CompiledEntry], fixtures: Iterable[Fixture]
) -> tuple[GoldenResult, ...]:
    compiled = tuple(entries)
    by_term = {item.entry.term: item for item in compiled}
    results: list[GoldenResult] = []
    for fixture in fixtures:
        actual = tuple(
            term for term, entry in by_term.items() if entry.matches(fixture.text)
        )
        expected = tuple(fixture.expected_matches)
        unknown_expected = sorted(set(expected).difference(by_term))
        if unknown_expected:
            raise FixtureError(
                f"{fixture.fixture_id!r}: expected unknown candidate terms: "
                f"{', '.join(unknown_expected)}"
            )
        results.append(
            GoldenResult(
                fixture_id=fixture.fixture_id,
                kind=fixture.kind,
                expected=expected,
                actual=actual,
                passed=set(actual) == set(expected),
            )
        )
    return tuple(results)
