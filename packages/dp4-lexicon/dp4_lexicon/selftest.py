"""No-dependency selftest for the DP4 package and its high-risk fixtures."""

from __future__ import annotations

from pathlib import Path

from .corpus import CorpusDocument, CorpusScanner
from .errors import BareAbbreviationError, CellIdCollisionError, RegexCompilationError, SchemaError
from .fixtures import load_fixtures, run_golden_fixtures
from .schema import LexiconEntry, load_lexicon
from .validation import compile_entry, compile_gate, validate_cell_id


ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "data" / "candidate_lexicon.json"
FIXTURES = ROOT / "fixtures" / "golden.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(*, verbose: bool = True) -> int:
    entries = load_lexicon(LEXICON)
    fixtures = load_fixtures(str(FIXTURES))
    fixture_index = {fixture.fixture_id: fixture for fixture in fixtures}
    compiled = compile_gate(entries)
    _assert(all(entry.exclude_patterns for entry in entries), "every candidate needs an exclusion regex")
    results = run_golden_fixtures(compiled, fixtures)
    failures = [result for result in results if not result.passed]
    _assert(not failures, f"golden fixture failures: {[item.as_dict() for item in failures]}")
    _assert(
        all(
            fixture_id in fixture_index
            for entry in entries
            for fixture_id in entry.test_fixture_ids
        ),
        "fixture index mismatch",
    )

    # Explicit negative checks required by the handoff: SAP/HDI/BT/PCB collision samples.
    negative_ids = {"sap-software", "hdi-isocyanate", "bt-bluetooth", "pcb-pollution"}
    negative_results = [result for result in results if result.fixture_id in negative_ids]
    _assert(len(negative_results) == len(negative_ids), "required negative sample is missing")
    _assert(all(not result.actual for result in negative_results), "a required negative sample matched")

    collision_text = "PCB裸板与HDI板均在该厂制造，采用微盲孔与任意层互连。"
    scan = CorpusScanner(compiled).scan(
        [CorpusDocument("collision-1", collision_text), CorpusDocument("none-1", "普通新闻")],
        scope="selftest",
        date="2026-08-26",
    )
    _assert(len(scan.collision_documents) == 1, "collision report did not find the collision document")
    _assert(scan.measurements[0].as_dict().keys() == {"keyword", "scope", "date", "hit_count"}, "measurement is not four-key")

    # Fail-closed mechanical gates.
    try:
        compile_entry(
            LexiconEntry(
                "SAP", "literal", (), (), "P5", "sensitive", ("sap-software",)
            )
        )
    except BareAbbreviationError:
        pass
    else:
        raise AssertionError("bare SAP was accepted")
    try:
        compile_entry(
            LexiconEntry(
                "M6", "literal", (), (), "AXIS_D", "sensitive", ("pcb-pollution",)
            )
        )
    except CellIdCollisionError:
        pass
    else:
        raise AssertionError("reserved M6 was accepted")
    validate_cell_id("M4")
    for inactive in ("M6", "M8"):
        try:
            validate_cell_id(inactive)
        except SchemaError:
            pass
        else:
            raise AssertionError(f"inactive target {inactive} was accepted")
    try:
        compile_entry(
            LexiconEntry(
                "坏正则", "literal", (), ("[",), "M1", "sensitive", ("ccl-positive",)
            )
        )
    except RegexCompilationError:
        pass
    else:
        raise AssertionError("invalid regex was accepted")

    if verbose:
        print(f"DP4 selftest: PASS ({len(entries)} entries, {len(results)} golden fixtures)")
    return 0
