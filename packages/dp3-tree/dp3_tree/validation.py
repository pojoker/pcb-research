"""Mechanical DP3 tree, attachment, sample, and mapping gates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .errors import SchemaError
from .schema import (
    ACTIVE_CELL_ID_SET,
    ACTIVE_CELL_IDS,
    AXES,
    EXPECTED_AXIS_IDS,
    EXPECTED_OUTSIDE_NEIGHBORS,
    FLOW_ID_RE,
    RESERVED_INACTIVE_CELL_IDS,
    STAGES,
    Tree,
)


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    details: tuple[tuple[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "details": {key: value for key, value in self.details},
        }


def _report(errors: list[str], warnings: list[str] | None = None, **details: Any) -> ValidationReport:
    return ValidationReport(not errors, tuple(errors), tuple(warnings or ()), tuple(details.items()))


def validate_tree(tree: Tree) -> ValidationReport:
    """Validate the frozen canonical tree without modifying it."""

    errors: list[str] = []
    if tree.schema_version != 1:
        errors.append(f"schema_version must be 1, got {tree.schema_version!r}")
    if tree.status != "frozen":
        errors.append(f"status must be 'frozen', got {tree.status!r}")
    if len(tree.cells) != 30:
        errors.append(f"cells must contain exactly 30 active cells, got {len(tree.cells)}")

    ids = [cell.cell_id for cell in tree.cells]
    duplicates = sorted({cell_id for cell_id in ids if ids.count(cell_id) > 1})
    if duplicates:
        errors.append(f"duplicate cell_id: {', '.join(duplicates)}")
    if set(ids) != ACTIVE_CELL_ID_SET:
        missing = sorted(ACTIVE_CELL_ID_SET.difference(ids))
        unknown = sorted(set(ids).difference(ACTIVE_CELL_ID_SET))
        if missing:
            errors.append(f"missing active cell_id: {', '.join(missing)}")
        if unknown:
            errors.append(f"unknown active cell_id: {', '.join(unknown)}")
    if any(cell_id in RESERVED_INACTIVE_CELL_IDS for cell_id in ids):
        errors.append("M6/M8 must not be declared as cell_id")

    flow_ids: list[str] = []
    for cell in tree.cells:
        if cell.system != "physical":
            errors.append(f"{cell.cell_id}: system must be 'physical'")
        if cell.axis not in AXES:
            errors.append(f"{cell.cell_id}: unknown axis {cell.axis!r}")
        if cell.stage not in STAGES:
            errors.append(f"{cell.cell_id}: illegal stage {cell.stage!r}")
        if not FLOW_ID_RE.fullmatch(cell.flow_id):
            errors.append(f"{cell.cell_id}: illegal flow_id {cell.flow_id!r}")
        flow_ids.append(cell.flow_id)
        if cell.cell_id in {"FAB1", "FAB2"} and cell.stage != "finished_board":
            errors.append(f"{cell.cell_id}: finished-board cell must have stage=finished_board")
        if cell.stage == "finished_board" and cell.cell_id not in {"FAB1", "FAB2"}:
            errors.append(f"{cell.cell_id}: only FAB1/FAB2 may use stage=finished_board")
    duplicate_flows = sorted({flow_id for flow_id in flow_ids if flow_ids.count(flow_id) > 1})
    if duplicate_flows:
        errors.append(f"duplicate flow_id: {', '.join(duplicate_flows)}")

    axis_ids = [axis.axis_id for axis in tree.route_axes]
    if tuple(axis_ids) != EXPECTED_AXIS_IDS:
        errors.append(f"route_axes must be exactly A-F in order, got {axis_ids!r}")
    route_values: list[str] = []
    for axis in tree.route_axes:
        if not axis.values:
            errors.append(f"route axis {axis.axis_id}: values must not be empty")
        if len(set(axis.values)) != len(axis.values):
            errors.append(f"route axis {axis.axis_id}: values must be unique")
        route_values.extend(axis.values)
    cell_id_collisions = sorted(set(route_values).intersection(ACTIVE_CELL_ID_SET | RESERVED_INACTIVE_CELL_IDS))
    if cell_id_collisions:
        errors.append(f"route values must not be cell or reserved cell tokens: {', '.join(cell_id_collisions)}")

    if tuple(tree.outside_neighbors) != EXPECTED_OUTSIDE_NEIGHBORS:
        missing = [item for item in EXPECTED_OUTSIDE_NEIGHBORS if item not in tree.outside_neighbors]
        extra = [item for item in tree.outside_neighbors if item not in EXPECTED_OUTSIDE_NEIGHBORS]
        if missing:
            errors.append(f"outside_neighbors missing: {', '.join(missing)}")
        if extra:
            errors.append(f"outside_neighbors unknown: {', '.join(extra)}")
    if "OUT" in tree.cell_ids:
        errors.append("OUT is a namespace label, never a cell_id")
    policy = tree.outside_neighbor_policy
    if "not a physical cell_id" not in policy or "must not" not in policy:
        errors.append("outside_neighbor_policy must state that OUT is not a cell and cannot attach to FAB")
    return _report(errors, cell_count=len(tree.cells), active_cell_ids=list(ACTIVE_CELL_IDS), axis_ids=list(axis_ids))


PRODUCT_FAMILY_TO_TARGET: dict[str, str] = {
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
    "锂电铜箔": "OUT",
    "整机": "OUT",
}
OUTSIDE_FAMILIES = frozenset(key for key, value in PRODUCT_FAMILY_TO_TARGET.items() if value == "OUT")
BOARD_FAMILIES = frozenset(key for key, value in PRODUCT_FAMILY_TO_TARGET.items() if value != "OUT")
SAMPLE_FIELDS = ("sample_id", "entity_id", "entity_name", "role", "sample_kind", "cell_id", "product_family", "outside_neighbor")
SAMPLE_KINDS = frozenset({"board", "capability", "outside"})


def _strict_record(record: Mapping[str, Any], fields: tuple[str, ...], label: str, errors: list[str]) -> None:
    missing = [field for field in fields if field not in record]
    extra = sorted(set(record).difference(fields))
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"{label}: unknown fields: {', '.join(extra)}")


def _required_record_string(record: Mapping[str, Any], field: str, label: str, errors: list[str]) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: {field} must be a non-empty string")
        return ""
    return value.strip()


def validate_samples(records: Iterable[Mapping[str, Any]], tree: Tree) -> ValidationReport:
    """Validate board/capability samples and explicit outside-neighbor samples."""

    errors: list[str] = []
    seen: set[str] = set()
    count = 0
    for index, record in enumerate(records):
        count += 1
        label = f"sample[{index}]"
        if not isinstance(record, Mapping):
            errors.append(f"{label}: must be an object")
            continue
        _strict_record(record, SAMPLE_FIELDS, label, errors)
        sample_id = _required_record_string(record, "sample_id", label, errors)
        entity_id = _required_record_string(record, "entity_id", label, errors)
        entity_name = _required_record_string(record, "entity_name", label, errors)
        role = _required_record_string(record, "role", label, errors)
        kind = _required_record_string(record, "sample_kind", label, errors)
        cell_id = record.get("cell_id")
        family = _required_record_string(record, "product_family", label, errors)
        outside_neighbor = record.get("outside_neighbor")
        if sample_id and sample_id in seen:
            errors.append(f"{label}: duplicate sample_id {sample_id!r}")
        seen.add(sample_id)
        if entity_id == "板厂" or entity_name == "板厂" or role == "板厂":
            errors.append(f"{label}: raw generic '板厂' is forbidden; use an entity and legal cell_id")
        if kind not in SAMPLE_KINDS:
            errors.append(f"{label}: sample_kind must be one of {sorted(SAMPLE_KINDS)}")
        if family not in PRODUCT_FAMILY_TO_TARGET:
            errors.append(f"{label}: unknown product_family {family!r}")
            continue
        target = PRODUCT_FAMILY_TO_TARGET[family]
        if kind in {"board", "capability"}:
            if not isinstance(cell_id, str) or not cell_id.strip():
                errors.append(f"{label}: board/capability sample requires a legal cell_id")
            elif cell_id not in tree.cell_ids or cell_id in RESERVED_INACTIVE_CELL_IDS:
                errors.append(f"{label}: cell_id {cell_id!r} is not an active tree cell")
            if target == "OUT":
                errors.append(f"{label}: outside product_family {family!r} cannot attach to a FAB/cell")
            elif kind == "board" and isinstance(cell_id, str) and cell_id.strip() and cell_id != target:
                errors.append(f"{label}: product_family {family!r} must attach to {target}, got {cell_id!r}")
            elif kind == "capability" and cell_id in {"FAB1", "FAB2"} and cell_id != target:
                errors.append(f"{label}: finished-board capability {family!r} must attach to {target}, got {cell_id!r}")
            if outside_neighbor not in ("", None):
                errors.append(f"{label}: board/capability sample must not use outside_neighbor")
        elif kind == "outside":
            if cell_id not in ("", None):
                errors.append(f"{label}: OUT is not a cell; outside sample cell_id must be empty")
            if target != "OUT":
                errors.append(f"{label}: board product_family {family!r} must use a FAB cell, not outside")
            if outside_neighbor not in tree.outside_neighbors:
                errors.append(f"{label}: outside_neighbor must be one of {list(tree.outside_neighbors)}")
    return _report(errors, sample_count=count, valid_sample_ids=sorted(seen - {""}))


PROCESS_EQUIPMENT_FIELDS = ("process_id", "equipment_id")
# This is a compatibility allow-list, not a defaulting table.  Missing pairs
# remain unmapped and are reported; no EQ6/EQ7 row is ever synthesized.
PROCESS_EQUIPMENT_COMPATIBILITY: dict[str, frozenset[str]] = {
    "P1": frozenset({"EQ1", "EQ7"}),
    "P2": frozenset({"EQ4"}),
    "P3": frozenset({"EQ2"}),
    "P4": frozenset({"EQ3"}),
    "P5": frozenset({"EQ1", "EQ7"}),
    "P6": frozenset({"EQ1"}),
    "P7": frozenset({"EQ3"}),
    "P8": frozenset({"EQ6"}),
    "P9": frozenset({"EQ5"}),
}


def validate_process_equipment_map(records: Iterable[Mapping[str, Any]], tree: Tree) -> ValidationReport:
    """Validate explicit many-to-many process/equipment edges.

    The result intentionally includes unmapped processes.  Unmapped does not
    mean "use EQ6/EQ7"; it stays an explicit gap for later evidence.
    """

    errors: list[str] = []
    pairs: set[tuple[str, str]] = set()
    mapped: dict[str, set[str]] = {process_id: set() for process_id in tree.process_ids}
    count = 0
    for index, record in enumerate(records):
        count += 1
        label = f"map[{index}]"
        if not isinstance(record, Mapping):
            errors.append(f"{label}: must be an object")
            continue
        _strict_record(record, PROCESS_EQUIPMENT_FIELDS, label, errors)
        process_id = _required_record_string(record, "process_id", label, errors)
        equipment_id = _required_record_string(record, "equipment_id", label, errors)
        pair = (process_id, equipment_id)
        if pair in pairs:
            errors.append(f"{label}: duplicate mapping {process_id}->{equipment_id}")
        pairs.add(pair)
        if process_id not in tree.process_ids:
            errors.append(f"{label}: process endpoint must be an active P* cell, got {process_id!r}")
        if equipment_id not in tree.equipment_ids:
            errors.append(f"{label}: equipment endpoint must be an active EQ* cell, got {equipment_id!r}")
        allowed = PROCESS_EQUIPMENT_COMPATIBILITY.get(process_id, frozenset())
        if process_id and equipment_id and equipment_id not in allowed:
            errors.append(f"{label}: incompatible mapping {process_id}->{equipment_id}; no default EQ6/EQ7 fallback")
        if process_id in mapped:
            mapped[process_id].add(equipment_id)
    unmapped = [process_id for process_id in tree.process_ids if not mapped[process_id]]
    return _report(errors, process_count=len(tree.process_ids), mapping_count=count, unmapped_processes=unmapped, mappings=sorted(pairs))


def validate_target_cell(target_cell: Any, tree: Tree) -> None:
    """Validate an individual target without confusing OUT with a cell."""

    if not isinstance(target_cell, str) or not target_cell.strip():
        raise SchemaError("target_cell must be a non-empty string")
    if target_cell in RESERVED_INACTIVE_CELL_IDS:
        raise SchemaError(f"target_cell {target_cell!r} is inactive/reserved")
    if target_cell == "OUT":
        raise SchemaError("OUT is not a target cell; use outside_neighbor")
    if target_cell not in ACTIVE_CELL_ID_SET:
        raise SchemaError(f"target_cell {target_cell!r} is not an active cell")
