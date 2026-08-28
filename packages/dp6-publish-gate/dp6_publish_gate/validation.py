"""DP6 mechanical validation and three-state decision logic."""

from __future__ import annotations

import math
from typing import Any

from .schema import (
    CUSTOMS_KIND,
    CUSTOMS_METADATA_KEYS,
    QUANT_KIND,
    adr_scope_matches,
    date_in_effective_range,
    validate_adr,
    validate_row_structure,
)


def _decision(row_id: str, status: str, reasons: list[str], **details: Any) -> dict[str, Any]:
    if status not in {"pass", "fail", "indeterminate"}:
        raise AssertionError(status)
    result = {
        "id": row_id,
        "status": status,
        "publishable": status == "pass",
        "reason_codes": list(dict.fromkeys(reasons)),
        "comparison_value": details.pop("comparison_value", None),
        "comparison_basis": details.pop("comparison_basis", None),
        "tolerance": details.pop("tolerance", None),
        "tolerance_anchor": details.pop("tolerance_anchor", None),
        "incomparability_reason": details.pop("incomparability_reason", None),
        "decision_date": details.pop("decision_date", None),
    }
    result.update(details)
    return result


def _hard_or_indeterminate(structure_errors: list[str]) -> tuple[str, list[str]]:
    # The contract explicitly treats missing/unknown columns, duplicate IDs and
    # non-finite numbers as hard failures. Domain incomparability is different.
    return "fail", [f"DP6_SCHEMA_{error.upper().replace(':', '_')}" for error in structure_errors]


def _validate_quant(row: dict[str, Any], adr: dict[str, Any] | None, adr_errors: list[str]) -> dict[str, Any]:
    row_id = str(row.get("id", "<missing-id>"))
    structural = validate_row_structure(row)
    if structural:
        return _decision(row_id, *_hard_or_indeterminate(structural))

    reasons: list[str] = []
    comparison = row["comparison"]
    details: dict[str, Any] = {
        "comparison_value": row["value"],
        "comparison_basis": {
            "unit": comparison["upper_bound_unit"],
            "period": comparison["upper_bound_period"],
            "period_type": comparison["upper_bound_period_type"],
            "currency": comparison["upper_bound_currency"],
            "consolidation_basis": comparison["upper_bound_consolidation_basis"],
        },
        "tolerance": None,
        "tolerance_anchor": None,
    }
    identity_pairs = (
        ("subject_id", comparison["subject_id"]),
        ("plant_id", comparison["plant_id"]),
        ("product_family", comparison["product_family"]),
        ("fab_cell", comparison["fab_cell"]),
        ("period", comparison["upper_bound_period"]),
        ("period_type", comparison["upper_bound_period_type"]),
        ("metric_type", comparison["metric_type"]),
        ("unit", comparison["upper_bound_unit"]),
        ("currency", comparison["upper_bound_currency"]),
        ("consolidation_basis", comparison["upper_bound_consolidation_basis"]),
    )
    mismatches = [field for field, expected in identity_pairs if row[field] != expected]
    if mismatches:
        return _decision(
            row_id,
            "indeterminate",
            ["DP6_INCOMPARABLE_SCOPE"],
            **details,
            incomparability_reason=";".join(mismatches),
        )

    ceiling = row["capacity_ceiling"]
    if (
        ceiling["value"] != comparison["upper_bound_value"]
        or ceiling["unit"] != comparison["upper_bound_unit"]
        or ceiling["period_type"] != comparison["upper_bound_period_type"]
    ):
        return _decision(row_id, "fail", ["DP6_CEILING_COMPARISON_MISMATCH"], **details)
    if ceiling["anchor_type"] in {"production_sales_table", "built_capacity_self_disclosure"}:
        if not ceiling["human_verified"]:
            reasons.append("DP6_CAPACITY_ANCHOR_NOT_HUMAN_VERIFIED")
    elif ceiling["anchor_type"] == "approval_capacity":
        reasons.append("DP6_WEAK_APPROVAL_CEILING")

    if adr_errors or adr is None:
        reasons.append("DP6_TOLERANCE_NOT_APPROVED_OR_MISSING")
    else:
        if adr["status"] != "approved":
            reasons.append("DP6_TOLERANCE_NOT_APPROVED")
        elif not adr_scope_matches(adr, row, comparison):
            reasons.append("DP6_TOLERANCE_SCOPE_MISMATCH")
        elif not date_in_effective_range(adr, row["retrieval_date"]):
            reasons.append("DP6_TOLERANCE_OUT_OF_EFFECTIVE_RANGE")
        else:
            details["tolerance"] = adr["tolerance"]
            details["tolerance_anchor"] = adr["evidence_anchor"]
            details["decision_date"] = adr["decision_date"]

    if reasons:
        return _decision(row_id, "indeterminate", reasons, **details)
    limit = comparison["upper_bound_value"] * (1 + details["tolerance"])
    if row["value"] > limit:
        return _decision(row_id, "fail", ["DP6_OVER_COMPARABLE_CEILING"], **details)
    return _decision(row_id, "pass", [], **details)


def _validate_customs(row: dict[str, Any]) -> dict[str, Any]:
    row_id = str(row.get("id", "<missing-id>"))
    structural = validate_row_structure(row)
    if structural:
        return _decision(row_id, *_hard_or_indeterminate(structural))
    if row["use_level"] in {"company", "plant"}:
        return _decision(row_id, "fail", ["DP6_CUSTOMS_8534_COMPANY_OR_PLANT_FORBIDDEN"])
    if row["conversion_method"] == "showcase_unit_price_cycle":
        return _decision(row_id, "fail", ["DP6_CUSTOMS_SHOWCASE_UNIT_PRICE_CYCLE"])
    status = row["applicability_status"]
    if status == "pending":
        return _decision(row_id, "indeterminate", ["DP6_CUSTOMS_APPLICABILITY_PENDING"])
    if status == "not_applicable_domestic_sales":
        if not isinstance(row["domestic_sales_evidence"], str) or not row["domestic_sales_evidence"].strip():
            return _decision(row_id, "indeterminate", ["DP6_CUSTOMS_DOMESTIC_SALES_EVIDENCE_MISSING"])
        return _decision(row_id, "pass", [], comparison_basis={"scope": "not_applicable"})
    if status in {"company_level", "plant_level"}:
        return _decision(row_id, "fail", ["DP6_CUSTOMS_8534_COMPANY_OR_PLANT_FORBIDDEN"])
    metadata = row["metadata"]
    if not isinstance(metadata, dict):
        return _decision(row_id, "indeterminate", ["DP6_CUSTOMS_METADATA_INCOMPLETE"])
    missing = sorted(CUSTOMS_METADATA_KEYS - metadata.keys())
    missing.extend(key for key, value in metadata.items() if not isinstance(value, str) or not value.strip())
    if missing:
        return _decision(
            row_id,
            "indeterminate",
            ["DP6_CUSTOMS_METADATA_INCOMPLETE"],
            incomparability_reason=";".join(missing),
        )
    return _decision(
        row_id,
        "pass",
        [],
        comparison_basis={"scope": "macro_only", "customs_code": "8534"},
        tolerance_anchor=metadata["conversion_anchor"],
    )


def validate_document(document: Any, adr: Any = None) -> dict[str, Any]:
    """Return a JSON-serializable report; no result is inferred from facts."""
    report: dict[str, Any] = {
        "schema_version": "dp6.publish-gate.report.v1",
        "overall_status": "fail",
        "publishable": False,
        "rows": [],
        "counts": {"pass": 0, "fail": 0, "indeterminate": 0},
    }
    if not isinstance(document, dict):
        report["errors"] = ["DP6_INPUT_NOT_OBJECT"]
        return report
    if set(document) != {"schema_version", "rows"} or document.get("schema_version") != "dp6.publish-gate.input.v1":
        report["errors"] = ["DP6_ROOT_SCHEMA_MISMATCH"]
    rows = document.get("rows")
    if not isinstance(rows, list):
        report["errors"] = report.get("errors", []) + ["DP6_ROOT_ROWS_NOT_ARRAY"]
        return report
    adr_errors = validate_adr(adr) if adr is not None else ["missing_adr"]
    if adr is not None and adr_errors:
        report["errors"] = [f"DP6_ADR_{error.upper().replace(':', '_')}" for error in adr_errors]
    id_counts: dict[Any, int] = {}
    for row in rows:
        if isinstance(row, dict):
            id_counts[row.get("id")] = id_counts.get(row.get("id"), 0) + 1
    for row in rows:
        if not isinstance(row, dict):
            result = _decision("<non-object>", "fail", ["DP6_SCHEMA_NOT_OBJECT"])
        elif id_counts.get(row.get("id"), 0) > 1:
            result = _decision(str(row.get("id")), "fail", ["DP6_DUPLICATE_ID"])
        elif row.get("kind") == QUANT_KIND:
            result = _validate_quant(row, adr if isinstance(adr, dict) else None, adr_errors)
        elif row.get("kind") == CUSTOMS_KIND:
            result = _validate_customs(row)
        else:
            result = _decision(str(row.get("id", "<missing-id>")), "fail", ["DP6_SCHEMA_UNKNOWN_KIND"])
        report["rows"].append(result)
        report["counts"][result["status"]] += 1
    if report.get("errors") or report["counts"]["fail"]:
        report["overall_status"] = "fail"
    elif report["counts"]["indeterminate"]:
        report["overall_status"] = "indeterminate"
    else:
        report["overall_status"] = "pass"
    report["publishable"] = report["overall_status"] == "pass"
    return report
