#!/usr/bin/env python3
"""Build deterministic canonical ledgers from the H1-H4 approved candidates.

This script encodes the human decision; it does not make one.  In particular,
capacity disclosures remain claim snapshots rather than plant-level physical
facts, and no manufacturing edge or numeric tolerance instance is invented.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "data" / "canonical"
OUTPUT = CANONICAL
CANDIDATES = ROOT / "data" / "candidates"
DECISION_SOURCE = ROOT / "data" / "decisions" / "2026-08-28-h1-h4.json"
DECISION_DATE = "2026-08-28"

IDENTITY_FIELDS = (
    "canonical_entity_id",
    "entity_type",
    "denominator_record_id",
    "dp5_subject_id",
    "capacity_subject_id",
    "name",
    "mapping_scope",
    "mapping_status",
    "missing_id_reason",
)
GENERATED_DATA_FILES = (
    "denominator_l2_frozen.csv",
    "inclusion_decision_l2.csv",
    "denominator_instances_frozen.csv",
    "inclusion_decision_instances.csv",
    "subject_identity_map.csv",
    "t1_source_ledger.csv",
    "company_points_ledger.json",
    "capacity_claim_snapshots.json",
    "tolerance_policy.json",
    "fx_policy.json",
    "human_gate_decisions.json",
)
GENERATED_FILES = (*GENERATED_DATA_FILES, "build_manifest.json")

for package in ("dp1-denominator", "dp2-sources", "dp5-ledger"):
    sys.path.insert(0, str(ROOT / "packages" / package))

from dp1_denominator.registry import FROZEN_FIELDS, INCLUSION_DECISION_FIELDS  # noqa: E402
from dp2_sources.schema import LEDGER_FIELDS  # noqa: E402
from dp5_ledger.schema import PAIR_FIELDS, POINT_FIELDS, SUBJECT_FIELDS  # noqa: E402


INSTANCE_SCOPES = {
    "002463": "FAB1/普通刚性；发行人能力点，不代表厂址产能",
    "300476": "FAB1/普通刚性+HDI；发行人能力点，不代表厂址产能",
    "688183": "FAB1/普通刚性；与生益科技禁止加总",
    "600183": "M1/普通刚性；CCL 材料点，与生益电子禁止加总",
    "603256": "M5/普通刚性；电子玻纤布/纱材料点",
    "601208": "M4/普通刚性；电子级树脂材料点",
    "301200": "EQ2+EQ6/普通刚性；设备供应点，不反推客户装机",
    "688700": "EQ3/普通刚性；设备供应点，不反推客户装机",
    "688630": "EQ1/普通刚性；设备供应点，不反推客户装机",
    "603328": "FAB1 披露快照；弱产能上界，不作强天顶",
    "603228": "FAB1 发行人合并披露快照；禁止厂址物理聚合",
    "002916": "FAB1+FAB2 披露分列；收入不得换算面积或跨 FAB 加总",
    "002436": "FAB2 建成/披露快照；约数不作强天顶",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "-") for field in fields})


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decision_for(row: Mapping[str, str], gate: str, ordinal: int, reason: str) -> dict[str, str]:
    return {
        "decision_id": f"{gate.lower()}-include-{ordinal:04d}",
        "decision_type": "manual_include",
        "action": "include",
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "issuer_id": row["issuer_id"],
        "legal_entity_id": row["legal_entity_id"],
        "plant_id": row["plant_id"],
        "group_id": row["group_id"],
        "name": row["name"],
        "layer": row["layer"],
        "registration_source": row["registration_source"],
        "inclusion_reason": reason,
        "exclusion_reason": "-",
        "evidence_anchor": f"human-gate://{DECISION_DATE}/{gate}/{row['entity_id']}",
        "source_url": row["source_url"],
        "query_date": row["query_date"],
        "decision_owner": "user",
        "decision_date": DECISION_DATE,
        "decision_status": "已裁决",
        "double_count_key": row["double_count_key"],
        "notes": f"{gate} 人闸批准；仅在本行 product_scope 内有效。",
    }


def build_denominators() -> None:
    main_rows = read_csv(CANDIDATES / "denominator_candidates.csv")
    l1bc_rows = read_csv(CANDIDATES / "denominator_l1bc_candidates.csv")
    if any(row["record_status"] != "待核" for row in [*main_rows, *l1bc_rows]):
        raise ValueError("candidate denominator row escaped pending state")

    l2_rows: list[dict[str, str]] = []
    for source in main_rows:
        if source["layer"] != "L2":
            continue
        row = {field: source[field] for field in FROZEN_FIELDS}
        row["record_id"] = row["record_id"].replace("cand:", "frozen:", 1)
        row["record_status"] = "已冻结"
        row["product_scope"] = "L2 台湾上市/上柜发行人机械母集；不含兴柜；不证明 PCB 主营或中国大陆产能"
        row["notes"] = "H1 人闸批准 2026-08-28 TWSE+TPEx 快照；仅冻结发行人母集身份。"
        l2_rows.append(row)
    l2_decisions = [
        decision_for(row, "H1", index, "冻结 2026-08-28 TWSE+TPEx（不含兴柜）L2 机械母集")
        for index, row in enumerate(l2_rows, start=1)
    ]
    write_csv(OUTPUT / "denominator_l2_frozen.csv", FROZEN_FIELDS, l2_rows)
    write_csv(OUTPUT / "inclusion_decision_l2.csv", INCLUSION_DECISION_FIELDS, l2_decisions)

    points = read_json(CANDIDATES / "company_points_edges.json")
    capacity = read_json(CANDIDATES / "capacity_metrics.json")
    point_url_by_code = {
        point["subject_id"].rsplit("_", 1)[-1]: point["source_url"]
        for point in points["points"]
    }
    capacity_url_by_code: dict[str, str] = {}
    for metric in capacity["metrics"]:
        code = metric["subject_id"].rsplit("_", 1)[-1]
        capacity_url_by_code.setdefault(code, metric["anchor"]["url"])

    candidates_by_code: dict[str, dict[str, str]] = {}
    for source in [*main_rows, *l1bc_rows]:
        code = source["issuer_id"].rsplit(":", 1)[-1]
        if code in INSTANCE_SCOPES:
            candidates_by_code[code] = source

    missing = sorted(set(INSTANCE_SCOPES).difference(candidates_by_code))
    if missing:
        raise ValueError(f"missing denominator candidates for: {', '.join(missing)}")
    point_codes = {point["subject_id"].rsplit("_", 1)[-1] for point in points["points"]}
    capacity_codes = {metric["subject_id"].rsplit("_", 1)[-1] for metric in capacity["metrics"]}
    extra_subjects = sorted((point_codes | capacity_codes).difference(INSTANCE_SCOPES))
    if extra_subjects:
        raise ValueError(f"canonical subject lacks an H3 denominator scope: {', '.join(extra_subjects)}")

    instance_rows: list[dict[str, str]] = []
    for code in INSTANCE_SCOPES:
        source = candidates_by_code[code]
        row = {field: source[field] for field in FROZEN_FIELDS}
        row["record_id"] = f"frozen:h3-cn-{code}"
        row["record_status"] = "已冻结"
        row["registration_source"] = "H3 人闸批准的发行人原始披露锚"
        row["source_url"] = (
            point_url_by_code[code]
            if code in point_url_by_code
            else capacity_url_by_code[code]
        )
        row["product_scope"] = INSTANCE_SCOPES[code]
        row["notes"] = "H3 仅批准发行人及窄范围能力点/披露快照；法人、厂址和物理流未补齐时不得推断。"
        instance_rows.append(row)
    instance_decisions = [
        decision_for(row, "H3", index, "先入正式分母，再允许对应 point 或披露快照进入正式账本")
        for index, row in enumerate(instance_rows, start=1)
    ]
    write_csv(OUTPUT / "denominator_instances_frozen.csv", FROZEN_FIELDS, instance_rows)
    write_csv(OUTPUT / "inclusion_decision_instances.csv", INCLUSION_DECISION_FIELDS, instance_decisions)

    point_subject_by_code = {
        point["subject_id"].rsplit("_", 1)[-1]: point["subject_id"]
        for point in points["points"]
    }
    capacity_subject_by_code = {
        metric["subject_id"].rsplit("_", 1)[-1]: metric["subject_id"]
        for metric in capacity["metrics"]
    }
    identity_rows = []
    for row in instance_rows:
        code = row["issuer_id"].rsplit(":", 1)[-1]
        identity_rows.append(
            {
                "canonical_entity_id": row["entity_id"],
                "entity_type": "issuer",
                "denominator_record_id": row["record_id"],
                "dp5_subject_id": point_subject_by_code.get(code, "-"),
                "capacity_subject_id": capacity_subject_by_code.get(code, "-"),
                "name": row["name"],
                "mapping_scope": "发行人证券代码；不映射法人、厂址或集团",
                "mapping_status": "已冻结",
                "missing_id_reason": "仅发行人身份已冻结；法人、厂址与集团 ID 尚未实例化。",
            }
        )
    write_csv(OUTPUT / "subject_identity_map.csv", IDENTITY_FIELDS, identity_rows)


def build_t1_ledger() -> None:
    rows = read_csv(CANDIDATES / "t1_source_candidates.csv")
    if any(
        row["review_status"] != "待核" or row["t1_bearing_decision"] != "待人工裁决"
        for row in rows
    ):
        raise ValueError("T1 candidate escaped its pending human gate")
    approved: list[dict[str, str]] = []
    suffix = "H2 人闸仅按 coverage_scope 与本条 review_note 批准；索引/导航页不得替代实际文件。"
    for source in rows:
        row = {field: source.get(field, "") for field in LEDGER_FIELDS}
        row["review_status"] = "已人工复核"
        row["reviewed_at"] = DECISION_DATE
        row["review_note"] = f"{row['review_note']} {suffix}"
        row["t1_bearing_decision"] = "人工允许"
        row["t1_bearing_decided_by"] = "user"
        row["t1_bearing_decided_at"] = DECISION_DATE
        approved.append(row)
    write_csv(OUTPUT / "t1_source_ledger.csv", LEDGER_FIELDS, approved)


def build_company_ledger() -> None:
    candidate = read_json(CANDIDATES / "company_points_edges.json")
    if any(point["review_status"] != "pending" for point in candidate["points"]):
        raise ValueError("point candidate escaped pending state")
    if any(pair["review_status"] != "pending" for pair in candidate["prohibited_additive_subject_pairs"]):
        raise ValueError("prohibited-pair candidate escaped pending state")
    subjects = []
    for record in candidate["subject_mappings"]:
        row = {field: record[field] for field in SUBJECT_FIELDS}
        if row["subject_type"] == "issuer":
            row["group_id"] = ""
            row["missing_id_reason"] = "H3 仅冻结发行人证券身份；法人、厂址与集团 ID 尚未实例化。"
        else:
            row["missing_id_reason"] = "H3 仅批准本 pair 的禁止加总关系范围；未将该占位符实例化为正式集团 ID。"
        subjects.append(row)
    points = [
        {field: record[field] for field in POINT_FIELDS}
        for record in candidate["points"]
    ]
    pairs = []
    for source in candidate["prohibited_additive_subject_pairs"]:
        row = {field: source[field] for field in PAIR_FIELDS}
        row["adjudicator"] = "user"
        row["adjudicated_on"] = DECISION_DATE
        row["registry_version"] = "human-gate-H3-v1"
        pairs.append(row)
    write_json(
        OUTPUT / "company_points_ledger.json",
        {
            "schema_version": 1,
            "subject_mappings": subjects,
            "points": points,
            "metrics": [],
            "manufacturing_edges": [],
            "prohibited_additive_subject_pairs": pairs,
            "aggregation_requests": [],
        },
    )


def build_capacity_snapshots() -> None:
    candidate_path = CANDIDATES / "capacity_metrics.json"
    candidate = read_json(candidate_path)
    if any(metric["status"] != "pending" for metric in candidate["metrics"]):
        raise ValueError("capacity candidate escaped pending state")
    snapshots = []
    for source in candidate["metrics"]:
        row = dict(source)
        row["candidate_record_type"] = row.pop("record_type")
        row["record_type"] = "disclosure_claim_snapshot"
        row["status"] = "accepted_as_claim_snapshot_only"
        row["human_gate_id"] = "H3"
        row["approved_by"] = "user"
        row["approved_on"] = DECISION_DATE
        row["semantic_scope"] = "source_disclosure_claim_only"
        row["physical_fact_status"] = "not_instantiated"
        row["publishable"] = False
        row["aggregation_eligibility"] = "blocked"
        row["disallowed_inferences"] = [
            "plant_physical_aggregation_without_complete_identity_and_flow_keys",
            "revenue_to_area_conversion",
            "manufacturing_edge_inference",
            "use_as_dp6_strong_ceiling_without_separate_exact_scope_gate",
        ]
        snapshots.append(row)
    write_json(
        OUTPUT / "capacity_claim_snapshots.json",
        {
            "schema_version": "canonical.capacity-disclosure-snapshots.v1",
            "generated_on": DECISION_DATE,
            "human_gate_id": "H3",
            "decision": "accepted_as_disclosure_claim_snapshots_only",
            "source_candidate_sha256": sha256(candidate_path),
            "scope_note": "披露快照是‘来源陈述了什么’，不是厂址物理事实、强产能天顶或可发布推断。",
            "subject_mappings": [
                {
                    **record,
                    "candidate_subject_type": record["subject_type"],
                    "subject_type": "issuer",
                    "mapping_status": "issuer_identity_frozen_deeper_ids_uninstantiated",
                    "missing_id_reason": "H3 仅冻结发行人证券身份；法人、厂址与集团 ID 尚未实例化。",
                }
                for record in candidate["subject_mappings"]
            ],
            "snapshots": snapshots,
            "excluded_or_indeterminate": candidate["excluded_or_indeterminate"],
        },
    )


def build_policies_and_gate_record() -> None:
    write_json(
        OUTPUT / "tolerance_policy.json",
        {
            "schema_version": "canonical.tolerance-policy.v1",
            "status": "accepted",
            "human_gate_id": "H4",
            "decided_by": "user",
            "decision_date": DECISION_DATE,
            "global_default": None,
            "rule": "exact_scope_calibration",
            "insufficient_evidence_result": "indeterminate",
            "approval_capacity_ceiling_strength": "weak_only",
            "approved_tolerance_instances": [],
            "note": "ADR 被接受不等于任意数值实例获批；当前没有可用于 DP6 的容差实例。",
        },
    )
    write_json(
        OUTPUT / "fx_policy.json",
        {
            "schema_version": "canonical.fx-policy.v1",
            "status": "accepted",
            "human_gate_id": "H4",
            "decided_by": "user",
            "decision_date": DECISION_DATE,
            "target_currency": "CNY",
            "preserve_original_currency": True,
            "stock_rate_rule": "period_end_official_closing_or_last_preceding_official_quote",
            "flow_rate_rule": "transaction_date_first",
            "period_average_rule": "requires_separate_volatility_human_gate",
            "missing_or_unapproved_result": "indeterminate",
            "instantiated_conversions": [],
        },
    )
    gates = read_json(DECISION_SOURCE)
    if gates.get("defined_gate_ids") != ["H1", "H2", "H3", "H4"]:
        raise ValueError("decision source defines an unexpected human-gate set")
    if gates.get("undefined_gate_ids") != [f"H{number}" for number in range(5, 15)]:
        raise ValueError("decision source does not preserve H5-H14 as undefined")
    if gates.get("undefined_gate_action") != "none" or len(gates.get("decisions", [])) != 4:
        raise ValueError("undefined gates were executed or the H1-H4 decision set drifted")
    write_json(OUTPUT / "human_gate_decisions.json", gates)


def build_manifest() -> None:
    write_json(
        OUTPUT / "build_manifest.json",
        {
            "schema_version": "canonical.build-manifest.v1",
            "generated_on": DECISION_DATE,
            "human_gate_source": str(DECISION_SOURCE.relative_to(ROOT)),
            "human_gate_source_sha256": sha256(DECISION_SOURCE),
            "artifacts": [
                {"path": name, "sha256": sha256(OUTPUT / name)}
                for name in GENERATED_DATA_FILES
            ],
        },
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=CANONICAL)
    args = parser.parse_args(argv)
    destination = args.output_dir.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    global OUTPUT
    with tempfile.TemporaryDirectory(prefix=".canonical-build-", dir=destination.parent) as stage:
        OUTPUT = Path(stage)
        build_denominators()
        build_t1_ledger()
        build_company_ledger()
        build_capacity_snapshots()
        build_policies_and_gate_record()
        build_manifest()
        missing = [name for name in GENERATED_FILES if not (OUTPUT / name).is_file()]
        if missing:
            raise RuntimeError(f"staged canonical build is incomplete: {', '.join(missing)}")
        destination.mkdir(parents=True, exist_ok=True)
        for name in GENERATED_DATA_FILES:
            os.replace(OUTPUT / name, destination / name)
        os.replace(OUTPUT / "build_manifest.json", destination / "build_manifest.json")
    OUTPUT = destination
    print(f"PASS: rebuilt H1-H4 canonical ledgers in {destination}")


if __name__ == "__main__":
    main()
