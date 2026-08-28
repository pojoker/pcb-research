"""Independent DP7 acceptance checks.  Does not read canonical project data."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from dp7_casebook.validation import validate_document

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def rejected(document, code):
    report = validate_document(document)
    assert not report["valid"], report
    assert any(error["code"] == code for error in report["errors"]), report


def mutate(document, name):
    if name == "missing_trap":
        document["cases"][0]["trap_checks"].pop("fx")
    elif name == "extra_trap":
        document["cases"][0]["trap_checks"]["extra"] = {"status": "checked", "explanation": "x", "evidence_anchor": "SRC-1"}
    elif name == "bad_anchor_type":
        document["cases"][0]["evidence_chain"][0]["anchor_type"] = "bad"
    elif name == "bad_anchor_locator":
        document["cases"][0]["evidence_chain"][0]["anchor_locator"] = "not-a-url"
    elif name == "c_load_bearing":
        document["references"][2]["usage"] = "load_bearing"
    elif name == "d_background":
        document["references"][3]["usage"] = "background"
    elif name == "d_load_bearing":
        document["references"][3]["usage"] = "load_bearing"
    elif name == "dangling_reference":
        document["references"].append({**document["references"][0], "reference_id": "REF-A-2", "case_id": "MISSING"})
    elif name == "a_one_group":
        document["cases"][0]["evidence_chain"][1]["independence_group"] = "issuer"
    elif name == "empty_overturn":
        document["cases"][2]["overturn_conditions"] = ""
    elif name == "unknown_field":
        document["unknown"] = True
    elif name == "duplicate_case":
        document["cases"].append(copy.deepcopy(document["cases"][0]))
    elif name == "duplicate_reference":
        document["references"].append(copy.deepcopy(document["references"][0]))
    elif name == "unknown_grade":
        document["cases"][0]["grade"] = "Z"
    elif name == "bad_date":
        document["cases"][0]["adjudication_date"] = "2026-99-99"
    else:
        raise AssertionError(f"unknown fixture mutation: {name}")


def main():
    checks = 0
    empty = validate_document(load("empty_casebook.json"))
    assert empty["valid"] and empty["case_count"] == 0 and empty["reference_count"] == 0
    checks += 1
    valid = load("templates.json")
    assert validate_document(valid)["valid"]
    assert {case["grade"] for case in valid["cases"]} == {"A", "B", "C", "D"}
    checks += 2

    for case in load("cases.json")["cases"]:
        document = copy.deepcopy(valid)
        mutate(document, case["mutation"])
        rejected(document, case["expected"])
        checks += 1
    print(f"DP7 selftest: PASS ({checks} checks)")


if __name__ == "__main__":
    main()
