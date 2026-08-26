from __future__ import annotations

import unittest
from pathlib import Path

from dp4_lexicon.corpus import CorpusDocument, CorpusScanner
from dp4_lexicon.errors import BareAbbreviationError, CellIdCollisionError, RegexCompilationError
from dp4_lexicon.fixtures import load_fixtures, run_golden_fixtures
from dp4_lexicon.schema import LexiconEntry, load_lexicon
from dp4_lexicon.validation import compile_entry, compile_gate


ROOT = Path(__file__).resolve().parents[1]


class DP4LexiconTest(unittest.TestCase):
    def test_schema_and_golden_fixtures(self):
        entries = load_lexicon(ROOT / "data/candidate_lexicon.json")
        fixtures = load_fixtures(str(ROOT / "fixtures/golden.json"))
        compiled = compile_gate(entries)
        results = run_golden_fixtures(compiled, fixtures)
        self.assertTrue(all(result.passed for result in results), [result.as_dict() for result in results if not result.passed])
        self.assertEqual(set(entries[0].as_dict()), {"term", "match_mode", "include_patterns", "exclude_patterns", "target_cell", "case_policy", "test_fixture_ids"})

    def test_required_negative_samples_are_empty(self):
        entries = compile_gate(load_lexicon(ROOT / "data/candidate_lexicon.json"))
        fixtures = load_fixtures(str(ROOT / "fixtures/golden.json"))
        negative_ids = {"sap-software", "hdi-isocyanate", "bt-bluetooth", "pcb-pollution"}
        results = {result.fixture_id: result for result in run_golden_fixtures(entries, fixtures)}
        self.assertEqual({fixture_id: results[fixture_id].actual for fixture_id in negative_ids}, {fixture_id: () for fixture_id in negative_ids})

    def test_regex_gate_bare_abbreviation_and_reserved_cell_gate(self):
        with self.assertRaises(BareAbbreviationError):
            compile_entry(LexiconEntry("SAP", "literal", (), (), "P5", "sensitive", ("x",)))
        with self.assertRaises(BareAbbreviationError):
            compile_entry(
                LexiconEntry(
                    "SAP", "context_any", ("制程",), ("软件",), "P5", "sensitive", ("x",)
                )
            )
        with self.assertRaises(CellIdCollisionError):
            compile_entry(LexiconEntry("M6", "literal", (), (), "AXIS_D", "sensitive", ("x",)))
        with self.assertRaises(RegexCompilationError):
            compile_entry(LexiconEntry("坏正则", "literal", (), ("[",), "M1", "sensitive", ("x",)))

    def test_four_key_measurement_and_collision_report(self):
        compiled = compile_gate(load_lexicon(ROOT / "data/candidate_lexicon.json"))
        scan = CorpusScanner(compiled).scan(
            [CorpusDocument("one", "PCB裸板和HDI板采用微盲孔与任意层。")],
            scope="unit-test",
            date="2026-08-26",
        )
        self.assertEqual(set(scan.measurements[0].as_dict()), {"keyword", "scope", "date", "hit_count"})
        self.assertEqual(scan.collision_report()["status"], "pending_review")
        self.assertEqual(scan.collision_report()["collision_statistics"]["documents_with_collisions"], 1)
