from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from dp7_casebook.validation import validate_document


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class DP7CasebookTests(unittest.TestCase):
    def test_empty_casebook_is_valid(self):
        self.assertTrue(validate_document(load("empty_casebook.json"))["valid"])

    def test_a_b_c_d_templates_are_valid(self):
        report = validate_document(load("templates.json"))
        self.assertTrue(report["valid"], report["errors"])

    def test_exactly_thirteen_traps_required(self):
        document = load("templates.json")
        document["cases"][0]["trap_checks"].pop("fx")
        codes = {e["code"] for e in validate_document(document)["errors"]}
        self.assertIn("trap_missing", codes)
        document = load("templates.json")
        document["cases"][0]["trap_checks"]["unexpected"] = {"status": "checked", "explanation": "x", "evidence_anchor": "SRC-1"}
        self.assertIn("trap_unknown", {e["code"] for e in validate_document(document)["errors"]})

    def test_anchor_rules(self):
        document = load("templates.json")
        evidence = document["cases"][0]["evidence_chain"][0]
        evidence["anchor_type"] = "url"
        evidence["anchor_locator"] = "not-a-url"
        self.assertIn("anchor_locator_invalid", {e["code"] for e in validate_document(document)["errors"]})

    def test_grade_a_requires_two_independent_hard_origins(self):
        document = load("templates.json")
        document["cases"][0]["evidence_chain"][1]["evidence_strength"] = "supporting"
        self.assertIn("grade_a_independence", {e["code"] for e in validate_document(document)["errors"]})
        document = load("templates.json")
        document["cases"][0]["evidence_chain"][1]["origin_source_id"] = "SRC-1"
        codes = {e["code"] for e in validate_document(document)["errors"]}
        self.assertTrue({"grade_a_independence", "independence_group_conflict"} <= codes)

    def test_trap_anchor_must_reference_case_evidence(self):
        document = load("templates.json")
        document["cases"][0]["trap_checks"]["fx"]["evidence_anchor"] = "SRC-MISSING"
        self.assertIn("trap_anchor_dangling", {e["code"] for e in validate_document(document)["errors"]})

    def test_grade_reference_rules(self):
        document = load("templates.json")
        document["references"][2]["usage"] = "load_bearing"
        document["references"][3]["usage"] = "background"
        codes = {e["code"] for e in validate_document(document)["errors"]}
        self.assertTrue({"grade_c_load_bearing", "grade_d_usage"} <= codes)

    def test_reference_consumer_must_match_a_declared_slot(self):
        document = load("templates.json")
        document["references"][0]["consumer_id"] = "EDGE-OTHER"
        self.assertIn("reference_slot_mismatch", {e["code"] for e in validate_document(document)["errors"]})

    def test_duplicate_and_unknown_are_rejected(self):
        document = load("templates.json")
        document["cases"].append(copy.deepcopy(document["cases"][0]))
        document["references"].append(copy.deepcopy(document["references"][0]))
        document["unexpected"] = 1
        codes = {e["code"] for e in validate_document(document)["errors"]}
        self.assertTrue({"duplicate_case_id", "duplicate_reference_id", "unknown_field"} <= codes)

    def test_invalid_date_and_grade_are_rejected(self):
        document = load("templates.json")
        document["cases"][0]["grade"] = "Z"
        document["cases"][1]["adjudication_date"] = "not-a-date"
        codes = {e["code"] for e in validate_document(document)["errors"]}
        self.assertTrue({"grade_invalid", "date_invalid"} <= codes)


if __name__ == "__main__":
    unittest.main()
