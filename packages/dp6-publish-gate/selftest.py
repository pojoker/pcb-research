"""Independent fixture-driven smoke test for DP6."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

from dp6_publish_gate.rendering import render_text
from dp6_publish_gate.validation import validate_document


HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def set_path(obj, path, value):
    parts = path.split(".")
    target = obj
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value


def run_quant_cases():
    checks = 0
    for case in load("cases.json")["cases"]:
        document = copy.deepcopy(load("valid_pass.json"))
        row = document["rows"][0]
        for path, value in case.get("patch", {}).items():
            set_path(row, path, value)
        if case.get("special_value") == "NaN":
            row["value"] = float("nan")
        if case.get("special_value") == "Infinity":
            row["value"] = float("inf")
        adr = copy.deepcopy(load("approved_tolerance.json"))
        if "adr_status" in case:
            adr["status"] = case["adr_status"]
        report = validate_document(document, adr)
        assert report["rows"][0]["status"] == case["expected"], case["name"]
        assert report["rows"][0]["publishable"] is (case["expected"] == "pass"), case["name"]
        checks += 1
    return checks


def macro_row(status="applicable_macro", use_level="region_industry", conversion_method="macro_anchor", metadata=None, domestic="fixture://domestic-sales"):
    all_metadata = {
        "tariff_year": "2026", "full_subheading": "8534.00", "direction": "export",
        "quantity_unit": "kg", "product_scope": "printed circuits", "trade_mode": "general",
        "declarant": "macro-declarant", "origin": "CN", "attribution_method": "region",
        "period": "2026Q2", "coverage_gap": "none", "conversion_anchor": "fixture://macro-anchor",
    }
    if metadata is not None:
        all_metadata = metadata
    return {"id": "CUSTOMS-" + status + use_level, "kind": "customs_calibration", "customs_code": "8534", "calibration_scope": "macro_only", "applicability_status": status, "use_level": use_level, "target_metric": "exported_quantity", "target_product_family": "普通刚性", "target_geography": "China customs", "metadata": all_metadata, "conversion_method": conversion_method, "domestic_sales_evidence": domestic, "recalibration": {"actual_value": None, "actual_unit": None, "actual_period": None, "error": None, "error_formula": None, "date": None}}


def main():
    checks = run_quant_cases()
    for case in load("customs_cases.json")["cases"]:
        metadata = macro_row()["metadata"]
        for key in case.get("metadata_remove", []):
            metadata.pop(key, None)
        row = macro_row(case["status"], case.get("use_level", "region_industry"), case.get("conversion_method", "macro_anchor"), metadata, case.get("domestic_sales_evidence", "fixture://domestic-sales"))
        report = validate_document({"schema_version": "dp6.publish-gate.input.v1", "rows": [row]})
        assert report["rows"][0]["status"] == case["expected"], case["name"]
        checks += 1
    valid = validate_document(load("valid_pass.json"), load("approved_tolerance.json"))
    assert valid["overall_status"] == "pass"
    assert valid["publishable"] is True
    assert math.isfinite(valid["rows"][0]["comparison_value"])
    indet = copy.deepcopy(load("approved_tolerance.json"))
    indet["status"] = "unapproved"
    indet_report = validate_document(load("valid_pass.json"), indet)
    rendered = render_text(indet_report)
    assert "status=indeterminate" in rendered and "publishable=false" in rendered
    assert "status=pass" not in rendered
    checks += 4
    print(f"DP6 selftest: PASS ({checks} checks)")


if __name__ == "__main__":
    main()
