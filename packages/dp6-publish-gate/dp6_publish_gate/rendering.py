"""Publication-safe renderers: status is always emitted verbatim."""

from __future__ import annotations

import json
import copy
from typing import Any


def _publication_safe(report: dict[str, Any]) -> dict[str, Any]:
    safe = copy.deepcopy(report)
    for row in safe.get("rows", []):
        if isinstance(row, dict):
            row["publishable"] = row.get("status") == "pass"
    safe["publishable"] = (
        safe.get("overall_status") == "pass"
        and all(isinstance(row, dict) and row.get("status") == "pass" for row in safe.get("rows", []))
    )
    return safe


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(_publication_safe(report), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)


def render_text(report: dict[str, Any]) -> str:
    report = _publication_safe(report)
    lines = [
        f"overall_status={report['overall_status']} publishable={str(report['publishable']).lower()}"
    ]
    for row in report["rows"]:
        reasons = ",".join(row["reason_codes"]) or "none"
        comparison = row.get("comparison_value")
        tolerance = row.get("tolerance")
        lines.append(
            "\t".join([
                row["id"],
                f"status={row['status']}",
                f"publishable={str(row['publishable']).lower()}",
                f"reason_codes={reasons}",
                f"comparison_value={comparison if comparison is not None else ''}",
                f"tolerance={tolerance if tolerance is not None else ''}",
                f"decision_date={row.get('decision_date') or ''}",
            ])
        )
    return "\n".join(lines) + "\n"
