"""Strict, JSON-compatible schemas for the DP3 tree contract.

The repository's ``tree.yaml`` is deliberately JSON-compatible YAML.  The
standard library can therefore parse the canonical file without silently
accepting a different YAML dialect or adding a PyYAML dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .errors import SchemaError


ROOT_FIELDS = (
    "schema_version",
    "status",
    "root_question",
    "source_spec",
    "cells",
    "route_axes",
    "demand_scenarios",
    "outside_neighbor_policy",
    "outside_neighbors",
)
CELL_FIELDS = ("cell_id", "system", "axis", "name", "stage", "flow_id", "boundary")
AXIS_FIELDS = ("axis_id", "name", "values")

ACTIVE_CELL_IDS = (
    "FAB1",
    "FAB2",
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "MSK",
    "M7",
    "FLX",
    "M9",
    "PM1",
    "PM2",
    "PM3",
    "P1",
    "P2",
    "P3",
    "P4",
    "P5",
    "P6",
    "P7",
    "P8",
    "P9",
    "EQ1",
    "EQ2",
    "EQ3",
    "EQ4",
    "EQ5",
    "EQ6",
    "EQ7",
)
ACTIVE_CELL_ID_SET = frozenset(ACTIVE_CELL_IDS)
RESERVED_INACTIVE_CELL_IDS = frozenset({"M6", "M8"})
EXPECTED_AXIS_IDS = tuple("ABCDEF")
EXPECTED_OUTSIDE_NEIGHBORS = (
    "PCBA",
    "SMT",
    "EMS",
    "设计",
    "锂电铜箔",
    "整机",
)
STAGES = frozenset(
    {"finished_board", "board_input", "base_material", "board_surface", "consumable", "process", "equipment"}
)
AXES = frozenset({"finished_board", "material", "process_material", "process", "equipment"})
FLOW_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Cell:
    cell_id: str
    system: str
    axis: str
    name: str
    stage: str
    flow_id: str
    boundary: str


@dataclass(frozen=True)
class RouteAxis:
    axis_id: str
    name: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class Tree:
    schema_version: int
    status: str
    root_question: str
    source_spec: str
    cells: tuple[Cell, ...]
    route_axes: tuple[RouteAxis, ...]
    demand_scenarios: tuple[str, ...]
    outside_neighbor_policy: str
    outside_neighbors: tuple[str, ...]

    @property
    def cell_ids(self) -> frozenset[str]:
        return frozenset(cell.cell_id for cell in self.cells)

    @property
    def process_ids(self) -> tuple[str, ...]:
        return tuple(cell.cell_id for cell in self.cells if cell.axis == "process")

    @property
    def equipment_ids(self) -> tuple[str, ...]:
        return tuple(cell.cell_id for cell in self.cells if cell.axis == "equipment")

    def cell(self, cell_id: str) -> Cell | None:
        return next((cell for cell in self.cells if cell.cell_id == cell_id), None)


def _exact_keys(record: Mapping[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in record]
    extra = sorted(set(record).difference(fields))
    if missing:
        raise SchemaError(f"missing {label} fields: {', '.join(missing)}")
    if extra:
        raise SchemaError(f"unknown {label} fields: {', '.join(extra)}")


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise SchemaError(f"{field} must be a non-empty list of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise SchemaError(f"{field}[{index}] must be a non-empty string")
        result.append(item.strip())
    return tuple(result)


def parse_tree(value: Any) -> Tree:
    """Parse only the exact tree schema; semantic gates live in validation.py."""

    if not isinstance(value, Mapping):
        raise SchemaError("tree top-level value must be an object")
    _exact_keys(value, ROOT_FIELDS, "tree")
    if not isinstance(value["schema_version"], int) or isinstance(value["schema_version"], bool):
        raise SchemaError("schema_version must be an integer")
    if not isinstance(value["cells"], list):
        raise SchemaError("cells must be a list")
    if not isinstance(value["route_axes"], list):
        raise SchemaError("route_axes must be a list")
    if not isinstance(value["demand_scenarios"], list):
        raise SchemaError("demand_scenarios must be a list")
    if not isinstance(value["outside_neighbors"], list):
        raise SchemaError("outside_neighbors must be a list")

    cells: list[Cell] = []
    for index, raw in enumerate(value["cells"]):
        if not isinstance(raw, Mapping):
            raise SchemaError(f"cells[{index}] must be an object")
        _exact_keys(raw, CELL_FIELDS, f"cells[{index}]")
        cells.append(
            Cell(
                cell_id=_string(raw["cell_id"], f"cells[{index}].cell_id"),
                system=_string(raw["system"], f"cells[{index}].system"),
                axis=_string(raw["axis"], f"cells[{index}].axis"),
                name=_string(raw["name"], f"cells[{index}].name"),
                stage=_string(raw["stage"], f"cells[{index}].stage"),
                flow_id=_string(raw["flow_id"], f"cells[{index}].flow_id"),
                boundary=_string(raw["boundary"], f"cells[{index}].boundary"),
            )
        )

    axes: list[RouteAxis] = []
    for index, raw in enumerate(value["route_axes"]):
        if not isinstance(raw, Mapping):
            raise SchemaError(f"route_axes[{index}] must be an object")
        _exact_keys(raw, AXIS_FIELDS, f"route_axes[{index}]")
        axes.append(
            RouteAxis(
                axis_id=_string(raw["axis_id"], f"route_axes[{index}].axis_id"),
                name=_string(raw["name"], f"route_axes[{index}].name"),
                values=_string_list(raw["values"], f"route_axes[{index}].values"),
            )
        )

    return Tree(
        schema_version=value["schema_version"],
        status=_string(value["status"], "status"),
        root_question=_string(value["root_question"], "root_question"),
        source_spec=_string(value["source_spec"], "source_spec"),
        cells=tuple(cells),
        route_axes=tuple(axes),
        demand_scenarios=_string_list(value["demand_scenarios"], "demand_scenarios"),
        outside_neighbor_policy=_string(value["outside_neighbor_policy"], "outside_neighbor_policy"),
        outside_neighbors=_string_list(value["outside_neighbors"], "outside_neighbors"),
    )


def load_tree(path: str | Path) -> Tree:
    """Load the repository JSON-compatible YAML tree using Python stdlib only."""

    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SchemaError(f"tree file not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise SchemaError(
            f"{source}: invalid JSON-compatible YAML at line {exc.lineno}, column {exc.colno}"
        ) from exc
    return parse_tree(payload)
