"""Fail-closed mechanical gates for evidence, output, and outsourcing ledgers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Mapping

from .schema import (
    AGGREGATION_FIELDS,
    CAPABILITY_ROLES,
    COMMON_FIELDS,
    CONSOLIDATION_BASES,
    CURRENCIES,
    DERIVATION_SOURCE_TYPES,
    EDGE_FIELDS,
    EDGE_TYPES,
    MATURITY_LEVELS,
    MEASUREMENT_BASIS,
    METRIC_FIELDS,
    METRIC_TYPES,
    OUTPUT_CHANNELS,
    OUTSIDE_FAMILIES,
    OWNERSHIP_BASES,
    PAIR_FIELDS,
    POINT_FIELDS,
    PRODUCT_FAMILY_TO_CELL,
    ROOT_FIELDS,
    SCOPES,
    SUBJECT_FIELDS,
    SUBJECT_TYPES,
    UNITS,
    exact_keys,
    require_date,
    require_enum,
    require_finite_number,
    require_string,
)


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    details: tuple[tuple[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": list(self.errors), "warnings": list(self.warnings), "details": dict(self.details)}


def _report(errors: list[str], **details: Any) -> ValidationReport:
    return ValidationReport(ok=not errors, errors=tuple(errors), details=tuple(details.items()))


def _record_list(payload: Mapping[str, Any], field: str, errors: list[str]) -> list[Mapping[str, Any]]:
    value = payload.get(field)
    if not isinstance(value, list):
        errors.append(f"ledger.{field} must be an array")
        return []
    result: list[Mapping[str, Any]] = []
    for index, record in enumerate(value):
        if not isinstance(record, Mapping):
            errors.append(f"ledger.{field}[{index}] must be an object")
        else:
            result.append(record)
    return result


def _common(record: Mapping[str, Any], label: str, subjects: Mapping[str, Mapping[str, str]], errors: list[str]) -> tuple[str, date | None, date | None]:
    subject_id = require_string(record, "subject_id", label, errors, identifier=True)
    reporting_id = require_string(record, "reporting_subject_id", label, errors, identifier=True)
    reporting_type = require_enum(record, "reporting_subject_type", SUBJECT_TYPES, label, errors)
    require_enum(record, "scope", SCOPES, label, errors)
    require_enum(record, "consolidation_basis", CONSOLIDATION_BASES, label, errors)
    start = require_date(record, "period_start", label, errors)
    end = require_date(record, "period_end", label, errors)
    require_string(record, "evidence_anchor_id", label, errors, identifier=True)
    require_string(record, "evidence_quote", label, errors)
    if start and end and start > end:
        errors.append(f"{label}: period_start must not be later than period_end")
    if subject_id and subject_id not in subjects:
        errors.append(f"{label}: subject_id {subject_id!r} is not in subject_mappings")
    if reporting_id and reporting_id not in subjects:
        errors.append(f"{label}: reporting_subject_id {reporting_id!r} is not in subject_mappings")
    elif reporting_id and reporting_type and subjects[reporting_id]["subject_type"] != reporting_type:
        errors.append(f"{label}: reporting_subject_type does not match its subject mapping")
    return subject_id, start, end


def _family_and_cell(
    record: Mapping[str, Any],
    label: str,
    active_cells: Mapping[str, str],
    errors: list[str],
    *,
    require_finished_board_target: bool,
) -> tuple[str, str]:
    cell_id = require_string(record, "cell_id", label, errors)
    family = require_string(record, "product_family", label, errors)
    if cell_id and cell_id not in active_cells:
        errors.append(f"{label}: cell_id {cell_id!r} is not an active tree cell")
    expected = PRODUCT_FAMILY_TO_CELL.get(family)
    if not expected:
        errors.append(f"{label}: unknown product_family {family!r}")
    elif expected == "OUT":
        errors.append(f"{label}: outside product_family {family!r} must not attach to a FAB/cell")
    elif require_finished_board_target and cell_id in {"FAB1", "FAB2"} and cell_id != expected:
        errors.append(f"{label}: product_family {family!r} must attach to {expected}, got {cell_id!r}")
    return cell_id, family


def _scope_split(record: Mapping[str, Any], label: str, errors: list[str]) -> None:
    mixed = record.get("mixed_business")
    if not isinstance(mixed, bool):
        errors.append(f"{label}: mixed_business must be boolean")
    require_string(record, "business_scope", label, errors)
    require_string(record, "metric_scope", label, errors)
    raw_split = record.get("split_evidence_id")
    if not isinstance(raw_split, str):
        errors.append(f"{label}: split_evidence_id must be a string")
        return
    split_id = raw_split.strip()
    if mixed is True:
        if not split_id:
            errors.append(f"{label}: mixed business requires split_evidence_id")
        elif not re.fullmatch(r"[a-z][a-z0-9_-]*", split_id):
            errors.append(f"{label}: split_evidence_id must be a valid identifier")
    elif mixed is False and split_id:
        errors.append(f"{label}: non-mixed record must not claim split evidence")


def _validate_subject_mappings(records: list[Mapping[str, Any]], errors: list[str]) -> dict[str, Mapping[str, str]]:
    subjects: dict[str, Mapping[str, str]] = {}
    for index, record in enumerate(records):
        label = f"subject_mappings[{index}]"
        errors.extend(exact_keys(record, SUBJECT_FIELDS, label))
        subject_id = require_string(record, "subject_id", label, errors, identifier=True)
        subject_type = require_enum(record, "subject_type", SUBJECT_TYPES, label, errors)
        missing_ids: list[str] = []
        for field in ("issuer_id", "legal_entity_id", "plant_id", "group_id"):
            raw_id = record.get(field)
            if not isinstance(raw_id, str):
                errors.append(f"{label}: {field} must be a string")
                continue
            mapped_id = raw_id.strip()
            if not mapped_id:
                missing_ids.append(field)
            elif not re.fullmatch(r"[a-z][a-z0-9_-]*", mapped_id):
                errors.append(f"{label}: {field} must be a valid identifier")
        own_field = {
            "issuer": "issuer_id",
            "legal_entity": "legal_entity_id",
            "plant": "plant_id",
            "group": "group_id",
        }.get(subject_type)
        if own_field and not str(record.get(own_field, "")).strip():
            errors.append(f"{label}: subject_type {subject_type!r} requires {own_field}")
        missing_reason = record.get("missing_id_reason")
        if not isinstance(missing_reason, str):
            errors.append(f"{label}: missing_id_reason must be a string")
        elif missing_ids and not missing_reason.strip():
            errors.append(f"{label}: missing mapped IDs require missing_id_reason")
        if subject_id in subjects:
            errors.append(f"{label}: duplicate subject_id {subject_id!r}")
        elif subject_id:
            subjects[subject_id] = {key: str(record.get(key, "")).strip() for key in SUBJECT_FIELDS}
    return subjects


def _validate_points(records: list[Mapping[str, Any]], subjects: Mapping[str, Mapping[str, str]], active_cells: Mapping[str, str], errors: list[str]) -> dict[str, Mapping[str, Any]]:
    points: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(records):
        label = f"points[{index}]"
        errors.extend(exact_keys(record, POINT_FIELDS, label))
        point_id = require_string(record, "point_id", label, errors, identifier=True)
        if record.get("record_type") != "point":
            errors.append(f"{label}: record_type must be 'point'")
        subject_id, _, _ = _common(record, label, subjects, errors)
        cell_id, family = _family_and_cell(record, label, active_cells, errors, require_finished_board_target=False)
        role = require_enum(record, "capability_role", CAPABILITY_ROLES, label, errors)
        evidence_subject_id = require_string(record, "evidence_subject_id", label, errors, identifier=True)
        require_enum(record, "maturity", MATURITY_LEVELS, label, errors)
        _scope_split(record, label, errors)
        if not isinstance(record.get("self_owned_output_inference"), bool):
            errors.append(f"{label}: self_owned_output_inference must be boolean")
        if evidence_subject_id and evidence_subject_id not in subjects:
            errors.append(f"{label}: evidence_subject_id {evidence_subject_id!r} is not in subject_mappings")
        elif evidence_subject_id and subject_id and evidence_subject_id != subject_id:
            errors.append(f"{label}: evidence_subject_id must equal subject_id; subject mismatch is fail-closed")
        if role == "process_outsourcing" and record.get("self_owned_output_inference") is True:
            errors.append(f"{label}: process_outsourcing point must not carry self-owned output inference")
        if role == "bare_board_manufacturing" and cell_id != "FAB1":
            errors.append(f"{label}: bare_board_manufacturing requires cell_id FAB1")
        if role == "substrate_manufacturing" and cell_id != "FAB2":
            errors.append(f"{label}: substrate_manufacturing requires cell_id FAB2")
        if family in OUTSIDE_FAMILIES:
            errors.append(f"{label}: outside family cannot create an in-tree capability point")
        if point_id in points:
            errors.append(f"{label}: duplicate point_id {point_id!r}")
        elif point_id:
            points[point_id] = record
    return points


def _validate_edges(records: list[Mapping[str, Any]], subjects: Mapping[str, Mapping[str, str]], errors: list[str]) -> dict[str, Mapping[str, Any]]:
    edges: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(records):
        label = f"manufacturing_edges[{index}]"
        errors.extend(exact_keys(record, EDGE_FIELDS, label))
        edge_id = require_string(record, "edge_id", label, errors, identifier=True)
        if record.get("record_type") != "manufacturing_edge":
            errors.append(f"{label}: record_type must be 'manufacturing_edge'")
        _common(record, label, subjects, errors)
        for field in ("capacity_owner", "process_operator", "contracting_party", "product_integrator", "seller_of_record"):
            actor = require_string(record, field, label, errors, identifier=True)
            if actor and actor not in subjects:
                errors.append(f"{label}: {field} {actor!r} is not in subject_mappings")
        require_enum(record, "edge_type", EDGE_TYPES, label, errors)
        start = require_date(record, "relationship_start", label, errors)
        end = require_date(record, "relationship_end", label, errors)
        if start and end and start > end:
            errors.append(f"{label}: relationship_start must not be later than relationship_end")
        if edge_id in edges:
            errors.append(f"{label}: duplicate edge_id {edge_id!r}")
        elif edge_id:
            edges[edge_id] = record
    return edges


def _validate_metrics(records: list[Mapping[str, Any]], subjects: Mapping[str, Mapping[str, str]], active_cells: Mapping[str, str], points: Mapping[str, Mapping[str, Any]], edges: Mapping[str, Mapping[str, Any]], errors: list[str]) -> dict[str, Mapping[str, Any]]:
    metrics: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(records):
        label = f"metrics[{index}]"
        errors.extend(exact_keys(record, METRIC_FIELDS, label))
        metric_id = require_string(record, "metric_id", label, errors, identifier=True)
        if record.get("record_type") != "metric":
            errors.append(f"{label}: record_type must be 'metric'")
        subject_id, _, _ = _common(record, label, subjects, errors)
        cell_id, family = _family_and_cell(record, label, active_cells, errors, require_finished_board_target=True)
        metric_type = require_enum(record, "metric_type", METRIC_TYPES, label, errors)
        output_channel = require_enum(record, "output_channel", OUTPUT_CHANNELS, label, errors)
        stage = require_string(record, "stage", label, errors)
        basis = require_enum(record, "measurement_basis", MEASUREMENT_BASIS, label, errors)
        require_finite_number(record, "value", label, errors)
        unit = require_enum(record, "unit", UNITS, label, errors)
        currency = require_enum(record, "currency", CURRENCIES, label, errors)
        ownership = require_enum(record, "ownership_basis", OWNERSHIP_BASES, label, errors)
        raw_flow_id = record.get("physical_flow_id")
        raw_line_id = record.get("line_or_asset_id")
        raw_definition = record.get("metric_definition")
        physical_flow_id = raw_flow_id.strip() if isinstance(raw_flow_id, str) else ""
        line_or_asset_id = raw_line_id.strip() if isinstance(raw_line_id, str) else ""
        metric_definition = raw_definition.strip() if isinstance(raw_definition, str) else ""
        if not isinstance(raw_flow_id, str) or not isinstance(raw_line_id, str) or not isinstance(raw_definition, str):
            errors.append(f"{label}: physical output key fields must be strings")
        if physical_flow_id and not re.fullmatch(r"[a-z][a-z0-9_-]*", physical_flow_id):
            errors.append(f"{label}: physical_flow_id must be a valid identifier")
        if line_or_asset_id and not re.fullmatch(r"[a-z][a-z0-9_-]*", line_or_asset_id):
            errors.append(f"{label}: line_or_asset_id must be a valid identifier")
        _scope_split(record, label, errors)
        source_type = require_enum(record, "derivation_source_type", DERIVATION_SOURCE_TYPES, label, errors)
        source_id = require_string(record, "derivation_source_id", label, errors, identifier=True)
        if cell_id and cell_id in active_cells and stage != active_cells[cell_id]:
            errors.append(f"{label}: stage must match tree cell stage {active_cells[cell_id]!r}")
        if metric_type == "actual_production" and (basis != "actual_production" or unit not in {"square_meter", "piece"} or currency != "NONE"):
            errors.append(f"{label}: actual_production requires square_meter/piece and currency NONE")
        if metric_type == "sales" and (basis != "actual_sales" or unit not in {"square_meter", "piece"} or currency != "NONE"):
            errors.append(f"{label}: sales requires actual_sales, square_meter/piece, and currency NONE")
        if metric_type in {"approved_capacity", "built_capacity"} and (
            basis != metric_type or unit not in {"square_meter", "piece"} or currency != "NONE"
        ):
            errors.append(f"{label}: {metric_type} requires matching basis, square_meter/piece, and currency NONE")
        if metric_type == "revenue" and (basis != "recognized_revenue" or unit not in CURRENCIES.difference({"NONE"}) or currency != unit):
            errors.append(f"{label}: revenue requires recognized_revenue and matching non-NONE currency/unit")
        if output_channel == "physical" and (not physical_flow_id or not line_or_asset_id or not metric_definition):
            errors.append(f"{label}: physical output requires physical_flow_id, line_or_asset_id, and metric_definition")
        if output_channel == "disclosure" and (physical_flow_id or line_or_asset_id or metric_definition):
            errors.append(f"{label}: disclosure output must not populate physical output key fields")
        if source_type == "point":
            source = points.get(source_id)
            if source is None:
                errors.append(f"{label}: derivation point {source_id!r} is not present")
            elif source.get("subject_id") != subject_id:
                errors.append(f"{label}: derivation point subject differs from metric subject")
            elif source.get("capability_role") == "process_outsourcing" and ownership == "self_owned":
                errors.append(f"{label}: process_outsourcing point must not generate self-owned output")
        elif source_type == "manufacturing_edge":
            source = edges.get(source_id)
            if source is None:
                errors.append(f"{label}: derivation manufacturing edge {source_id!r} is not present")
            elif ownership == "self_owned":
                errors.append(f"{label}: outsourcing/manufacturing edge must not generate self-owned output")
        if metric_id in metrics:
            errors.append(f"{label}: duplicate metric_id {metric_id!r}")
        elif metric_id:
            metrics[metric_id] = record
    return metrics


def _validate_pairs(records: list[Mapping[str, Any]], subjects: Mapping[str, Mapping[str, str]], errors: list[str]) -> list[Mapping[str, Any]]:
    pairs: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str, str, str]] = set()
    for index, record in enumerate(records):
        label = f"prohibited_additive_subject_pairs[{index}]"
        errors.extend(exact_keys(record, PAIR_FIELDS, label))
        pair_id = require_string(record, "pair_id", label, errors, identifier=True)
        if record.get("record_type") != "prohibited_additive_subject_pair":
            errors.append(f"{label}: record_type must be 'prohibited_additive_subject_pair'")
        _, start, end = _common(record, label, subjects, errors)
        left = require_string(record, "subject_a_id", label, errors, identifier=True)
        right = require_string(record, "subject_b_id", label, errors, identifier=True)
        if left and left not in subjects:
            errors.append(f"{label}: subject_a_id {left!r} is not in subject_mappings")
        if right and right not in subjects:
            errors.append(f"{label}: subject_b_id {right!r} is not in subject_mappings")
        if left and right and left == right:
            errors.append(f"{label}: prohibited pair must contain two different subjects")
        require_string(record, "relationship_evidence_anchor_id", label, errors, identifier=True)
        require_string(record, "relationship_evidence_quote", label, errors)
        require_string(record, "adjudicator", label, errors)
        require_date(record, "adjudicated_on", label, errors)
        require_string(record, "registry_version", label, errors)
        if pair_id in seen_ids:
            errors.append(f"{label}: duplicate pair_id {pair_id!r}")
        seen_ids.add(pair_id)
        if left and right and start and end:
            key = (min(left, right), max(left, right), start.isoformat(), end.isoformat())
            if key in seen_pairs:
                errors.append(f"{label}: duplicate prohibited pair coverage")
            seen_pairs.add(key)
        pairs.append(record)
    return pairs


def _overlap(left_start: date, left_end: date, right_start: date, right_end: date) -> bool:
    return left_start <= right_end and right_start <= left_end


def _validate_aggregations(records: list[Mapping[str, Any]], metrics: Mapping[str, Mapping[str, Any]], pairs: list[Mapping[str, Any]], errors: list[str]) -> None:
    seen: set[str] = set()
    for index, record in enumerate(records):
        label = f"aggregation_requests[{index}]"
        errors.extend(exact_keys(record, AGGREGATION_FIELDS, label))
        request_id = require_string(record, "aggregation_id", label, errors, identifier=True)
        channel = require_enum(record, "output_channel", OUTPUT_CHANNELS, label, errors)
        metric_type = require_enum(record, "metric_type", METRIC_TYPES, label, errors)
        metric_ids = record.get("metric_ids")
        if not isinstance(metric_ids, list) or not metric_ids or not all(isinstance(value, str) and value for value in metric_ids):
            errors.append(f"{label}: metric_ids must be a non-empty list of IDs")
            metric_ids = []
        if len(set(metric_ids)) != len(metric_ids):
            errors.append(f"{label}: metric_ids must not contain duplicates")
        rows = [metrics[metric_id] for metric_id in metric_ids if metric_id in metrics]
        missing = sorted(set(metric_ids).difference(metrics))
        if missing:
            errors.append(f"{label}: unknown metric_ids: {', '.join(missing)}")
        if rows:
            for row in rows:
                if row.get("output_channel") != channel:
                    errors.append(f"{label}: physical and disclosure outputs must not be mixed")
                    break
            for row in rows:
                if row.get("metric_type") != metric_type:
                    errors.append(f"{label}: metric_type must match every source metric")
                    break
            for field in ("cell_id", "product_family", "unit", "currency", "period_start", "period_end", "consolidation_basis"):
                values = {str(row.get(field)) for row in rows}
                if len(values) > 1:
                    errors.append(f"{label}: source metrics must share {field}; default cross-key aggregation is forbidden")
            ownerships = {str(row.get("ownership_basis")) for row in rows}
            if len(ownerships) > 1:
                errors.append(f"{label}: self-owned and outsourced outputs must not be mixed")
            cells = {str(row.get("cell_id")) for row in rows}
            if {"FAB1", "FAB2"}.issubset(cells):
                errors.append(f"{label}: FAB1/FAB2 production, revenue, and area must not be aggregated")
            if {"M1", "M3"}.issubset(cells):
                errors.append(f"{label}: CCL (M1, contains foil) and independent copper foil (M3) must not be aggregated")
            subjects = {str(row.get("subject_id")) for row in rows}
            for pair in pairs:
                left = str(pair.get("subject_a_id"))
                right = str(pair.get("subject_b_id"))
                if {left, right}.issubset(subjects):
                    pair_start = date.fromisoformat(str(pair["period_start"]))
                    pair_end = date.fromisoformat(str(pair["period_end"]))
                    overlap = any(
                        _overlap(date.fromisoformat(str(row["period_start"])), date.fromisoformat(str(row["period_end"])), pair_start, pair_end)
                        for row in rows
                        if str(row.get("subject_id")) in {left, right}
                    )
                    if overlap:
                        errors.append(f"{label}: prohibited additive subject pair hit in either direction: {left}/{right}")
        if request_id in seen:
            errors.append(f"{label}: duplicate aggregation_id {request_id!r}")
        seen.add(request_id)


def validate_ledger(payload: Any, active_cells: Mapping[str, str]) -> ValidationReport:
    """Validate one complete DP5 ledger payload without mutating any input."""

    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return _report(["ledger must be a JSON object"], active_cell_count=len(active_cells))
    errors.extend(exact_keys(payload, ROOT_FIELDS, "ledger"))
    if payload.get("schema_version") != 1:
        errors.append("ledger.schema_version must be 1")
    subject_records = _record_list(payload, "subject_mappings", errors)
    point_records = _record_list(payload, "points", errors)
    metric_records = _record_list(payload, "metrics", errors)
    edge_records = _record_list(payload, "manufacturing_edges", errors)
    pair_records = _record_list(payload, "prohibited_additive_subject_pairs", errors)
    aggregation_records = _record_list(payload, "aggregation_requests", errors)
    subjects = _validate_subject_mappings(subject_records, errors)
    points = _validate_points(point_records, subjects, active_cells, errors)
    edges = _validate_edges(edge_records, subjects, errors)
    metrics = _validate_metrics(metric_records, subjects, active_cells, points, edges, errors)
    pairs = _validate_pairs(pair_records, subjects, errors)
    _validate_aggregations(aggregation_records, metrics, pairs, errors)
    return _report(
        errors,
        active_cell_count=len(active_cells),
        subject_mapping_count=len(subject_records),
        point_count=len(point_records),
        metric_count=len(metric_records),
        manufacturing_edge_count=len(edge_records),
        prohibited_pair_count=len(pair_records),
        aggregation_request_count=len(aggregation_records),
    )
