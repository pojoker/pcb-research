"""Small, dependency-free structural checks for the DP6 JSON contract."""

from __future__ import annotations

import datetime as dt
import math
from typing import Any, Iterable

from .errors import NonFiniteNumber

STATUSES = {"pass", "fail", "indeterminate"}
EVIDENCE_GRADES = {"C", "D"}
QUANT_KIND = "quantitative_inference"
CUSTOMS_KIND = "customs_calibration"
PERIOD_TYPES = {"month", "quarter", "half_year", "year", "custom"}
CURRENCIES = {"CNY", "USD", "TWD", "HKD", "JPY", "EUR", "NA"}
CAPACITY_ANCHORS = {
    "production_sales_table",
    "built_capacity_self_disclosure",
    "approval_capacity",
}
CUSTOMS_STATUSES = {
    "applicable_macro",
    "pending",
    "not_applicable_domestic_sales",
    "company_level",
    "plant_level",
}
CUSTOMS_USE_LEVELS = {"region_industry", "company", "plant"}
CONVERSION_METHODS = {"none", "macro_anchor", "showcase_unit_price_cycle"}

QUANT_KEYS = {
    "id", "kind", "subject_id", "plant_id", "product_family", "fab_cell",
    "period", "period_type", "metric_type", "value", "unit", "currency",
    "consolidation_basis", "derivation_formula", "revenue_input",
    "unit_price_input", "capacity_ceiling", "customs_applicability",
    "evidence_grade", "retrieval_date", "scenario", "comparison",
    "recalibration",
}
CUSTOMS_KEYS = {
    "id", "kind", "customs_code", "calibration_scope", "applicability_status",
    "use_level", "target_metric", "target_product_family", "target_geography",
    "metadata", "conversion_method", "domestic_sales_evidence", "recalibration",
}
INPUT_KEYS = {"value", "unit", "currency", "anchor"}
CAPACITY_KEYS = {
    "value", "unit", "period_type", "anchor_type", "anchor", "human_verified"
}
COMPARISON_KEYS = {
    "upper_bound_value", "upper_bound_unit", "upper_bound_period",
    "upper_bound_period_type", "upper_bound_currency",
    "upper_bound_consolidation_basis", "subject_id", "plant_id",
    "product_family", "fab_cell", "metric_type", "tolerance_adr_id",
}
RECAL_KEYS = {
    "actual_value", "actual_unit", "actual_period", "error",
    "error_formula", "date",
}
CUSTOMS_METADATA_KEYS = {
    "tariff_year", "full_subheading", "direction", "quantity_unit",
    "product_scope", "trade_mode", "declarant", "origin",
    "attribution_method", "period", "coverage_gap", "conversion_anchor",
}
ADR_KEYS = {
    "schema_version", "id", "status", "tolerance", "unit", "metric_type",
    "period_type", "scope", "decided_by", "decision_date", "evidence_anchor",
    "effective_from", "effective_to",
}
ADR_SCOPE_KEYS = {
    "subject_id", "plant_id", "product_family", "fab_cell", "metric_type",
    "unit", "period_type", "period", "currency", "consolidation_basis",
}


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def key_errors(obj: Any, required: Iterable[str], allowed: Iterable[str] | None = None) -> list[str]:
    if not isinstance(obj, dict):
        return ["not_object"]
    required_set = set(required)
    allowed_set = set(allowed or required_set)
    errors = [f"missing:{key}" for key in sorted(required_set - obj.keys())]
    errors.extend(f"unknown:{key}" for key in sorted(obj.keys() - allowed_set))
    return errors


def _string_errors(obj: dict[str, Any], fields: Iterable[str]) -> list[str]:
    return [f"not_nonempty_string:{field}" for field in fields if not _nonempty(obj.get(field))]


def validate_recalibration(value: Any, row: dict[str, Any]) -> list[str]:
    errors = key_errors(value, RECAL_KEYS)
    if errors:
        return errors
    values = [value[key] for key in RECAL_KEYS]
    all_empty = all(item is None for item in values)
    all_full = all(item is not None for item in values)
    if not all_empty and not all_full:
        return ["recalibration_partial"]
    if all_empty:
        return []
    errors = []
    if not _is_finite_number(value["actual_value"]):
        errors.append("recalibration_actual_not_finite")
    if not _is_finite_number(value["error"]):
        errors.append("recalibration_error_not_finite")
    if value["actual_unit"] != row.get("unit"):
        errors.append("recalibration_unit_mismatch")
    if value["actual_period"] != row.get("period"):
        errors.append("recalibration_period_mismatch")
    if not _date(value["date"]):
        errors.append("recalibration_date_invalid")
    actual = value["actual_value"]
    inferred = row.get("value")
    if value["error_formula"] not in {
        "actual_value - inferred_value",
        "inferred_value - actual_value",
        "abs(actual_value - inferred_value)",
    }:
        errors.append("recalibration_formula_invalid")
    elif not _is_finite_number(actual) or not _is_finite_number(row.get("value")):
        errors.append("recalibration_values_not_finite")
    else:
        expected = {
            "actual_value - inferred_value": actual - inferred,
            "inferred_value - actual_value": inferred - actual,
            "abs(actual_value - inferred_value)": abs(actual - inferred),
        }[value["error_formula"]]
        if not math.isclose(value["error"], expected, rel_tol=1e-9, abs_tol=1e-9):
            errors.append("recalibration_formula_mismatch")
    return errors


def validate_adr(adr: Any) -> list[str]:
    errors = key_errors(adr, ADR_KEYS)
    if errors:
        return errors
    errors.extend(_string_errors(adr, ("schema_version", "id", "status", "unit", "metric_type", "period_type", "decided_by", "evidence_anchor")))
    if adr.get("status") not in {"approved", "unapproved", "pending", "rejected"}:
        errors.append("unknown:status")
    if not _is_finite_number(adr.get("tolerance")) or adr["tolerance"] < 0:
        errors.append("tolerance_not_finite_or_negative")
    if adr.get("period_type") not in PERIOD_TYPES:
        errors.append("unknown:period_type")
    errors.extend(_validate_scope(adr.get("scope")))
    for field in ("decision_date", "effective_from"):
        if not _date(adr.get(field)):
            errors.append(f"invalid_date:{field}")
    if adr.get("effective_to") is not None and not _date(adr["effective_to"]):
        errors.append("invalid_date:effective_to")
    return errors


def _validate_scope(scope: Any) -> list[str]:
    errors = key_errors(scope, ADR_SCOPE_KEYS)
    if errors:
        return errors
    errors.extend(_string_errors(scope, ADR_SCOPE_KEYS))
    if scope.get("period_type") not in PERIOD_TYPES:
        errors.append("unknown:scope.period_type")
    if scope.get("currency") not in CURRENCIES:
        errors.append("unknown:scope.currency")
    return errors


def validate_row_structure(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["not_object"]
    kind = row.get("kind")
    if kind == QUANT_KIND:
        return _validate_quant_structure(row)
    if kind == CUSTOMS_KIND:
        return _validate_customs_structure(row)
    return ["unknown:kind"]


def _validate_quant_structure(row: dict[str, Any]) -> list[str]:
    errors = key_errors(row, QUANT_KEYS)
    if errors:
        return errors
    errors.extend(_string_errors(row, (
        "id", "subject_id", "plant_id", "product_family", "fab_cell", "period",
        "metric_type", "unit", "consolidation_basis", "derivation_formula",
    )))
    if row.get("period_type") not in PERIOD_TYPES:
        errors.append("unknown:period_type")
    if row.get("currency") not in CURRENCIES:
        errors.append("unknown:currency")
    if not _is_finite_number(row.get("value")):
        errors.append("value_not_finite")
    if not isinstance(row.get("scenario"), bool):
        errors.append("scenario_not_boolean")
    if row.get("evidence_grade") not in EVIDENCE_GRADES:
        errors.append("evidence_grade_above_C_or_unknown")
    if row.get("scenario") and row.get("evidence_grade") != "D":
        errors.append("scenario_requires_D")
    if not row.get("scenario") and row.get("evidence_grade") != "C":
        errors.append("baseline_requires_C")
    if not _date(row.get("retrieval_date")):
        errors.append("retrieval_date_invalid")
    for name in ("revenue_input", "unit_price_input"):
        input_value = row.get(name)
        errors.extend(key_errors(input_value, INPUT_KEYS))
        if isinstance(input_value, dict):
            if not _is_finite_number(input_value.get("value")):
                errors.append(f"{name}_not_finite")
            errors.extend(_string_errors(input_value, ("unit", "currency", "anchor")))
    ceiling = row.get("capacity_ceiling")
    errors.extend(key_errors(ceiling, CAPACITY_KEYS))
    if isinstance(ceiling, dict):
        if not _is_finite_number(ceiling.get("value")) or ceiling.get("value") < 0:
            errors.append("capacity_ceiling_not_finite_or_negative")
        if ceiling.get("period_type") not in PERIOD_TYPES:
            errors.append("unknown:capacity_ceiling.period_type")
        if ceiling.get("anchor_type") not in CAPACITY_ANCHORS:
            errors.append("unknown:capacity_ceiling.anchor_type")
        errors.extend(_string_errors(ceiling, ("unit", "anchor")))
        if not isinstance(ceiling.get("human_verified"), bool):
            errors.append("capacity_human_verified_not_boolean")
    comparison = row.get("comparison")
    errors.extend(key_errors(comparison, COMPARISON_KEYS))
    if isinstance(comparison, dict):
        if not _is_finite_number(comparison.get("upper_bound_value")) or comparison.get("upper_bound_value") < 0:
            errors.append("comparison_upper_bound_not_finite_or_negative")
        errors.extend(_string_errors(comparison, (
            "upper_bound_unit", "upper_bound_period", "upper_bound_consolidation_basis",
            "subject_id", "plant_id", "product_family", "fab_cell", "metric_type",
            "tolerance_adr_id",
        )))
        if comparison.get("upper_bound_period_type") not in PERIOD_TYPES:
            errors.append("unknown:comparison.period_type")
        if comparison.get("upper_bound_currency") not in CURRENCIES:
            errors.append("unknown:comparison.currency")
    errors.extend(validate_recalibration(row.get("recalibration"), row))
    customs = row.get("customs_applicability")
    errors.extend(key_errors(customs, {"status", "scope", "anchor"}))
    if isinstance(customs, dict):
        if customs.get("status") not in {"not_applicable", "macro_only", "pending", "company_level", "plant_level"}:
            errors.append("unknown:customs_applicability.status")
        errors.extend(_string_errors(customs, ("scope", "anchor")))
        if customs.get("status") in {"company_level", "plant_level"}:
            errors.append("customs_company_or_plant_use")
    return errors


def _validate_customs_structure(row: dict[str, Any]) -> list[str]:
    errors = key_errors(row, CUSTOMS_KEYS)
    if errors:
        return errors
    errors.extend(_string_errors(row, (
        "id", "customs_code", "calibration_scope", "target_metric",
        "target_product_family", "target_geography",
    )))
    if row.get("customs_code") != "8534":
        errors.append("customs_code_must_be_8534")
    if row.get("calibration_scope") != "macro_only":
        errors.append("customs_scope_not_macro_only")
    if row.get("applicability_status") not in CUSTOMS_STATUSES:
        errors.append("unknown:applicability_status")
    if row.get("use_level") not in CUSTOMS_USE_LEVELS:
        errors.append("unknown:use_level")
    if row.get("conversion_method") not in CONVERSION_METHODS:
        errors.append("unknown:conversion_method")
    if not isinstance(row.get("domestic_sales_evidence"), str):
        errors.append("domestic_sales_evidence_not_string")
    metadata = row.get("metadata")
    if isinstance(metadata, dict):
        # The domain rule intentionally makes an incomplete 8534 metadata
        # tuple indeterminate, so missing metadata keys are checked by the
        # decision layer rather than promoted to a structural hard failure.
        errors.extend(f"unknown:metadata.{key}" for key in sorted(metadata.keys() - CUSTOMS_METADATA_KEYS))
    return errors


def date_in_effective_range(adr: dict[str, Any], retrieval_date: str) -> bool:
    if retrieval_date < adr["effective_from"]:
        return False
    return adr.get("effective_to") is None or retrieval_date <= adr["effective_to"]


def adr_scope_matches(adr: dict[str, Any], row: dict[str, Any], comparison: dict[str, Any]) -> bool:
    scope = adr["scope"]
    expected = {
        "subject_id": comparison["subject_id"],
        "plant_id": comparison["plant_id"],
        "product_family": comparison["product_family"],
        "fab_cell": comparison["fab_cell"],
        "metric_type": comparison["metric_type"],
        "unit": comparison["upper_bound_unit"],
        "period_type": comparison["upper_bound_period_type"],
        "period": comparison["upper_bound_period"],
        "currency": comparison["upper_bound_currency"],
        "consolidation_basis": comparison["upper_bound_consolidation_basis"],
    }
    return all(scope[key] == value for key, value in expected.items())
