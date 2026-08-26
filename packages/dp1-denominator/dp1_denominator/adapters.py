"""Configurable source adapters for draft discovery only.

There is intentionally no built-in exchange/association parser or hard-coded
membership conclusion.  A config names the endpoint and supplies a mapping;
the adapter emits candidate rows marked ``待核`` for human review.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from .registry import FROZEN_FIELDS


class DraftAdapterError(ValueError):
    pass


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
