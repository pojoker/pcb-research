from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from dp1_denominator.adapters import fetch_draft
from dp1_denominator.registry import (
    FROZEN_FIELDS,
    INCLUSION_DECISION_FIELDS,
    build_snapshot_metadata,
    diff_snapshots,
    find_duplicate_candidates,
    load_csv,
    merge_decisions,
    validate_frozen,
    validate_inclusion_decisions,
    write_csv,
)


HERE = Path(__file__).resolve().parents[1]
FIXTURES = HERE / "fixtures"


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frozen = load_csv(FIXTURES / "_frozen.csv", FROZEN_FIELDS)
        self.decisions = load_csv(FIXTURES / "inclusion_decision.csv", INCLUSION_DECISION_FIELDS)

    def test_fixture_schemas_and_rules_pass(self) -> None:
        frozen_report = validate_frozen(self.frozen)
        decision_report = validate_inclusion_decisions(self.decisions, self.frozen)
        self.assertTrue(frozen_report.ok, frozen_report.errors)
        self.assertTrue(decision_report.ok, decision_report.errors)
        self.assertEqual(len(frozen_report.warnings), 3)

    def test_three_mother_child_pairs_are_candidates_not_removed(self) -> None:
        candidates = find_duplicate_candidates(self.frozen)
        keys = {candidate["candidate_key"] for candidate in candidates}
        self.assertEqual(keys, {"dcg:zhending", "dcg:kingboard", "dcg:shengyi"})
        ids = {row["entity_id"] for row in self.frozen}
        self.assertIn("issuer:TW:4958", ids)
        self.assertIn("issuer:CN:002938", ids)
        self.assertEqual(len(self.frozen), 6)

    def test_missing_duplicate_triage_is_rejected(self) -> None:
        report = validate_inclusion_decisions(self.decisions[:-1], self.frozen)
        self.assertFalse(report.ok)
        self.assertTrue(any("missing duplicate_candidate triage" in error for error in report.errors))

    def test_invalid_layer_and_id_are_rejected(self) -> None:
        bad = copy.deepcopy(self.frozen[0])
        bad["layer"] = "L9"
        bad["issuer_id"] = "002463"
        report = validate_frozen([bad])
        self.assertFalse(report.ok)
        self.assertTrue(any("invalid layer" in error for error in report.errors))
        self.assertTrue(any("invalid ID" in error for error in report.errors))

    def test_snapshot_metadata_is_auditable_and_pending(self) -> None:
        metadata = build_snapshot_metadata(
            self.frozen,
            source_name="fixture seed",
            source_kind="fixture",
            source_url="https://example.invalid/dp1/fixture-seed",
            query_date="2026-08-26",
            adapter_name="fixture",
            input_path=FIXTURES / "_frozen.csv",
        )
        self.assertTrue(metadata["snapshot_id"].startswith("snap:2026-08-26:"))
        self.assertEqual(metadata["freeze_status"], "待核")
        self.assertEqual(metadata["record_count"], 6)
        self.assertIn("input_sha256", metadata)

    def test_add_and_remove_each_emit_triage_row(self) -> None:
        before = self.frozen
        after = [row for row in self.frozen if row["entity_id"] != "issuer:HK:00148"]
        added = copy.deepcopy(self.frozen[0])
        added["entity_id"] = "issuer:CN:002463"
        added["issuer_id"] = "issuer:CN:002463"
        added["record_id"] = "rec:added"
        after.append(added)
        diff, triage = diff_snapshots(
            before,
            after,
            before_snapshot_id="snap:before",
            after_snapshot_id="snap:after",
            query_date="2026-08-26",
        )
        self.assertEqual({row["change"] for row in diff}, {"add", "remove"})
        self.assertEqual({row["decision_type"] for row in triage}, {"snapshot_add", "snapshot_remove"})
        self.assertTrue(all(row["decision_status"] == "待核" for row in triage))
        generated_report = validate_inclusion_decisions(triage)
        self.assertTrue(generated_report.ok, generated_report.errors)
        merged = merge_decisions(self.decisions, triage)
        self.assertEqual(len(merged), len(self.decisions) + 2)

    def test_draft_adapter_forces_pending_without_source_conclusion(self) -> None:
        payload = {
            "records": [{"code": "4958", "name": "fixture issuer", "layer": "L2"}]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            rows = fetch_draft(
                {
                    "fixture_path": str(path),
                    "field_map": {
                        "entity_id": "code",
                        "issuer_id": "code",
                        "name": "name",
                    },
                    "id_prefixes": {
                        "entity_id": "issuer:TW:",
                        "issuer_id": "issuer:TW:",
                    },
                    "defaults": {
                        "entity_type": "issuer",
                        "legal_entity_id": "-",
                        "plant_id": "-",
                        "group_id": "-",
                        "registration_source": "configured source pending verification",
                        "source_url": "https://example.invalid/draft",
                        "query_date": "2026-08-26",
                        "double_count_key": "dcg:fixture",
                        "double_count_rule": "无",
                        "aggregation_policy": "不适用",
                        "product_scope": "待核",
                    },
                }
            )
        self.assertEqual(rows[0]["record_status"], "待核")
        self.assertTrue(validate_frozen(rows).ok)
        self.assertIn("禁止视为交易所或协会结论", rows[0]["notes"])

    def test_csv_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roundtrip.csv"
            write_csv(path, FROZEN_FIELDS, self.frozen)
            self.assertEqual(load_csv(path, FROZEN_FIELDS), self.frozen)


if __name__ == "__main__":
    unittest.main()
