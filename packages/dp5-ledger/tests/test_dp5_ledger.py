from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from dp5_ledger.schema import load_active_cells
from dp5_ledger.validation import validate_ledger


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
FIXTURES = PACKAGE_ROOT / "fixtures"


def read_json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _parent(payload, path: str):
    parts = path.split(".")
    current = payload
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current, parts[-1]


def apply_mutations(base, mutations):
    result = copy.deepcopy(base)
    for mutation in mutations:
        parent, final = _parent(result, mutation["path"])
        if mutation["op"] == "set":
            if isinstance(parent, list):
                parent[int(final)] = mutation["value"]
            else:
                parent[final] = mutation["value"]
        elif mutation["op"] == "delete":
            if isinstance(parent, list):
                del parent[int(final)]
            else:
                del parent[final]
        elif mutation["op"] == "append":
            target = parent[int(final)] if isinstance(parent, list) else parent[final]
            target.append(mutation["value"])
        else:
            raise AssertionError(f"unknown fixture mutation: {mutation['op']}")
    return result


class DP5LedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells = load_active_cells(REPO_ROOT / "tree.yaml")
        cls.base = read_json("valid_ledger.json")

    def test_valid_ledger_passes(self):
        report = validate_ledger(self.base, self.cells)
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(dict(report.details)["metric_count"], 8)

    def test_partial_subject_mapping_requires_and_accepts_an_explicit_reason(self):
        payload = copy.deepcopy(self.base)
        payload["subject_mappings"][0]["plant_id"] = ""
        payload["subject_mappings"][0]["missing_id_reason"] = "plant mapping is not established"
        report = validate_ledger(payload, self.cells)
        self.assertTrue(report.ok, report.errors)

    def test_mixed_business_accepts_a_real_split_anchor(self):
        payload = copy.deepcopy(self.base)
        payload["metrics"][0]["mixed_business"] = True
        payload["metrics"][0]["split_evidence_id"] = "anchor_split_scope"
        report = validate_ledger(payload, self.cells)
        self.assertTrue(report.ok, report.errors)

    def test_four_record_type_negative_fixtures_fail_closed(self):
        for fixture_name in ("negative_points.json", "negative_metrics.json", "negative_edges.json", "negative_pairs.json"):
            for case in read_json(fixture_name):
                with self.subTest(fixture_id=case["fixture_id"]):
                    report = validate_ledger(apply_mutations(self.base, case["mutations"]), self.cells)
                    self.assertFalse(report.ok)
                    self.assertTrue(any(case["expected_error"] in error for error in report.errors), report.errors)

    def test_rejects_nan_inf_and_duplicate_metric_ids(self):
        for nonfinite in (float("nan"), float("inf")):
            payload = copy.deepcopy(self.base)
            payload["metrics"][0]["value"] = nonfinite
            report = validate_ledger(payload, self.cells)
            self.assertFalse(report.ok)
            self.assertTrue(any("finite" in error for error in report.errors), report.errors)
        duplicate = copy.deepcopy(self.base)
        duplicate["metrics"].append(copy.deepcopy(duplicate["metrics"][0]))
        duplicate_report = validate_ledger(duplicate, self.cells)
        self.assertFalse(duplicate_report.ok)
        self.assertTrue(any("duplicate metric_id" in error for error in duplicate_report.errors), duplicate_report.errors)


if __name__ == "__main__":
    unittest.main()
