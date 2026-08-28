from __future__ import annotations

import copy
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from dp1_denominator.adapters import (
    DraftAdapterError,
    TWSE_LISTED_COMPANIES_ENDPOINT,
    fetch_draft,
    fetch_twse_listed_company_draft,
)
from dp1_denominator.cli import main as cli_main
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

    def test_frozen_record_fails_closed_without_a_matching_manual_include_decision(self) -> None:
        frozen = copy.deepcopy(self.frozen[0])
        frozen["record_status"] = "已冻结"

        no_decisions = validate_frozen([frozen])
        self.assertFalse(no_decisions.ok)
        self.assertTrue(any("requires a matching manual_include" in error for error in no_decisions.errors))

        decision_ledger_without_rows = validate_inclusion_decisions([], [frozen])
        self.assertFalse(decision_ledger_without_rows.ok)
        self.assertTrue(
            any("requires a matching manual_include" in error for error in decision_ledger_without_rows.errors)
        )

        bypass = copy.deepcopy(self.decisions[0])
        bypass.update(
            {
                "entity_id": frozen["entity_id"],
                "issuer_id": frozen["issuer_id"],
                "name": frozen["name"],
                "layer": frozen["layer"],
                "registration_source": frozen["registration_source"],
                "decision_type": "duplicate_candidate",
                "action": "triage",
                "decision_status": "已裁决",
                "decision_owner": "reviewer-a",
                "decision_date": "2026-08-27",
                "evidence_anchor": "fixture://manual-review/zhending",
                "source_url": frozen["source_url"],
                "double_count_key": frozen["double_count_key"],
            }
        )
        bypass_report = validate_frozen([frozen], [bypass])
        self.assertFalse(bypass_report.ok)
        self.assertTrue(any("requires a matching manual_include" in error for error in bypass_report.errors))

    def test_frozen_record_requires_auditable_matching_manual_include_fields(self) -> None:
        frozen = copy.deepcopy(self.frozen[0])
        frozen["record_status"] = "已冻结"
        decision = copy.deepcopy(self.decisions[0])
        decision.update(
            {
                "decision_id": "manual:include:zhending",
                "decision_type": "manual_include",
                "action": "include",
                "entity_id": frozen["entity_id"],
                "issuer_id": frozen["issuer_id"],
                "name": frozen["name"],
                "layer": frozen["layer"],
                "registration_source": frozen["registration_source"],
                "inclusion_reason": "人工确认纳入",
                "evidence_anchor": "fixture://manual-review/zhending",
                "source_url": frozen["source_url"],
                "query_date": frozen["query_date"],
                "decision_owner": "reviewer-a",
                "decision_date": "2026-08-27",
                "decision_status": "已裁决",
                "double_count_key": frozen["double_count_key"],
            }
        )

        valid = validate_frozen([frozen], [decision])
        self.assertTrue(valid.ok, valid.errors)

        for field, invalid_value in (
            ("decision_owner", "待定"),
            ("decision_date", "-"),
            ("evidence_anchor", "-"),
            ("source_url", "https://example.invalid/dp1/other"),
            ("double_count_key", "dcg:other"),
        ):
            with self.subTest(field=field):
                invalid = copy.deepcopy(decision)
                invalid[field] = invalid_value
                report = validate_frozen([frozen], [invalid])
                self.assertFalse(report.ok)
                self.assertTrue(any(field in error for error in report.errors), report.errors)

    def test_snapshot_metadata_and_cli_reject_freeze_status_override(self) -> None:
        with self.assertRaisesRegex(ValueError, "mechanical snapshots remain 待核"):
            build_snapshot_metadata(
                self.frozen,
                source_name="fixture seed",
                source_kind="fixture",
                source_url="https://example.invalid/dp1/fixture-seed",
                query_date="2026-08-26",
                adapter_name="fixture",
                freeze_status="已冻结",
            )

        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stderr(io.StringIO()):
            result = cli_main(
                [
                    "snapshot",
                    "--frozen",
                    str(FIXTURES / "_frozen.csv"),
                    "--output",
                    str(Path(directory) / "snapshot.json"),
                    "--source-name",
                    "fixture seed",
                    "--source-kind",
                    "fixture",
                    "--source-url",
                    "https://example.invalid/dp1/fixture-seed",
                    "--query-date",
                    "2026-08-26",
                    "--adapter-name",
                    "fixture",
                    "--freeze-status",
                    "已冻结",
                ]
            )
        self.assertEqual(result, 2)

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

    def test_twse_listed_company_adapter_is_offline_capable_and_never_decides_scope(self) -> None:
        rows = fetch_twse_listed_company_draft(
            query_date="2026-08-28",
            fixture_path=FIXTURES / "twse_t187ap03_L.json",
        )

        self.assertEqual(TWSE_LISTED_COMPANIES_ENDPOINT, "https://openapi.twse.com.tw/v1/opendata/t187ap03_L")
        self.assertEqual([row["entity_id"] for row in rows], ["issuer:TW:2330", "issuer:TW:4958"])
        self.assertTrue(all(row["record_status"] == "待核" for row in rows))
        self.assertTrue(all(row["layer"] == "观察" for row in rows))
        self.assertTrue(all(row["product_scope"] == "待核" for row in rows))
        self.assertTrue(all(row["source_url"] == TWSE_LISTED_COMPANIES_ENDPOINT for row in rows))
        self.assertIn("產業別=半導體業", rows[0]["notes"])
        self.assertIn("不构成 PCB 纳入裁决", rows[0]["notes"])
        self.assertTrue(validate_frozen(rows).ok)

    def test_twse_listed_company_adapter_rejects_missing_official_fields(self) -> None:
        payload = [{"公司代號": "2330", "公司名稱": "台灣積體電路製造股份有限公司"}]
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "twse.json"
            fixture.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(DraftAdapterError, "missing required TWSE fields"):
                fetch_twse_listed_company_draft(
                    query_date="2026-08-28",
                    fixture_path=fixture,
                )

    def test_cli_fetches_twse_fixture_as_pending_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "twse-draft.csv"
            result = cli_main(
                [
                    "fetch-twse-listed-draft",
                    "--query-date",
                    "2026-08-28",
                    "--fixture",
                    str(FIXTURES / "twse_t187ap03_L.json"),
                    "--output",
                    str(output),
                ]
            )
            rows = load_csv(output, FROZEN_FIELDS)
        self.assertEqual(result, 0)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["record_status"] == "待核" for row in rows))

    def test_csv_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roundtrip.csv"
            write_csv(path, FROZEN_FIELDS, self.frozen)
            self.assertEqual(load_csv(path, FROZEN_FIELDS), self.frozen)


if __name__ == "__main__":
    unittest.main()
