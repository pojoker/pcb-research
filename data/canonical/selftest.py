#!/usr/bin/env python3
"""Fail-closed checks for the H1-H4 canonical instance bundle."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

for package in ("dp1-denominator", "dp2-sources", "dp5-ledger"):
    sys.path.insert(0, str(ROOT / "packages" / package))

from dp1_denominator.registry import (  # noqa: E402
    FROZEN_FIELDS,
    INCLUSION_DECISION_FIELDS,
    load_csv,
    validate_frozen,
    validate_inclusion_decisions,
)
from build_from_approved_candidates import GENERATED_FILES, IDENTITY_FIELDS  # noqa: E402
from dp2_sources.schema import LEDGER_FIELDS, validate_ledger_record  # noqa: E402
from dp5_ledger.schema import load_active_cells  # noqa: E402
from dp5_ledger.validation import validate_ledger  # noqa: E402


def load_json(name: str):
    with (HERE / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_plain_csv(name: str) -> list[dict[str, str]]:
    with (HERE / name).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_dp1(frozen_name: str, decision_name: str, expected_count: int) -> None:
    frozen = load_csv(HERE / frozen_name, FROZEN_FIELDS)
    decisions = load_csv(HERE / decision_name, INCLUSION_DECISION_FIELDS)
    assert len(frozen) == expected_count
    assert len(decisions) == expected_count
    assert all(row["record_status"] == "已冻结" for row in frozen)
    frozen_report = validate_frozen(frozen, decisions)
    decision_report = validate_inclusion_decisions(decisions, frozen)
    assert frozen_report.ok, frozen_report.errors
    assert decision_report.ok, decision_report.errors


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="canonical-selftest-") as temp_dir:
        rebuilt = Path(temp_dir)
        subprocess.run(
            [sys.executable, str(HERE / "build_from_approved_candidates.py"), "--output-dir", str(rebuilt)],
            check=True,
        )
        for name in GENERATED_FILES:
            assert (HERE / name).read_bytes() == (rebuilt / name).read_bytes(), f"generated artifact drift: {name}"

    assert_dp1("denominator_l2_frozen.csv", "inclusion_decision_l2.csv", 1985)
    assert_dp1("denominator_instances_frozen.csv", "inclusion_decision_instances.csv", 13)

    instance_rows = load_csv(HERE / "denominator_instances_frozen.csv", FROZEN_FIELDS)
    identity_rows = load_plain_csv("subject_identity_map.csv")
    assert tuple(identity_rows[0]) == IDENTITY_FIELDS
    assert len(identity_rows) == 13
    assert all(row["mapping_status"] == "已冻结" for row in identity_rows)
    assert {row["canonical_entity_id"] for row in identity_rows} == {row["entity_id"] for row in instance_rows}
    assert all(
        row["denominator_record_id"] == f"frozen:h3-cn-{row['canonical_entity_id'].rsplit(':', 1)[-1]}"
        for row in identity_rows
    )
    assert all(
        row["dp5_subject_id"] in {"-", f"issuer_cn_{row['canonical_entity_id'].rsplit(':', 1)[-1]}"}
        for row in identity_rows
    )
    assert all(
        row["capacity_subject_id"] in {"-", f"issuer_{row['canonical_entity_id'].rsplit(':', 1)[-1]}"}
        for row in identity_rows
    )
    dp5_subjects = {row["dp5_subject_id"] for row in identity_rows if row["dp5_subject_id"] != "-"}
    capacity_subjects = {row["capacity_subject_id"] for row in identity_rows if row["capacity_subject_id"] != "-"}

    t1_rows = load_plain_csv("t1_source_ledger.csv")
    assert tuple(t1_rows[0]) == LEDGER_FIELDS
    assert len(t1_rows) == 12
    for row in t1_rows:
        report = validate_ledger_record(row)
        assert report.valid, report.errors
        assert row["review_status"] == "已人工复核"
        assert row["t1_bearing_decision"] == "人工允许"

    ledger = load_json("company_points_ledger.json")
    active_cells = load_active_cells(ROOT / "tree.yaml")
    report = validate_ledger(ledger, active_cells)
    assert report.ok, report.errors
    assert len(ledger["points"]) == 11
    assert len(ledger["manufacturing_edges"]) == 0
    assert len(ledger["prohibited_additive_subject_pairs"]) == 1
    assert len({row["cell_id"] for row in ledger["points"]}) == 8
    assert {row["subject_id"] for row in ledger["points"]} == dp5_subjects
    assert all(
        pair[side] in dp5_subjects
        for pair in ledger["prohibited_additive_subject_pairs"]
        for side in ("subject_a_id", "subject_b_id")
    )

    capacity = load_json("capacity_claim_snapshots.json")
    assert len(capacity["snapshots"]) == 9
    assert all(row["status"] == "accepted_as_claim_snapshot_only" for row in capacity["snapshots"])
    assert all(row["record_type"] == "disclosure_claim_snapshot" for row in capacity["snapshots"])
    assert {row["subject_id"] for row in capacity["snapshots"]} == capacity_subjects
    assert all(row["physical_fact_status"] == "not_instantiated" for row in capacity["snapshots"])
    assert all(row["publishable"] is False for row in capacity["snapshots"])
    assert all(row["aggregation_eligibility"] == "blocked" for row in capacity["snapshots"])
    assert all(row["formal_ledger_eligibility"].startswith("blocked") for row in capacity["snapshots"])
    assert all(
        row["plant_id"] == "unknown" or row["plant_id"].endswith("_candidate")
        for row in capacity["snapshots"]
    )
    assert capacity["source_candidate_sha256"] == sha256(ROOT / "data" / "candidates" / "capacity_metrics.json")

    tolerance = load_json("tolerance_policy.json")
    fx = load_json("fx_policy.json")
    gates = load_json("human_gate_decisions.json")
    assert tolerance["status"] == "accepted" and tolerance["approved_tolerance_instances"] == []
    assert fx["status"] == "accepted" and fx["instantiated_conversions"] == []
    assert gates["defined_gate_ids"] == ["H1", "H2", "H3", "H4"]
    assert gates["undefined_gate_ids"] == [f"H{number}" for number in range(5, 15)]
    assert gates["undefined_gate_action"] == "none"
    assert len(gates["decisions"]) == 4
    assert gates == json.loads(
        (ROOT / "data" / "decisions" / "2026-08-28-h1-h4.json").read_text(encoding="utf-8")
    )

    manifest = load_json("build_manifest.json")
    assert manifest["human_gate_source_sha256"] == sha256(ROOT / manifest["human_gate_source"])
    assert {row["path"] for row in manifest["artifacts"]} == set(GENERATED_FILES).difference({"build_manifest.json"})
    for artifact in manifest["artifacts"]:
        assert artifact["sha256"] == sha256(HERE / artifact["path"]), artifact["path"]

    for adr in ("0002-capacity-ceiling-tolerance.md", "0003-fx-conversion-policy.md"):
        text = (ROOT / "docs" / "adr" / adr).read_text(encoding="utf-8")
        assert text.startswith("---\nstatus: accepted\n---")

    print("PASS: H1-H4 canonical bundle validates")


if __name__ == "__main__":
    main()
