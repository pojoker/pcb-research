"""Source adapters for draft discovery only.

The module includes one fixed TWSE listing adapter plus a configurable JSON
adapter.  Neither converts exchange registration or an industry label into a
PCB-universe membership conclusion; every emitted row remains ``待核``.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from .registry import FROZEN_FIELDS


class DraftAdapterError(ValueError):
    pass


TWSE_LISTED_COMPANIES_ENDPOINT = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TWSE_LISTED_COMPANIES_FIELDS = (
    "公司代號",
    "公司名稱",
    "公司簡稱",
    "產業別",
    "出表日期",
)


def _read_payload(config: Mapping[str, Any]) -> Any:
    if config.get("fixture_path"):
        with Path(str(config["fixture_path"])).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    endpoint = config.get("endpoint")
    if not endpoint or not str(endpoint).startswith(("https://", "http://")):
        raise DraftAdapterError("config requires endpoint http(s) or fixture_path")
    request = urllib.request.Request(str(endpoint), method=str(config.get("method", "GET")).upper())
    for key, value in dict(config.get("headers", {})).items():
        request.add_header(str(key), str(value))
    with urllib.request.urlopen(request, timeout=float(config.get("timeout_seconds", 20))) as response:
        return json.loads(response.read().decode("utf-8"))


def _validate_iso_date(value: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise DraftAdapterError("query_date must be ISO YYYY-MM-DD") from exc


def fetch_twse_listed_company_draft(
    *,
    query_date: str,
    fixture_path: str | Path | None = None,
    timeout_seconds: float = 20,
) -> list[dict[str, str]]:
    """Fetch TWSE listed-company records as pending DP1 candidates only.

    The official listing endpoint establishes neither PCB product scope nor a
    research-universe inclusion decision.  ``fixture_path`` is intentionally
    supported for reproducible offline tests; both paths use the same mapping.
    """

    _validate_iso_date(query_date)
    payload = _read_payload(
        {
            "fixture_path": str(fixture_path) if fixture_path is not None else None,
            "endpoint": TWSE_LISTED_COMPANIES_ENDPOINT,
            "timeout_seconds": timeout_seconds,
        }
    )
    if not isinstance(payload, list):
        raise DraftAdapterError("TWSE payload must be a list")

    output: list[dict[str, str]] = []
    seen_codes: set[str] = set()
    for index, source_row in enumerate(payload, start=1):
        if not isinstance(source_row, dict):
            raise DraftAdapterError(f"TWSE record {index} is not an object")
        missing = [
            field
            for field in TWSE_LISTED_COMPANIES_FIELDS
            if not str(source_row.get(field, "")).strip()
        ]
        if missing:
            raise DraftAdapterError(
                f"TWSE record {index}: missing required TWSE fields: {', '.join(missing)}"
            )
        code = str(source_row["公司代號"]).strip()
        if code in seen_codes:
            raise DraftAdapterError(f"TWSE record {index}: duplicate 公司代號 {code!r}")
        seen_codes.add(code)
        legal_name = str(source_row["公司名稱"]).strip()
        short_name = str(source_row["公司簡稱"]).strip()
        industry = str(source_row["產業別"]).strip()
        statement_date = str(source_row["出表日期"]).strip()
        output.append(
            {
                "record_id": f"draft:twse-listed:{code}",
                "entity_type": "issuer",
                "entity_id": f"issuer:TW:{code}",
                "issuer_id": f"issuer:TW:{code}",
                "legal_entity_id": "-",
                "plant_id": "-",
                "group_id": "-",
                "name": short_name,
                "layer": "观察",
                "registration_source": "TWSE 上市公司基本资料 OpenAPI（待核）",
                "source_url": TWSE_LISTED_COMPANIES_ENDPOINT,
                "query_date": query_date,
                "record_status": "待核",
                "double_count_key": f"twse-listing:{code}",
                "double_count_rule": "无",
                "aggregation_policy": "不适用",
                "product_scope": "待核",
                "notes": (
                    "TWSE 官方上市公司基本资料草稿；"
                    f"公司名稱={legal_name}；公司簡稱={short_name}；"
                    f"產業別={industry}；出表日期={statement_date}；"
                    "产业别与上市事实不构成 PCB 纳入裁决，仍须人工复核。"
                ),
            }
        )
    return output


def fetch_draft(config: Mapping[str, Any]) -> list[dict[str, str]]:
    """Map arbitrary JSON records to DP1 candidates; never marks them frozen."""

    payload = _read_payload(config)
    records = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise DraftAdapterError("payload must be a list or an object with records list")
    field_map = dict(config.get("field_map", {}))
    defaults = dict(config.get("defaults", {}))
    id_prefixes = dict(config.get("id_prefixes", {}))
    output: list[dict[str, str]] = []
    for index, source_row in enumerate(records, start=1):
        if not isinstance(source_row, dict):
            raise DraftAdapterError(f"record {index} is not an object")
        row: dict[str, str] = {}
        for field in FROZEN_FIELDS:
            source_key = field_map.get(field, field)
            value = source_row.get(source_key, defaults.get(field, "-"))
            row[field] = str(value).strip() if value is not None else "-"
            if field in {"entity_id", "issuer_id", "legal_entity_id", "plant_id", "group_id"} and row[field] != "-":
                namespace = field.removesuffix("_id")
                if not row[field].startswith(namespace + ":"):
                    prefix = str(id_prefixes.get(field, ""))
                    if prefix:
                        row[field] = prefix + row[field]
        row["record_id"] = row["record_id"] if row["record_id"] != "-" else f"draft:{index}"
        row["record_status"] = "待核"
        row["notes"] = f"网络/外部适配草稿；未核验，禁止视为交易所或协会结论。原始序号={index}。"
        output.append(row)
    return output
