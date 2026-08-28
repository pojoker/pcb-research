from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dp6_publish_gate.rendering import render_json, render_text
from dp6_publish_gate.validation import validate_document


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def load_json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def set_path(obj: dict, path: str, value) -> None:
    parts = path.split(".")
    target = obj
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value


def quant_case(case: dict, adr: dict | None = None):
    document = copy.deepcopy(load_json("valid_pass.json"))
    row = document["rows"][0]
    for path, value in case.get("patch", {}).items():
        set_path(row, path, value)
    if case.get("special_value") == "NaN":
        row["value"] = float("nan")
    if case.get("special_value") == "Infinity":
        row["value"] = float("inf")
    effective_adr = copy.deepcopy(adr or load_json("approved_tolerance.json"))
    if "adr_status" in case:
        effective_adr["status"] = case["adr_status"]
    return document, effective_adr


def customs_row(case: dict) -> dict:
    metadata = {
        "tariff_year": "2026", "full_subheading": "8534.00", "direction": "export",
        "quantity_unit": "kg", "product_scope": "printed circuits", "trade_mode": "general",
        "declarant": "macro-declarant", "origin": "CN", "attribution_method": "region",
        "period": "2026Q2", "coverage_gap": "none", "conversion_anchor": "fixture://macro-anchor",
    }
    case_status = case["status"]
    for key in case.get("metadata_remove", []):
        metadata.pop(key, None)
    return {
        "id": "C-" + case["name"], "kind": "customs_calibration", "customs_code": "8534",
        "calibration_scope": "macro_only", "applicability_status": case_status,
        "use_level": case.get("use_level", "region_industry"), "target_metric": "exported_quantity",
        "target_product_family": "普通刚性", "target_geography": "China customs",
        "metadata": metadata, "conversion_method": case.get("conversion_method", "macro_anchor"),
        "domestic_sales_evidence": case.get("domestic_sales_evidence", "fixture://domestic-sales"),
        "recalibration": {"actual_value": None, "actual_unit": None, "actual_period": None, "error": None, "error_formula": None, "date": None},
    }


class DP6PublishGateTests(unittest.TestCase):
    def test_valid_pass_is_publishable(self):
        report = validate_document(load_json("valid_pass.json"), load_json("approved_tolerance.json"))
        self.assertEqual(report["overall_status"], "pass")
        self.assertTrue(report["rows"][0]["publishable"])

    def test_declared_quant_cases(self):
        manifest = load_json("cases.json")
        for case in manifest["cases"]:
            with self.subTest(case=case["name"]):
                document, adr = quant_case(case)
                report = validate_document(document, adr)
                self.assertEqual(report["rows"][0]["status"], case["expected"])
                self.assertEqual(report["rows"][0]["publishable"], case["expected"] == "pass")

    def test_declared_customs_cases(self):
        manifest = load_json("customs_cases.json")
        for case in manifest["cases"]:
            with self.subTest(case=case["name"]):
                report = validate_document({"schema_version": "dp6.publish-gate.input.v1", "rows": [customs_row(case)]})
                self.assertEqual(report["rows"][0]["status"], case["expected"])

    def test_valid_macro_8534_passes(self):
        case = {"name": "customs_macro_pass", "status": "applicable_macro"}
        report = validate_document({"schema_version": "dp6.publish-gate.input.v1", "rows": [customs_row(case)]})
        self.assertEqual(report["rows"][0]["status"], "pass")
        self.assertEqual(report["overall_status"], "pass")
        self.assertTrue(report["publishable"])

    def test_missing_tolerance_keeps_quantitative_rows_indeterminate(self):
        document = load_json("valid_pass.json")
        document["rows"][0]["value"] = 1201
        report = validate_document(document, None)
        self.assertEqual(report["rows"][0]["status"], "indeterminate")
        self.assertEqual(report["overall_status"], "indeterminate")
        self.assertFalse(report["publishable"])

    def test_duplicate_and_unknown_columns_are_hard_failures(self):
        document = load_json("valid_pass.json")
        document["rows"].append(copy.deepcopy(document["rows"][0]))
        report = validate_document(document, load_json("approved_tolerance.json"))
        self.assertEqual(report["counts"]["fail"], 2)
        document = load_json("valid_pass.json")
        document["rows"][0]["unexpected"] = True
        report = validate_document(document, load_json("approved_tolerance.json"))
        self.assertEqual(report["rows"][0]["status"], "fail")

    def test_aggregation_priority_is_fail_then_indeterminate_then_pass(self):
        pass_row = copy.deepcopy(load_json("valid_pass.json")["rows"][0])
        indeterminate_row = copy.deepcopy(pass_row)
        indeterminate_row["id"] = "Q-INDET"
        indeterminate_row["comparison"]["subject_id"] = "S2"
        fail_row = copy.deepcopy(pass_row)
        fail_row["id"] = "Q-FAIL"
        fail_row["value"] = 1201
        report = validate_document({"schema_version": "dp6.publish-gate.input.v1", "rows": [pass_row, indeterminate_row, fail_row]}, load_json("approved_tolerance.json"))
        self.assertEqual(report["overall_status"], "fail")
        self.assertFalse(report["publishable"])

    def test_renderer_never_upgrades_indeterminate(self):
        document, adr = quant_case({"name": "render", "expected": "indeterminate", "adr_status": "unapproved"})
        report = validate_document(document, adr)
        text = render_text(report)
        self.assertIn("status=indeterminate", text)
        self.assertIn("publishable=false", text)
        self.assertNotIn("status=pass", text)
        self.assertEqual(json.loads(render_json(report))["rows"][0]["status"], "indeterminate")
        forged = copy.deepcopy(report)
        forged["publishable"] = True
        forged["rows"][0]["publishable"] = True
        safe = json.loads(render_json(forged))
        self.assertFalse(safe["publishable"])
        self.assertFalse(safe["rows"][0]["publishable"])

    def test_bad_recalibration_values_fail_without_crashing(self):
        document = load_json("valid_pass.json")
        recalibration = document["rows"][0]["recalibration"]
        recalibration.update({
            "actual_value": "not-a-number",
            "actual_unit": "square_meter",
            "actual_period": "2026Q2",
            "error": 0,
            "error_formula": "actual_value - inferred_value",
            "date": "2026-08-28",
        })
        report = validate_document(document, load_json("approved_tolerance.json"))
        self.assertEqual(report["rows"][0]["status"], "fail")

    def test_cli_emits_machine_readable_report(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "report.json"
            completed = subprocess.run(
                [sys.executable, "-m", "dp6_publish_gate", "validate", "--input", str(FIXTURES / "valid_pass.json"), "--tolerance-adr", str(FIXTURES / "approved_tolerance.json"), "--output", str(output)],
                cwd=ROOT, env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}, text=True,
                capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(json.loads(output.read_text())["overall_status"], "pass")


if __name__ == "__main__":
    unittest.main()
