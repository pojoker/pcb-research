"""Fail-closed input readers shared by every DP2 CLI gate."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Sequence


class InputSchemaError(ValueError):
    """An input cannot be safely interpreted under its declared schema."""


def _format_fields(fields: Iterable[str]) -> str:
    return "[" + ", ".join(repr(field) for field in fields) + "]"


def _header_error(schema_name: str, expected: tuple[str, ...], received: tuple[str, ...]) -> InputSchemaError:
    missing = tuple(field for field in expected if field not in received)
    extra = tuple(field for field in received if field not in expected)
    details: list[str] = []
    if missing:
        details.append(f"missing columns {_format_fields(missing)}")
    if extra:
        details.append(f"extra columns {_format_fields(extra)}")
    if not missing and not extra:
        mismatch = next(
            index for index, (want, got) in enumerate(zip(expected, received), start=1) if want != got
        )
        details.append(
            f"column order differs at position {mismatch}: expected {expected[mismatch - 1]!r}, "
            f"received {received[mismatch - 1]!r}"
        )
    detail = "; ".join(details) or "header values differ"
    return InputSchemaError(
        f"{schema_name} CSV header must exactly match the canonical ordered schema; "
        f"{detail}. Expected {_format_fields(expected)}; received {_format_fields(received)}."
    )


def read_csv_records(path: Path, expected_fields: Sequence[str], schema_name: str) -> list[dict[str, str]]:
    """Read a CSV only when its header and every row match exactly.

    ``csv.DictReader`` intentionally accepts several forms of drift.  DP2
    inputs are audit records, so accepting an unknown column or silently
    shifting values would be worse than rejecting the file.
    """

    expected = tuple(expected_fields)
    try:
        handle = path.open(newline="", encoding="utf-8-sig")
    except OSError as exc:
        raise InputSchemaError(f"cannot read {schema_name} CSV {path}: {exc}") from exc
    try:
        reader = csv.reader(handle, strict=True)
        try:
            received = tuple(next(reader))
        except StopIteration as exc:
            raise InputSchemaError(
                f"{schema_name} CSV {path} is empty; expected canonical header {_format_fields(expected)}."
            ) from exc
        except csv.Error as exc:
            raise InputSchemaError(f"cannot parse {schema_name} CSV {path} header: {exc}") from exc
        if received != expected:
            raise _header_error(schema_name, expected, received)

        records: list[dict[str, str]] = []
        for line_number, values in enumerate(reader, start=2):
            if len(values) != len(expected):
                difference = "extra data fields" if len(values) > len(expected) else "missing data fields"
                raise InputSchemaError(
                    f"{schema_name} CSV {path} row {line_number} has {len(values)} fields; "
                    f"expected exactly {len(expected)} ({difference})."
                )
            records.append(dict(zip(expected, values)))
        return records
    except csv.Error as exc:
        raise InputSchemaError(f"cannot parse {schema_name} CSV {path}: {exc}") from exc
    finally:
        handle.close()


def parse_exact_json_records(payload: Any, expected_fields: Sequence[str], input_name: str) -> list[dict[str, Any]]:
    """Validate an array of JSON objects against one exact field set.

    JSON object order is not semantic, so accepted records are normalized into
    canonical field order after rejecting any missing or unknown fields.
    """

    expected = tuple(expected_fields)
    if not isinstance(payload, list):
        raise InputSchemaError(f"{input_name} JSON must be an array of objects.")
    records: list[dict[str, Any]] = []
    for index, record in enumerate(payload, start=1):
        if not isinstance(record, dict):
            raise InputSchemaError(f"{input_name} JSON record {index} must be an object.")
        received = tuple(record.keys())
        if set(received) != set(expected) or len(received) != len(expected):
            raise _json_record_error(input_name, index, expected, received)
        records.append({field: record[field] for field in expected})
    return records


def _json_record_error(
    input_name: str, index: int, expected: tuple[str, ...], received: tuple[str, ...]
) -> InputSchemaError:
    missing = tuple(field for field in expected if field not in received)
    extra = tuple(field for field in received if field not in expected)
    details: list[str] = []
    if missing:
        details.append(f"missing fields {_format_fields(missing)}")
    if extra:
        details.append(f"unexpected fields {_format_fields(extra)}")
    return InputSchemaError(
        f"{input_name} JSON record {index} does not match the exact schema: {'; '.join(details)}. "
        f"Expected {_format_fields(expected)}; received {_format_fields(received)}."
    )


def load_json(path: Path, input_name: str) -> Any:
    """Load JSON with a user-readable input error instead of a traceback."""

    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as exc:
        raise InputSchemaError(f"cannot read {input_name} JSON {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputSchemaError(
            f"cannot parse {input_name} JSON {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
