"""Strict JSON schema parsing for the DP5 ledger contract.

DP5 deliberately accepts JSON only.  Canonical ``tree.yaml`` is JSON-compatible
YAML, so the standard library can read its active cell list without accepting a
second YAML dialect or a third-party parser.
"""

from __future__ import annotations

from datetime import date
import json
from math import isfinite
from pathlib import Path
import re
from typing import Any, Mapping

from .errors import SchemaError


ROOT_FIELDS = (
    "schema_version",
    "subject_mappings",
    "points",
    "metrics",
    "manufacturing_edges",
    "prohibited_additive_subject_pairs",
    "aggregation_requests",
)
SUBJECT_FIELDS = (
    "subject_id",
    "subject_type",
    "issuer_id",
    "legal_entity_id",
    "plant_id",
    "group_id",
    "missing_id_reason",
)
COMMON_FIELDS = (
    "subject_id",
    "reporting_subject_id",
    "reporting_subject_type",
    "scope",
    "consolidation_basis",
    "period_start",
    "period_end",
    "evidence_anchor_id",
    "evidence_quote",
)
POINT_FIELDS = (
    "point_id",
    "record_type",
    *COMMON_FIELDS,
    "cell_id",
    "product_family",
    "capability_role",
    "evidence_subject_id",
    "maturity",
    "mixed_business",
    "business_scope",
    "metric_scope",
    "split_evidence_id",
    "self_owned_output_inference",
)
METRIC_FIELDS = (
    "metric_id",
    "record_type",
    *COMMON_FIELDS,
    "cell_id",
    "product_family",
    "metric_type",
    "output_channel",
    "stage",
    "measurement_basis",
    "value",
    "unit",
    "currency",
    "ownership_basis",
    "physical_flow_id",
    "line_or_asset_id",
    "metric_definition",
    "mixed_business",
    "business_scope",
    "metric_scope",
    "split_evidence_id",
    "derivation_source_type",
    "derivation_source_id",
)
EDGE_FIELDS = (
    "edge_id",
    "record_type",
    *COMMON_FIELDS,
    "capacity_owner",
    "process_operator",
    "contracting_party",
    "product_integrator",
    "seller_of_record",
    "edge_type",
    "relationship_start",
    "relationship_end",
)
PAIR_FIELDS = (
    "pair_id",
    "record_type",
    *COMMON_FIELDS,
    "subject_a_id",
    "subject_b_id",
    "relationship_evidence_anchor_id",
    "relationship_evidence_quote",
    "adjudicator",
    "adjudicated_on",
    "registry_version",
)
AGGREGATION_FIELDS = ("aggregation_id", "metric_ids", "output_channel", "metric_type")

SUBJECT_TYPES = frozenset({"issuer", "legal_entity", "plant", "group"})
SCOPES = SUBJECT_TYPES
CONSOLIDATION_BASES = frozenset({"standalone", "consolidated", "plant_specific", "group_consolidated"})
CAPABILITY_ROLES = frozenset(
    {
        "material_supply",
        "copper_foil_supply",
        "chemical_supply",
        "equipment_supply",
        "process_outsourcing",
        "bare_board_manufacturing",
        "substrate_manufacturing",
    }
)
MATURITY_LEVELS = frozenset({"planned", "sample", "qualified", "mass_production"})
METRIC_TYPES = frozenset({"actual_production", "sales", "revenue", "approved_capacity", "built_capacity"})
OUTPUT_CHANNELS = frozenset({"physical", "disclosure"})
OWNERSHIP_BASES = frozenset({"self_owned", "outsourced", "not_applicable"})
DERIVATION_SOURCE_TYPES = frozenset({"direct_evidence", "point", "manufacturing_edge"})
EDGE_TYPES = frozenset({"委外加工", "受托加工", "表面处理外协", "来料加工", "返工再处理", "外发加工"})
UNITS = frozenset({"square_meter", "piece", "CNY", "TWD", "HKD", "USD", "JPY", "KRW"})
CURRENCIES = frozenset({"NONE", "CNY", "TWD", "HKD", "USD", "JPY", "KRW"})
MEASUREMENT_BASIS = frozenset(
    {"actual_production", "actual_sales", "recognized_revenue", "approved_capacity", "built_capacity"}
)

PRODUCT_FAMILY_TO_CELL = {
    "普通刚性": "FAB1",
    "HDI": "FAB1",
    "FPC": "FAB1",
    "刚挠": "FAB1",
    "金属基": "FAB1",
    "高频": "FAB1",
    "背板": "FAB1",
    "IC 载板": "FAB2",
    "PCBA": "OUT",
    "SMT": "OUT",
    "EMS": "OUT",
    "设计": "OUT",
    "整机": "OUT",
    "锂电铜箔": "OUT",
}
OUTSIDE_FAMILIES = frozenset(family for family, target in PRODUCT_FAMILY_TO_CELL.items() if target == "OUT")
FINISHED_BOARD_FAMILIES = frozenset(family for family, target in PRODUCT_FAMILY_TO_CELL.items() if target in {"FAB1", "FAB2"})
ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def _reject_constant(value: str) -> None:
    raise SchemaError(f"non-finite JSON constant is forbidden: {value}")


def load_json(path: str | Path) -> Any:
    source = Path(path)
    try:
        return json.loads(source.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    except FileNotFoundError as exc:
        raise SchemaError(f"input file not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise SchemaError(f"{source}: invalid JSON at line {exc.lineno}, column {exc.colno}") from exc


def load_active_cells(tree_path: str | Path) -> dict[str, str]:
    """Return active ``cell_id -> stage`` from the canonical read-only tree."""

    value = load_json(tree_path)
    if not isinstance(value, Mapping) or not isinstance(value.get("cells"), list):
        raise SchemaError("tree must be a JSON-compatible YAML object with a cells list")
    result: dict[str, str] = {}
    for index, cell in enumerate(value["cells"]):
        if not isinstance(cell, Mapping):
            raise SchemaError(f"tree.cells[{index}] must be an object")
        cell_id = cell.get("cell_id")
        stage = cell.get("stage")
        if not isinstance(cell_id, str) or not cell_id or not isinstance(stage, str) or not stage:
            raise SchemaError(f"tree.cells[{index}] requires non-empty cell_id and stage")
        if cell_id in result:
            raise SchemaError(f"tree contains duplicate cell_id {cell_id!r}")
        result[cell_id] = stage
    if not result:
        raise SchemaError("tree contains no active cells")
    return result


def exact_keys(record: Mapping[str, Any], fields: tuple[str, ...], label: str) -> list[str]:
    errors: list[str] = []
    missing = [field for field in fields if field not in record]
    extra = sorted(set(record).difference(fields))
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"{label}: unknown fields: {', '.join(extra)}")
    return errors


def require_string(record: Mapping[str, Any], field: str, label: str, errors: list[str], *, identifier: bool = False) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: {field} must be a non-empty string")
        return ""
    value = value.strip()
    if identifier and not ID_RE.fullmatch(value):
        errors.append(f"{label}: {field} must match {ID_RE.pattern}")
    return value


def require_date(record: Mapping[str, Any], field: str, label: str, errors: list[str]) -> date | None:
    value = require_string(record, field, label, errors)
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label}: {field} must use YYYY-MM-DD")
        return None
    if parsed.isoformat() != value:
        errors.append(f"{label}: {field} must use YYYY-MM-DD")
    return parsed


def require_enum(record: Mapping[str, Any], field: str, allowed: frozenset[str], label: str, errors: list[str]) -> str:
    value = require_string(record, field, label, errors)
    if value and value not in allowed:
        errors.append(f"{label}: {field} must be one of {sorted(allowed)}")
    return value


def require_finite_number(record: Mapping[str, Any], field: str, label: str, errors: list[str]) -> float | None:
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{label}: {field} must be a finite number")
        return None
    if not isfinite(value):
        errors.append(f"{label}: {field} must be finite (NaN/Inf are forbidden)")
        return None
    if value < 0:
        errors.append(f"{label}: {field} must be non-negative")
    return float(value)
