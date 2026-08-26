"""8534 scope-freeze template validation; it does not freeze a definition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping


FREEZE_DECISIONS = frozenset({"待人工裁决", "已人工冻结", "拒绝冻结"})
FREEZE_FIELDS = (
    "tariff_year_and_version",
    "full_subheading",
    "direction",
    "quantity_unit",
    "product_scope",
    "trade_mode_allowlist",
    "declarant_scope",
    "origin",
    "company_attribution_method",
    "period",
    "coverage_gaps",
    "area_conversion_anchor",
)
FREEZE_AUDIT_FIELDS = ("freeze_decision", "decided_by", "decided_at", "decision_note")
FREEZE_TEMPLATE_FIELDS = FREEZE_FIELDS + FREEZE_AUDIT_FIELDS
PENDING_UNFROZEN = "待核-口径未冻结"
PENDING_HUMAN = "待人工裁决-口径字段齐全"


@dataclass(frozen=True)
class FreezeCheck:
    status: str
    missing_fields: tuple[str, ...]
    is_frozen: bool
    errors: tuple[str, ...]


def check_8534_freeze(record: Mapping[str, object]) -> FreezeCheck:
    """Check completeness and preserve the human-only freeze decision.

    Any missing frozen item produces ``待核-口径未冻结`` even when a user has
    accidentally filled in ``已人工冻结``.  Complete fields alone remain pending:
    this function never grants the frozen state itself.
    """

    missing = tuple(field for field in FREEZE_FIELDS if not str(record.get(field, "")).strip())
    decision = str(record.get("freeze_decision", "待人工裁决")).strip() or "待人工裁决"
    errors: list[str] = []
    if decision not in FREEZE_DECISIONS:
        errors.append(f"freeze_decision must be one of {sorted(FREEZE_DECISIONS)}")
    if decision == "已人工冻结":
        for field in ("decided_by", "decided_at", "decision_note"):
            if not str(record.get(field, "")).strip():
                errors.append(f"已人工冻结 requires {field}")
        decided_at = str(record.get("decided_at", "")).strip()
        if decided_at:
            try:
                date.fromisoformat(decided_at)
            except ValueError:
                errors.append("decided_at must be an ISO date (YYYY-MM-DD)")
    if missing:
        return FreezeCheck(PENDING_UNFROZEN, missing, False, tuple(errors))
    if errors:
        return FreezeCheck(PENDING_HUMAN, (), False, tuple(errors))
    if decision == "已人工冻结":
        return FreezeCheck("已人工冻结", (), True, ())
    if decision == "拒绝冻结":
        return FreezeCheck("人工拒绝冻结", (), False, ())
    return FreezeCheck(PENDING_HUMAN, (), False, ())


def freeze_csv_header() -> tuple[str, ...]:
    return FREEZE_TEMPLATE_FIELDS
