"""Schema and validation for the DP2 source ledger.

The ledger is intentionally a registry, not an evidence-ranking engine.
Fields such as ``source_role`` describe how a carrier was used for one anchor;
they do not grant any factual or T1 load-bearing status.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping
from urllib.parse import urlparse


SOURCE_ROLES = frozenset({"direct", "secondary", "derived", "unavailable"})
PAYWALL_VALUES = frozenset({"yes", "no", "unknown"})
REVIEW_STATUSES = frozenset({"待核", "已人工复核", "驳回"})
T1_BEARING_DECISIONS = frozenset({"待人工裁决", "人工允许", "人工不允许"})

# Kept as CSV-friendly ordered fields.  The final four are mandatory audit
# fields: no source may silently become an unreviewed canonical input.
LEDGER_FIELDS = (
    "origin_source_id",
    "carrier_url",
    "independence_group",
    "paywall",
    "coverage_scope",
    "source_role",
    "publisher_name",
    "source_tier",
    "recorded_at",
    "recorded_by",
    "review_status",
    "reviewed_at",
    "review_note",
    "t1_bearing_decision",
    "t1_bearing_decided_by",
    "t1_bearing_decided_at",
)


@dataclass(frozen=True)
class LedgerValidation:
    """Validation result; a valid row may still require human review."""

    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def _required(record: Mapping[str, object], field: str, errors: list[str]) -> str:
    value = str(record.get(field, "")).strip()
    if not value:
        errors.append(f"missing required field: {field}")
    return value


def _valid_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate_ledger_record(record: Mapping[str, object]) -> LedgerValidation:
    """Validate one ledger row without assigning its research authority."""

    errors: list[str] = []
    warnings: list[str] = []
    origin_source_id = _required(record, "origin_source_id", errors)
    carrier_url = _required(record, "carrier_url", errors)
    independence_group = _required(record, "independence_group", errors)
    paywall = _required(record, "paywall", errors)
    coverage_scope = _required(record, "coverage_scope", errors)
    source_role = _required(record, "source_role", errors)
    _required(record, "publisher_name", errors)
    _required(record, "source_tier", errors)
    recorded_at = _required(record, "recorded_at", errors)
    _required(record, "recorded_by", errors)
    review_status = _required(record, "review_status", errors)
    t1_decision = _required(record, "t1_bearing_decision", errors)

    parsed = urlparse(carrier_url)
    if carrier_url and (parsed.scheme not in {"http", "https"} or not parsed.netloc):
        errors.append("carrier_url must be an absolute http(s) URL")
    if paywall and paywall not in PAYWALL_VALUES:
        errors.append(f"paywall must be one of {sorted(PAYWALL_VALUES)}")
    if source_role and source_role not in SOURCE_ROLES:
        errors.append(f"source_role must be one of {sorted(SOURCE_ROLES)}")
    if review_status and review_status not in REVIEW_STATUSES:
        errors.append(f"review_status must be one of {sorted(REVIEW_STATUSES)}")
    if t1_decision and t1_decision not in T1_BEARING_DECISIONS:
        errors.append(
            "t1_bearing_decision must be one of "
            f"{sorted(T1_BEARING_DECISIONS)}"
        )
    if recorded_at and not _valid_iso_date(recorded_at):
        errors.append("recorded_at must be an ISO date (YYYY-MM-DD)")
    for field in ("reviewed_at", "t1_bearing_decided_at"):
        value = str(record.get(field, "")).strip()
        if value and not _valid_iso_date(value):
            errors.append(f"{field} must be an ISO date (YYYY-MM-DD) when set")
    if origin_source_id and independence_group and origin_source_id == independence_group:
        warnings.append("origin_source_id equals independence_group; confirm this is intentional")
    if t1_decision == "人工允许":
        if not str(record.get("t1_bearing_decided_by", "")).strip():
            errors.append("人工允许 requires t1_bearing_decided_by")
        if not str(record.get("t1_bearing_decided_at", "")).strip():
            errors.append("人工允许 requires t1_bearing_decided_at")

    return LedgerValidation(not errors, tuple(errors), tuple(warnings))


def ledger_csv_header() -> tuple[str, ...]:
    """Return the canonical header for a DP2 source ledger CSV."""

    return LEDGER_FIELDS
