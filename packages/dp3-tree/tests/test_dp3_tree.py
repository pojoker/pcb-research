from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from dp3_tree.rendering import render_coverage
from dp3_tree.schema import ACTIVE_CELL_IDS, RESERVED_INACTIVE_CELL_IDS, load_tree, parse_tree
from dp3_tree.validation import (
    PRODUCT_FAMILY_TO_TARGET,
    validate_process_equipment_map,
    validate_samples,
    validate_target_cell,
    validate_tree,
)
from dp3_tree.errors import SchemaError


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
TREE_PATH = REPO_ROOT / "tree.yaml"


def read_json(name: str):
    return json.loads((PACKAGE_ROOT / "fixtures" / name).read_text(encoding="utf-8"))


class DP3TreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = load_tree(TREE_PATH)

    def test_canonical_tree_is_frozen_and_exactly_30_active_cells(self):
        report = validate_tree(self.tree)
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(len(self.tree.cells), 30)
        self.assertEqual(set(self.tree.cell_ids), set(ACTIVE_CELL_IDS))
        self.assertEqual(len(self.tree.cell_ids), 30)
        self.assertIn("M4", self.tree.cell_ids)
        self.assertTrue(RESERVED_INACTIVE_CELL_IDS.isdisjoint(self.tree.cell_ids))

    def test_tree_schema_is_exact_and_status_gate_is_mechanical(self):
        raw = json.loads(TREE_PATH.read_text(encoding="utf-8"))
        del raw["status"]
        with self.assertRaisesRegex(SchemaError, "missing tree fields: status"):
            parse_tree(raw)
        self.assertFalse(validate_tree(replace(self.tree, status="draft")).ok)

    def test_axes_are_a_to_f_non_empty_and_route_values_are_not_cells(self):
        self.assertEqual(tuple(axis.axis_id for axis in self.tree.route_axes), tuple("ABCDEF"))
        self.assertTrue(all(axis.values for axis in self.tree.route_axes))
        self.assertTrue(
            all(value not in self.tree.cell_ids for axis in self.tree.route_axes for value in axis.values)
        )

    def test_m4_is_valid_target_but_m6_m8_and_out_are_not(self):
        validate_target_cell("M4", self.tree)
        for invalid in ("M6", "M8", "OUT"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(SchemaError):
                    validate_target_cell(invalid, self.tree)

    def test_required_outside_neighbors_are_explicit(self):
        self.assertEqual(
            set(self.tree.outside_neighbors),
            {"PCBA", "SMT", "EMS", "设计", "锂电铜箔", "整机"},
        )
        self.assertNotIn("OUT", self.tree.cell_ids)

    def test_valid_and_negative_sample_fixtures(self):
        valid = validate_samples(read_json("valid_samples.json"), self.tree)
        self.assertTrue(valid.ok, valid.errors)
        for case in read_json("negative_samples.json"):
            with self.subTest(fixture_id=case["fixture_id"]):
                report = validate_samples(case["records"], self.tree)
                self.assertFalse(report.ok)
                self.assertTrue(any(case["expected_error"] in error for error in report.errors), report.errors)

    def test_product_family_compatibility_matrix(self):
        for family in ("普通刚性", "HDI", "FPC", "刚挠", "金属基", "高频", "背板"):
            self.assertEqual(PRODUCT_FAMILY_TO_TARGET[family], "FAB1")
        self.assertEqual(PRODUCT_FAMILY_TO_TARGET["IC 载板"], "FAB2")
        for family in ("PCBA", "SMT", "EMS", "设计", "锂电铜箔", "整机"):
            self.assertEqual(PRODUCT_FAMILY_TO_TARGET[family], "OUT")

    def test_process_equipment_map_is_explicit_many_to_many_and_does_not_default(self):
        self.assertEqual(set(self.tree.process_ids), {f"P{index}" for index in range(1, 10)})
        self.assertNotIn("PM1", self.tree.process_ids)
        report = validate_process_equipment_map(read_json("valid_process_equipment_map.json"), self.tree)
        self.assertTrue(report.ok, report.errors)
        details = dict(report.details)
        self.assertIn(("P1", "EQ1"), details["mappings"])
        self.assertIn("P7", details["unmapped_processes"])
        self.assertNotIn(("P7", "EQ6"), details["mappings"])
        self.assertNotIn(("P7", "EQ7"), details["mappings"])
        for case in read_json("negative_process_equipment_map.json"):
            with self.subTest(fixture_id=case["fixture_id"]):
                negative = validate_process_equipment_map(case["records"], self.tree)
                self.assertFalse(negative.ok)
                self.assertTrue(any(case["expected_error"] in error for error in negative.errors), negative.errors)

    def test_renderer_emits_all_30_cells_and_explicit_spaces(self):
        payload = read_json("valid_render_input.json")
        report, rows = render_coverage(self.tree, payload["attachments"], payload["coverage"])
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(len(rows), 30)
        self.assertEqual({row["cell_id"] for row in rows}, set(ACTIVE_CELL_IDS))
        by_id = {row["cell_id"]: row for row in rows}
        self.assertEqual(by_id["FAB1"]["coverage_status"], "covered")
        self.assertTrue(by_id["FAB2"]["empty_space"])
        self.assertEqual(by_id["FAB2"]["space"], "空格")
        self.assertFalse(by_id["M4"]["empty_space"])

    def test_renderer_rejects_out_and_reserved_cells(self):
        payload = read_json("negative_render_input.json")
        report, rows = render_coverage(self.tree, payload["attachments"], payload["coverage"])
        self.assertFalse(report.ok)
        self.assertEqual(len(rows), 30)
        self.assertTrue(any("OUT" in error for error in report.errors))
        self.assertTrue(any("M6" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
