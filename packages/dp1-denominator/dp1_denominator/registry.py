"""Mechanical DP1 checks.

This module deliberately does not decide whether a company belongs in the
research universe.  It validates the shape and provenance of a candidate
registry, records duplicate candidates, and creates review rows for snapshot
changes.  All source-derived input is expected to remain ``待核`` until a
human decision is recorded.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


FROZEN_FIELDS = (
    "record_id",
    "entity_type",
    "entity_id",
    "issuer_id",
    "legal_entity_id",
    "plant_id",
    "group_id",
    "name",
    "layer",
    "registration_source",
    "source_url",
    "query_date",
    "record_status",
    "double_count_key",
    "double_count_rule",
    "aggregation_policy",
    "product_scope",
    "notes",
)

INCLUSION_DECISION_FIELDS = (
    "decision_id",
    "decision_type",
    "action",
    "entity_type",
    "entity_id",
    "issuer_id",
    "legal_entity_id",
    "plant_id",
    "group_id",
    "name",
    "layer",
    "registration_source",
    "inclusion_reason",
    "exclusion_reason",
    "evidence_anchor",
    "source_url",
    "query_date",
    "decision_owner",
    "decision_date",
    "decision_status",
    "double_count_key",
    "notes",
)

ENTITY_TYPES = {"issuer", "legal_entity", "plant", "group"}
LAYERS = {"L1-A", "L1-B", "L1-C", "L2", "L3", "L4", "观察"}
RECORD_STATUSES = {"待核", "已冻结"}
DECISION_STATUSES = {"待核", "已裁决"}
DOUBLE_COUNT_RULES = {"母子双上市", "同厂多法人", "集团合并交叉校验", "无"}
AGGREGATION_POLICIES = {"分列-禁止加总", "不适用"}
DECISION_TYPES = {
    "manual_include",
    "manual_exclude",
    "snapshot_add",
    "snapshot_remove",
    "duplicate_candidate",
}
DECISION_ACTIONS = {"include", "exclude", "triage"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^(issuer|legal_entity|plant|group):[A-Za-z0-9][A-Za-z0-9._-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)?$")
URL_RE = re.compile(r"^https?://[^\s]+$")


@dataclass
class ValidationReport:
    """Structured validation result suitable for CLI and tests."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def extend(self, other: "ValidationReport") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def load_csv(path: str | Path, expected_fields: Sequence[str]) -> list[dict[str, str]]:
    """Load a UTF-8 CSV and fail closed on schema drift."""

    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = tuple(reader.fieldnames or ())
        expected = tuple(expected_fields)
        if actual != expected:
            raise ValueError(
                f"{path}: schema mismatch; expected {expected}, got {actual}"
            )
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"{path}:{line_number}: extra CSV fields")
            if all(value in (None, "") for value in row.values()):
                raise ValueError(f"{path}:{line_number}: blank row")
            rows.append({key: (value or "").strip() for key, value in row.items()})
    return rows


def write_csv(path: str | Path, fields: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    """Write a deterministic UTF-8 CSV with the package schema."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "-") for field in fields})


def _check_schema(rows: Sequence[Mapping[str, str]], fields: Sequence[str], report: ValidationReport) -> None:
    for index, row in enumerate(rows, start=2):
        missing = [field for field in fields if field not in row]
        if missing:
            report.error(f"row {index}: missing fields: {', '.join(missing)}")
        blank = [field for field in fields if row.get(field, "") == ""]
        if blank:
            report.error(f"row {index}: blank fields must use '-' explicitly: {', '.join(blank)}")


def _valid_date(value: str, *, allow_dash: bool = False) -> bool:
    if allow_dash and value == "-":
        return True
    if not DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _valid_url(value: str, *, allow_dash: bool = False) -> bool:
    return (allow_dash and value == "-") or bool(URL_RE.fullmatch(value))


def _check_id(value: str, expected_type: str, row_number: int, field: str, report: ValidationReport, *, required: bool = False) -> None:
    if value == "-":
        if required:
            report.error(f"row {row_number}: {field} is required for {expected_type}")
        return
    if not ID_RE.fullmatch(value):
        report.error(f"row {row_number}: {field} has invalid ID {value!r}")
        return
    if not value.startswith(expected_type + ":"):
        report.error(f"row {row_number}: {field} must use {expected_type}: namespace")


def _validate_common_identity(row: Mapping[str, str], row_number: int, report: ValidationReport) -> None:
    entity_type = row.get("entity_type", "")
    if entity_type not in ENTITY_TYPES:
        report.error(f"row {row_number}: invalid entity_type {entity_type!r}")
        return
    _check_id(row.get("entity_id", ""), entity_type, row_number, "entity_id", report, required=True)
    for field, expected_type in (
        ("issuer_id", "issuer"),
        ("legal_entity_id", "legal_entity"),
        ("plant_id", "plant"),
        ("group_id", "group"),
    ):
        _check_id(row.get(field, ""), expected_type, row_number, field, report)
    if row.get(f"{entity_type}_id") != row.get("entity_id"):
        report.error(f"row {row_number}: entity_id must equal {entity_type}_id")

    layer = row.get("layer", "")
    if layer not in LAYERS:
        report.error(f"row {row_number}: invalid layer {layer!r}")
    if not row.get("name", "") or row.get("name") == "-":
        report.error(f"row {row_number}: name is required")
    if not row.get("registration_source", "") or row.get("registration_source") == "-":
        report.error(f"row {row_number}: registration_source is required")
    if not _valid_url(row.get("source_url", "")):
        report.error(f"row {row_number}: source_url must be an http(s) URL")
    if not _valid_date(row.get("query_date", "")):
        report.error(f"row {row_number}: query_date must be ISO YYYY-MM-DD")


def find_duplicate_candidates(rows: Sequence[Mapping[str, str]]) -> list[dict[str, object]]:
    """Find intentional-review candidates without declaring them duplicates.

    A repeated ``double_count_key`` is the explicit mother/child or group
    overlap signal.  A repeated plant ID is the same-plant multi-legal-entity
    signal.  The caller must route these candidates through a human triage
    row; the function never removes or merges records.
    """

    by_double_key: dict[str, list[str]] = defaultdict(list)
    by_plant: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        entity_id = row.get("entity_id", "-")
        key = row.get("double_count_key", "-")
        plant_id = row.get("plant_id", "-")
        if key not in {"", "-"}:
            by_double_key[key].append(entity_id)
        if plant_id not in {"", "-"}:
            by_plant[plant_id].append(entity_id)

    candidates: list[dict[str, object]] = []
    for key, entity_ids in sorted(by_double_key.items()):
        if len(entity_ids) > 1:
            candidates.append({"candidate_type": "double_count_key", "candidate_key": key, "entity_ids": sorted(entity_ids)})
    for key, entity_ids in sorted(by_plant.items()):
        if len(entity_ids) > 1:
            candidates.append({"candidate_type": "plant_id", "candidate_key": key, "entity_ids": sorted(entity_ids)})
    return candidates


def _matching_frozen_decision_errors(
    frozen: Mapping[str, str],
    decisions: Sequence[Mapping[str, str]],
    *,
    row_number: int,
) -> list[str]:
    """Return fail-closed errors for a row represented as ``已冻结``.

    A mechanical record cannot freeze itself.  The matching manual decision is
    the audit authority; the frozen row supplies the source and duplicate-key
    values that decision must preserve.
    """

    entity_id = frozen.get("entity_id", "-")
    candidates = [
        decision
        for decision in decisions
        if decision.get("entity_id") == entity_id
        and decision.get("decision_type") == "manual_include"
        and decision.get("action") == "include"
        and decision.get("decision_status") == "已裁决"
    ]
    if not candidates:
        return [
            f"row {row_number}: record_status=已冻结 requires a matching "
            "manual_include/include/已裁决 decision"
        ]

    errors: list[str] = []
    for decision in candidates:
        decision_id = decision.get("decision_id", "-")
        prefix = f"row {row_number}: frozen decision {decision_id}"
        candidate_errors: list[str] = []
        if decision.get("decision_owner") in {"", "-", "待定"}:
            candidate_errors.append(f"{prefix}: decision_owner must name the human reviewer")
        if not _valid_date(decision.get("decision_date", "")):
            candidate_errors.append(f"{prefix}: decision_date must be an ISO review date")
        evidence_anchor = decision.get("evidence_anchor", "")
        if evidence_anchor in {"", "-"} or "://" not in evidence_anchor:
            candidate_errors.append(f"{prefix}: evidence_anchor must be a traceable locator")
        source_url = decision.get("source_url", "")
        if not _valid_url(source_url) or source_url != frozen.get("source_url"):
            candidate_errors.append(f"{prefix}: source_url must be valid and match the frozen row")
        if decision.get("double_count_key") != frozen.get("double_count_key"):
            candidate_errors.append(f"{prefix}: double_count_key must match the frozen row")
        if not candidate_errors:
            return []
        errors.extend(candidate_errors)

    return errors


def validate_frozen(
    rows: Sequence[Mapping[str, str]],
    decisions: Sequence[Mapping[str, str]] = (),
) -> ValidationReport:
    report = ValidationReport()
    _check_schema(rows, FROZEN_FIELDS, report)
    seen_record_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        record_id = row.get("record_id", "")
        if not record_id or record_id == "-":
            report.error(f"row {row_number}: record_id is required")
        elif record_id in seen_record_ids:
            report.error(f"row {row_number}: duplicate record_id {record_id!r}")
        seen_record_ids.add(record_id)
        _validate_common_identity(row, row_number, report)
        if row.get("record_status") not in RECORD_STATUSES:
            report.error(f"row {row_number}: invalid record_status {row.get('record_status')!r}")
        if row.get("double_count_rule") not in DOUBLE_COUNT_RULES:
            report.error(f"row {row_number}: invalid double_count_rule")
        if row.get("aggregation_policy") not in AGGREGATION_POLICIES:
            report.error(f"row {row_number}: invalid aggregation_policy")
        if not row.get("double_count_key") or row.get("double_count_key") == "-":
            report.error(f"row {row_number}: double_count_key is required; use a unique key when not a candidate")
        if not row.get("product_scope") or row.get("product_scope") == "-":
            report.error(f"row {row_number}: product_scope is required")
        if not row.get("notes") or row.get("notes") == "-":
            report.error(f"row {row_number}: notes must state pending/freeze context")
        if row.get("record_status") == "已冻结":
            report.errors.extend(
                _matching_frozen_decision_errors(
                    row,
                    decisions,
                    row_number=row_number,
                )
            )

    candidates = find_duplicate_candidates(rows)
    for candidate in candidates:
        report.warning(
            "duplicate candidate requires triage: "
            f"{candidate['candidate_type']}={candidate['candidate_key']} "
            f"({', '.join(candidate['entity_ids'])})"
        )
    return report


def validate_inclusion_decisions(
    rows: Sequence[Mapping[str, str]], frozen_rows: Sequence[Mapping[str, str]] | None = None
) -> ValidationReport:
    report = ValidationReport()
    _check_schema(rows, INCLUSION_DECISION_FIELDS, report)
    seen_decision_ids: set[str] = set()
    frozen_by_entity = {row.get("entity_id"): row for row in (frozen_rows or [])}
    for row_number, row in enumerate(rows, start=2):
        decision_id = row.get("decision_id", "")
        if not decision_id or decision_id == "-":
            report.error(f"row {row_number}: decision_id is required")
        elif decision_id in seen_decision_ids:
            report.error(f"row {row_number}: duplicate decision_id {decision_id!r}")
        seen_decision_ids.add(decision_id)
        _validate_common_identity(row, row_number, report)
        if row.get("decision_type") not in DECISION_TYPES:
            report.error(f"row {row_number}: invalid decision_type")
        if row.get("action") not in DECISION_ACTIONS:
            report.error(f"row {row_number}: invalid action")
        if row.get("decision_status") not in DECISION_STATUSES:
            report.error(f"row {row_number}: invalid decision_status")
        if not _valid_date(row.get("query_date", "")):
            report.error(f"row {row_number}: query_date must be ISO YYYY-MM-DD")
        if not _valid_date(row.get("decision_date", ""), allow_dash=True):
            report.error(f"row {row_number}: decision_date must be ISO YYYY-MM-DD or '-'")
        if row.get("decision_status") == "已裁决":
            if row.get("decision_owner") in {"", "-", "待定"} or row.get("decision_date") == "-":
                report.error(f"row {row_number}: a decided row needs owner and decision_date")
        elif not row.get("decision_owner") or row.get("decision_owner") == "-":
            report.error(f"row {row_number}: pending row needs decision_owner='待定' or named reviewer")
        if not _valid_url(row.get("source_url", ""), allow_dash=True):
            report.error(f"row {row_number}: source_url must be an http(s) URL or '-' ")
        if not row.get("evidence_anchor"):
            report.error(f"row {row_number}: evidence_anchor is required; use '-' only when explicitly unavailable")
        if row.get("decision_type") == "duplicate_candidate" and row.get("action") != "triage":
            report.error(f"row {row_number}: duplicate_candidate must use action=triage")
        if row.get("decision_type") in {"snapshot_add", "snapshot_remove"} and row.get("action") != "triage":
            report.error(f"row {row_number}: snapshot changes must use action=triage")
        frozen = frozen_by_entity.get(row.get("entity_id"))
        if frozen and row.get("double_count_key") != frozen.get("double_count_key"):
            report.error(f"row {row_number}: decision double_count_key disagrees with frozen row")
    if frozen_rows:
        for frozen_row_number, frozen in enumerate(frozen_rows, start=2):
            if frozen.get("record_status") == "已冻结":
                report.errors.extend(
                    _matching_frozen_decision_errors(
                        frozen,
                        rows,
                        row_number=frozen_row_number,
                    )
                )
        duplicate_candidates = find_duplicate_candidates(frozen_rows)
        triaged_pairs = {
            (row.get("double_count_key"), row.get("entity_id"))
            for row in rows
            if row.get("decision_type") == "duplicate_candidate"
        }
        for candidate in duplicate_candidates:
            if candidate["candidate_type"] != "double_count_key":
                continue
            key = str(candidate["candidate_key"])
            for entity_id in candidate["entity_ids"]:
                if (key, entity_id) not in triaged_pairs:
                    report.error(
                        "missing duplicate_candidate triage for "
                        f"{key}/{entity_id}"
                    )
    return report


def _canonical_rows(rows: Sequence[Mapping[str, str]]) -> list[str]:
    return sorted(
        "\x1f".join(str(row.get(field, "-")) for field in FROZEN_FIELDS)
        for row in rows
    )


def _row_identity(row: Mapping[str, str]) -> str:
    return row.get("entity_id", "-")


def build_snapshot_metadata(
    rows: Sequence[Mapping[str, str]],
    *,
    source_name: str,
    source_kind: str,
    source_url: str,
    query_date: str,
    adapter_name: str,
    input_path: str | Path | None = None,
    freeze_status: str = "待核",
) -> dict[str, object]:
    """Return auditable metadata; does not claim that a source was verified."""

    if not _valid_date(query_date):
        raise ValueError("query_date must be ISO YYYY-MM-DD")
    if not _valid_url(source_url):
        raise ValueError("source_url must be an http(s) URL")
    if freeze_status != "待核":
        raise ValueError("mechanical snapshots remain 待核; --freeze-status cannot freeze a snapshot")
    canonical = "\n".join(_canonical_rows(rows)).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    layer_counts = Counter(row.get("layer", "-") for row in rows)
    return {
        "snapshot_id": f"snap:{query_date}:{digest[:16]}",
        "source_name": source_name,
        "source_kind": source_kind,
        "source_url": source_url,
        "query_date": query_date,
        "adapter_name": adapter_name,
        "input_path": str(input_path) if input_path is not None else "-",
        "input_sha256": digest,
        "record_count": len(rows),
        "layer_counts": dict(sorted(layer_counts.items())),
        "freeze_status": "待核",
        "verification_note": "机械快照元数据；来源结论与纳入裁决仍待核。",
    }


def _triage_row(row: Mapping[str, str], *, change: str, snapshot_id: str, query_date: str) -> dict[str, str]:
    entity_id = row.get("entity_id", "-")
    decision_type = "snapshot_add" if change == "add" else "snapshot_remove"
    return {
        "decision_id": f"triage:{snapshot_id}:{change}:{entity_id}",
        "decision_type": decision_type,
        "action": "triage",
        "entity_type": row.get("entity_type", "-"),
        "entity_id": entity_id,
        "issuer_id": row.get("issuer_id", "-"),
        "legal_entity_id": row.get("legal_entity_id", "-"),
        "plant_id": row.get("plant_id", "-"),
        "group_id": row.get("group_id", "-"),
        "name": row.get("name", "-"),
        "layer": row.get("layer", "-"),
        "registration_source": row.get("registration_source", "-"),
        "inclusion_reason": f"snapshot diff {change}; 人工复核前不得冻结",
        "exclusion_reason": "-",
        "evidence_anchor": f"snapshot://{snapshot_id}",
        "source_url": row.get("source_url", "-"),
        "query_date": query_date,
        "decision_owner": "待定",
        "decision_date": "-",
        "decision_status": "待核",
        "double_count_key": row.get("double_count_key", "-"),
        "notes": "自动生成 triage；不代表纳入/移出裁决。",
    }


def diff_snapshots(
    before_rows: Sequence[Mapping[str, str]],
    after_rows: Sequence[Mapping[str, str]],
    *,
    before_snapshot_id: str,
    after_snapshot_id: str,
    query_date: str,
    existing_decisions: Sequence[Mapping[str, str]] = (),
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Compare rows by entity_id and return (diff_rows, generated_triage_rows)."""

    if not _valid_date(query_date):
        raise ValueError("query_date must be ISO YYYY-MM-DD")
    before = {_row_identity(row): row for row in before_rows}
    after = {_row_identity(row): row for row in after_rows}
    diff_rows: list[dict[str, str]] = []
    triage_rows: list[dict[str, str]] = []
    for entity_id in sorted(set(after) - set(before)):
        row = after[entity_id]
        diff_rows.append({"change": "add", "entity_id": entity_id, "before_snapshot_id": before_snapshot_id, "after_snapshot_id": after_snapshot_id, "name": row.get("name", "-"), "triage_required": "yes"})
        triage_rows.append(_triage_row(row, change="add", snapshot_id=after_snapshot_id, query_date=query_date))
    for entity_id in sorted(set(before) - set(after)):
        row = before[entity_id]
        diff_rows.append({"change": "remove", "entity_id": entity_id, "before_snapshot_id": before_snapshot_id, "after_snapshot_id": after_snapshot_id, "name": row.get("name", "-"), "triage_required": "yes"})
        triage_rows.append(_triage_row(row, change="remove", snapshot_id=after_snapshot_id, query_date=query_date))
    existing_ids = {row.get("decision_id") for row in existing_decisions}
    triage_rows = [row for row in triage_rows if row["decision_id"] not in existing_ids]
    return diff_rows, triage_rows


def merge_decisions(
    existing: Sequence[Mapping[str, str]], generated_triage: Sequence[Mapping[str, str]]
) -> list[dict[str, str]]:
    """Stable, de-duplicated decision ledger output."""

    merged: dict[str, Mapping[str, str]] = {}
    for row in [*existing, *generated_triage]:
        merged[row.get("decision_id", "-")] = row
    return [dict(merged[key]) for key in sorted(merged)]


def report_text(report: ValidationReport) -> str:
    lines = ["OK" if report.ok else "FAIL"]
    lines.extend(f"ERROR: {message}" for message in report.errors)
    lines.extend(f"WARNING: {message}" for message in report.warnings)
    return "\n".join(lines)
