"""The DP4 validation and regex compilation gates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

from .errors import BareAbbreviationError, CellIdCollisionError, RegexCompilationError, SchemaError
from .schema import LexiconEntry


# A target must be a currently active tree cell.  M6/M8 are reserved market
# words but are deliberately absent here; M4 remains the active resin cell.
ACTIVE_TARGET_CELL_IDS = frozenset(
    {
        "FAB1",
        "FAB2",
        "M1",
        "M2",
        "M3",
        "M4",
        "M5",
        "M7",
        "M9",
        "MSK",
        "FLX",
        "PM1",
        "PM2",
        "PM3",
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "P7",
        "P8",
        "P9",
        "EQ1",
        "EQ2",
        "EQ3",
        "EQ4",
        "EQ5",
        "EQ6",
        "EQ7",
    }
)
# Terms may not collide with active cells, inactive loss-grade words, or cell
# namespace prefixes.  Keeping this separate from ACTIVE_TARGET_CELL_IDS is
# what allows target M4 while still rejecting a bare lexical term named M4.
RESERVED_TERM_TOKENS = ACTIVE_TARGET_CELL_IDS | frozenset(
    {"M6", "M8", "M", "PM", "P", "EQ"}
)
SPECIAL_TARGET_CELLS = frozenset({"ANY", "OUTSIDE", "ROLE", "AXIS_D"})
_BARE_ABBREVIATION = re.compile(r"^[A-Za-z][A-Za-z0-9./-]*$")
# ``mSAP`` is explicitly admitted by docs/04 as a qualified process term.
# Any other all-ASCII candidate must be expanded into a phrase before it can
# enter this package; contextual regexes do not turn a bare abbreviation into
# a qualified term.
QUALIFIED_ASCII_TERMS = frozenset({"mSAP"})


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    term: str | None
    message: str

    def as_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "term": self.term, "message": self.message}


def validate_cell_id(cell_id: str) -> None:
    """Check a declared target cell without confusing it with a term collision."""

    if not isinstance(cell_id, str) or not cell_id.strip():
        raise SchemaError("target_cell must be a non-empty string")
    normalized = cell_id.strip().upper()
    if normalized not in ACTIVE_TARGET_CELL_IDS and normalized not in SPECIAL_TARGET_CELLS:
        raise SchemaError(
            f"target_cell {cell_id!r} is not a declared cell id or special target "
            f"({', '.join(sorted(SPECIAL_TARGET_CELLS))})"
        )


def _reserved_collision(term: str) -> str | None:
    normalized = term.strip().upper()
    if normalized in RESERVED_TERM_TOKENS:
        return normalized
    return None


def _check_bare_abbreviation(entry: LexiconEntry) -> None:
    if (
        _BARE_ABBREVIATION.fullmatch(entry.term)
        and entry.term not in QUALIFIED_ASCII_TERMS
    ):
        raise BareAbbreviationError(
            f"{entry.term!r}: bare abbreviations are prohibited; use a qualified phrase"
        )


def compile_pattern(pattern: str, *, case_policy: str, term: str, pattern_kind: str) -> re.Pattern[str]:
    flags = re.IGNORECASE if case_policy == "insensitive" else 0
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise RegexCompilationError(
            f"{term!r}: invalid {pattern_kind} regex {pattern!r}: {exc.msg}"
        ) from exc


@dataclass(frozen=True)
class CompiledEntry:
    entry: LexiconEntry
    base_pattern: re.Pattern[str]
    include_patterns: tuple[re.Pattern[str], ...]
    exclude_patterns: tuple[re.Pattern[str], ...]

    def match_trace(self, text: str) -> dict[str, object]:
        base_match = self.base_pattern.search(text)
        include_hits = [pattern.search(text) is not None for pattern in self.include_patterns]
        exclude_hits = [pattern.search(text) is not None for pattern in self.exclude_patterns]
        mode = self.entry.match_mode
        if mode in {"literal", "regex"}:
            include_ok = all(include_hits)
        elif mode == "context_any":
            include_ok = any(include_hits)
        elif mode == "context_all":
            include_ok = all(include_hits)
        elif mode == "context_2_of":
            include_ok = sum(include_hits) >= 2
        else:  # guarded by LexiconEntry.from_mapping
            include_ok = False
        matched = bool(base_match and include_ok and not any(exclude_hits))
        return {
            "matched": matched,
            "base_hit": base_match is not None,
            "include_hits": include_hits,
            "exclude_hits": exclude_hits,
        }

    def matches(self, text: str) -> bool:
        return bool(self.match_trace(text)["matched"])


def compile_entry(entry: LexiconEntry) -> CompiledEntry:
    collision = _reserved_collision(entry.term)
    if collision:
        raise CellIdCollisionError(
            f"{entry.term!r}: term collides with reserved cell_id {collision!r}"
        )
    _check_bare_abbreviation(entry)
    validate_cell_id(entry.target_cell)
    flags = re.IGNORECASE if entry.case_policy == "insensitive" else 0
    if entry.match_mode == "regex":
        base_pattern = compile_pattern(
            entry.term,
            case_policy=entry.case_policy,
            term=entry.term,
            pattern_kind="term",
        )
    else:
        base_pattern = re.compile(re.escape(entry.term), flags)
    includes = tuple(
        compile_pattern(
            pattern,
            case_policy=entry.case_policy,
            term=entry.term,
            pattern_kind="include",
        )
        for pattern in entry.include_patterns
    )
    excludes = tuple(
        compile_pattern(
            pattern,
            case_policy=entry.case_policy,
            term=entry.term,
            pattern_kind="exclude",
        )
        for pattern in entry.exclude_patterns
    )
    return CompiledEntry(entry, base_pattern, includes, excludes)


def compile_gate(entries: Iterable[LexiconEntry]) -> tuple[CompiledEntry, ...]:
    """Compile all entries or fail; no partial compiled vocabulary is returned."""

    return tuple(compile_entry(entry) for entry in validate_entries(entries))


def validate_entries(
    entries: Iterable[LexiconEntry], fixture_index: Mapping[str, object] | None = None
) -> tuple[LexiconEntry, ...]:
    """Apply schema-adjacent mechanical checks before the regex gate.

    The function raises on the first invalid item so an invalid regex or reserved
    word cannot be silently carried into a report.
    """

    materialized = tuple(entries)
    seen: set[str] = set()
    for entry in materialized:
        if entry.term in seen:
            raise SchemaError(f"duplicate term: {entry.term!r}")
        seen.add(entry.term)
        collision = _reserved_collision(entry.term)
        if collision:
            raise CellIdCollisionError(
                f"{entry.term!r}: term collides with reserved cell_id {collision!r}"
            )
        _check_bare_abbreviation(entry)
        validate_cell_id(entry.target_cell)
        # Compile all patterns here so the gate fails before any corpus work.
        if entry.match_mode == "regex":
            compile_pattern(entry.term, case_policy=entry.case_policy, term=entry.term, pattern_kind="term")
        for pattern in entry.include_patterns:
            compile_pattern(pattern, case_policy=entry.case_policy, term=entry.term, pattern_kind="include")
        for pattern in entry.exclude_patterns:
            compile_pattern(pattern, case_policy=entry.case_policy, term=entry.term, pattern_kind="exclude")
        if fixture_index is not None:
            missing = [fixture_id for fixture_id in entry.test_fixture_ids if fixture_id not in fixture_index]
            if missing:
                raise SchemaError(
                    f"{entry.term!r}: unknown test_fixture_ids: {', '.join(missing)}"
                )
    return materialized
