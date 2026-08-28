"""Explicit 30-cell coverage rendering for DP3."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .validation import ValidationReport, _report, _required_record_string, _strict_record
from .schema import ACTIVE_CELL_ID_SET, RESERVED_INACTIVE_CELL_IDS, Tree


ATTACHMENT_FIELDS = ("attachment_id", "cell_id")
COVERAGE_FIELDS = ("cell_id", "status")
COVERAGE_STATUSES = frozenset({"covered", "empty", "待核"})


def _validate_attachment_rows(attachments: Iterable[Mapping[str, Any]], tree: Tree) -> tuple[list[str], dict[str, list[str]]]:
    errors: list[str] = []
    by_cell: dict[str, list[str]] = {cell_id: [] for cell_id in tree.cell_ids}
    seen: set[str] = set()
    for index, record in enumerate(attachments):
        label = f"attachments[{index}]"
        if not isinstance(record, Mapping):
            errors.append(f"{label}: must be an object")
            continue
        _strict_record(record, ATTACHMENT_FIELDS, label, errors)
        attachment_id = _required_record_string(record, "attachment_id", label, errors)
        cell_id = _required_record_string(record, "cell_id", label, errors)
        if attachment_id in seen:
            errors.append(f"{label}: duplicate attachment_id {attachment_id!r}")
        seen.add(attachment_id)
        if cell_id not in ACTIVE_CELL_ID_SET or cell_id in RESERVED_INACTIVE_CELL_IDS:
            errors.append(f"{label}: cell_id {cell_id!r} is not an active cell; OUT is not a cell")
        elif cell_id in by_cell:
            by_cell[cell_id].append(attachment_id)
    return errors, by_cell


def _validate_coverage_rows(coverage: Iterable[Mapping[str, Any]], tree: Tree) -> tuple[list[str], dict[str, str]]:
    errors: list[str] = []
    by_cell: dict[str, str] = {}
    for index, record in enumerate(coverage):
        label = f"coverage[{index}]"
        if not isinstance(record, Mapping):
            errors.append(f"{label}: must be an object")
            continue
        _strict_record(record, COVERAGE_FIELDS, label, errors)
        cell_id = _required_record_string(record, "cell_id", label, errors)
        status = _required_record_string(record, "status", label, errors)
        if cell_id in by_cell:
            errors.append(f"{label}: duplicate coverage cell_id {cell_id!r}")
        by_cell[cell_id] = status
        if cell_id not in ACTIVE_CELL_ID_SET:
            errors.append(f"{label}: coverage cell_id {cell_id!r} is not an active cell")
        if status not in COVERAGE_STATUSES:
            errors.append(f"{label}: status must be one of {sorted(COVERAGE_STATUSES)}")
    return errors, by_cell


def render_coverage(
    tree: Tree,
    attachments: Iterable[Mapping[str, Any]],
    coverage: Iterable[Mapping[str, Any]],
) -> tuple[ValidationReport, list[dict[str, Any]]]:
    """Return every active cell, including explicit empty-space rows."""

    attachment_errors, by_cell = _validate_attachment_rows(attachments, tree)
    coverage_errors, statuses = _validate_coverage_rows(coverage, tree)
    errors = attachment_errors + coverage_errors
    rows: list[dict[str, Any]] = []
    for cell in tree.cells:
        status = statuses.get(cell.cell_id)
        if status is None:
            status = "covered" if by_cell[cell.cell_id] else "empty"
        empty_space = status == "empty"
        rows.append(
            {
                "cell_id": cell.cell_id,
                "name": cell.name,
                "axis": cell.axis,
                "stage": cell.stage,
                "flow_id": cell.flow_id,
                "attachment_ids": list(by_cell[cell.cell_id]),
                "coverage_status": status,
                "empty_space": empty_space,
                "space": "空格" if empty_space else "",
            }
        )
    report = _report(errors, cell_count=len(rows), empty_cell_ids=[row["cell_id"] for row in rows if row["empty_space"]])
    return report, rows
