#!/usr/bin/env python3
"""Fail-closed checks for pending research candidates."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "dp1-denominator"))
sys.path.insert(0, str(ROOT / "packages" / "dp2-sources"))

from dp1_denominator.registry import FROZEN_FIELDS, load_csv, validate_frozen  # noqa: E402
from dp2_sources.input_schema import read_csv_records  # noqa: E402
from dp2_sources.schema import LEDGER_FIELDS, validate_ledger_record  # noqa: E402


HERE = Path(__file__).resolve().parent
SNAPSHOTS = ROOT / "data" / "snapshots" / "2026-08-28"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    denominator = load_csv(HERE / "denominator_candidates.csv", FROZEN_FIELDS)
    denominator_report = validate_frozen(denominator)
    require(denominator_report.ok, f"DP1 candidate errors: {denominator_report.errors}")
    require(len(denominator) == 2017, "expected 2,017 denominator candidates")
    require(all(row["record_status"] == "待核" for row in denominator), "denominator row escaped pending")
    denominator_l1bc = load_csv(HERE / "denominator_l1bc_candidates.csv", FROZEN_FIELDS)
    denominator_l1bc_report = validate_frozen(denominator_l1bc)
    require(denominator_l1bc_report.ok, f"DP1 L1-B/C candidate errors: {denominator_l1bc_report.errors}")
    require(len(denominator_l1bc) == 19, "expected 19 L1-B/C denominator candidates")
    require(all(row["record_status"] == "待核" for row in denominator_l1bc), "L1-B/C denominator row escaped pending")

    sources = read_csv_records(HERE / "t1_source_candidates.csv", LEDGER_FIELDS, "T1 source candidate")
    source_reports = [validate_ledger_record(row) for row in sources]
    require(len(sources) == 12, "expected 12 T1 source candidates")
    require(all(report.valid for report in source_reports), "invalid DP2 source candidate")
    require(all(row["t1_bearing_decision"] == "待人工裁决" for row in sources), "T1 source escaped human gate")

    company = json.loads((HERE / "company_points_edges.json").read_text(encoding="utf-8"))
    capacity = json.loads((HERE / "capacity_metrics.json").read_text(encoding="utf-8"))
    require(len(company["points"]) == 11, "expected 11 point candidates")
    require(not company["manufacturing_edges"], "manufacturing edge exists without five-tuple review")
    require(all(point["review_status"] == "pending" for point in company["points"]), "point escaped pending")
    require(all(point["t1_level"] == "T1_candidate" for point in company["points"]), "point self-approved T1")
    require(all(metric["status"] == "pending" for metric in capacity["metrics"]), "capacity metric escaped pending")
    require(len(capacity["metrics"]) == 9, "expected 9 capacity metric candidates")

    capacity_by_id = {row["metric_id"]: row for row in capacity["metrics"]}
    for metric_id in ("cap_yidun_approved_existing_20241031", "cap_yidun_built_existing_20241031"):
        require(capacity_by_id[metric_id]["unit"] == "square_meter_per_year", f"{metric_id} lost annual rate dimension")
    xingsen_quote = capacity_by_id["cap_xingsen_fcbga_built_20221231"]["anchor"]["quote"]
    require("6,000平方米/月" in xingsen_quote, "Xingsen capacity value lacks a matched quote")

    with (HERE / "subject_identity_map.csv").open(encoding="utf-8", newline="") as handle:
        identity_rows = list(csv.DictReader(handle))
    mapped_dp5 = {row["dp5_subject_id"] for row in identity_rows if row["dp5_subject_id"]}
    mapped_capacity = {row["capacity_subject_id"] for row in identity_rows if row["capacity_subject_id"]}
    dp5_issuers = {row["subject_id"] for row in company["subject_mappings"] if row["subject_type"] == "issuer"}
    capacity_subjects = {row["subject_id"] for row in capacity["subject_mappings"]}
    require(dp5_issuers <= mapped_dp5, f"unmapped DP5 issuers: {sorted(dp5_issuers - mapped_dp5)}")
    require(capacity_subjects <= mapped_capacity, f"unmapped capacity subjects: {sorted(capacity_subjects - mapped_capacity)}")

    metadata = json.loads((SNAPSHOTS / "metadata.json").read_text(encoding="utf-8"))
    source_payloads: dict[str, list[dict[str, object]]] = {}
    for source in metadata["sources"]:
        path = SNAPSHOTS / source["path"]
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(sha256(path) == source["sha256"], f"snapshot hash mismatch: {path.name}")
        require(len(payload) == source["row_count"], f"snapshot row count mismatch: {path.name}")
        source_payloads[source["source_id"]] = payload
    twse_codes = {str(row["公司代號"]).strip() for row in source_payloads["twse_t187ap03_L"]}
    tpex_codes = {str(row["SecuritiesCompanyCode"]).strip() for row in source_payloads["tpex_mopsfin_t187ap03_O"]}
    require(not (twse_codes & tpex_codes), "TWSE/TPEx issuer code intersection is non-zero")
    require(len(twse_codes) + len(tpex_codes) == 1985, "L2 snapshot count changed")

    for adr in (ROOT / "docs" / "adr" / "0002-capacity-ceiling-tolerance.md", ROOT / "docs" / "adr" / "0003-fx-conversion-policy.md"):
        require("status: proposed" in adr.read_text(encoding="utf-8")[:80], f"ADR escaped proposed status: {adr.name}")

    print("candidate selftest: PASS")
    print("denominator=2036 t1_sources=12 points=11 manufacturing_edges=0 capacity_metrics=9 l2_snapshot=1985")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
