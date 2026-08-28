import json
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dp2_sources.cli import main


PACKAGE_ROOT = Path(__file__).parents[1]


CSV_COMMANDS = (
    (
        "validate-ledger",
        "fixtures/source_ledger_template.csv",
        (
            "origin_source_id",
            "carrier_url",
            "independence_group",
            "paywall",
            "coverage_scope",
            "source_role",
            "publisher_name",
            "source_tier",
            "recorded_at",
            "recorded_by",
            "review_status",
            "reviewed_at",
            "review_note",
            "t1_bearing_decision",
            "t1_bearing_decided_by",
            "t1_bearing_decided_at",
        ),
    ),
    (
        "probe-t1",
        "fixtures/t1_probe_sources.csv",
        ("origin_source_id", "carrier_url"),
    ),
    (
        "check-8534",
        "fixtures/8534_freeze_template.csv",
        (
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
            "freeze_decision",
            "decided_by",
            "decided_at",
            "decision_note",
        ),
    ),
)


class CliSchemaDriftTests(unittest.TestCase):
    def _run(self, command, input_path, output_path):
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main([command, str(input_path), str(output_path)])
        return code, stderr.getvalue()

    def _write_csv(self, path, header, row=None):
        values = row or ["x"] * len(header)
        path.write_text(",".join(header) + "\n" + ",".join(values) + "\n", encoding="utf-8")

    def test_missing_column_fails_closed_for_every_csv_cli(self):
        for command, _, header in CSV_COMMANDS:
            with self.subTest(command=command):
                with TemporaryDirectory() as directory:
                    input_path = Path(directory) / "missing.csv"
                    output_path = Path(directory) / "result.json"
                    self._write_csv(input_path, header[:-1])
                    code, error = self._run(command, input_path, output_path)
                    self.assertNotEqual(code, 0)
                    self.assertIn("header", error.lower())
                    self.assertIn("missing", error.lower())
                    self.assertFalse(output_path.exists())

    def test_extra_column_fails_closed_for_every_csv_cli(self):
        for command, _, header in CSV_COMMANDS:
            with self.subTest(command=command):
                with TemporaryDirectory() as directory:
                    input_path = Path(directory) / "extra.csv"
                    output_path = Path(directory) / "result.json"
                    self._write_csv(input_path, header + ("unexpected",))
                    code, error = self._run(command, input_path, output_path)
                    self.assertNotEqual(code, 0)
                    self.assertIn("header", error.lower())
                    self.assertIn("extra", error.lower())
                    self.assertFalse(output_path.exists())

    def test_reordered_header_fails_closed_for_every_csv_cli(self):
        for command, _, header in CSV_COMMANDS:
            with self.subTest(command=command):
                with TemporaryDirectory() as directory:
                    input_path = Path(directory) / "reordered.csv"
                    output_path = Path(directory) / "result.json"
                    reordered = (header[1], header[0], *header[2:])
                    self._write_csv(input_path, reordered)
                    code, error = self._run(command, input_path, output_path)
                    self.assertNotEqual(code, 0)
                    self.assertIn("header", error.lower())
                    self.assertIn("order", error.lower())
                    self.assertFalse(output_path.exists())

    def test_extra_data_cell_fails_closed(self):
        command, _, header = CSV_COMMANDS[1]
        with TemporaryDirectory() as directory:
            input_path = Path(directory) / "extra-cell.csv"
            output_path = Path(directory) / "result.json"
            self._write_csv(input_path, header, ["source", "https://example.invalid", "unexpected"])
            code, error = self._run(command, input_path, output_path)
            self.assertNotEqual(code, 0)
            self.assertIn("row 2", error.lower())
            self.assertFalse(output_path.exists())

    def test_echo_input_unknown_field_fails_closed(self):
        fixture = PACKAGE_ROOT / "fixtures" / "prismark_three_layers.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        payload[0]["unexpected"] = "must be rejected"
        with TemporaryDirectory() as directory:
            input_path = Path(directory) / "echoes.json"
            output_path = Path(directory) / "result.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            code, error = self._run("detect-echoes", input_path, output_path)
            self.assertNotEqual(code, 0)
            self.assertIn("unexpected", error.lower())
            self.assertFalse(output_path.exists())

    def test_echo_json_object_order_is_not_treated_as_schema_drift(self):
        fixture = PACKAGE_ROOT / "fixtures" / "prismark_three_layers.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        payload = [dict(reversed(tuple(record.items()))) for record in payload]
        with TemporaryDirectory() as directory:
            input_path = Path(directory) / "echoes.json"
            output_path = Path(directory) / "result.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            code, error = self._run("detect-echoes", input_path, output_path)
            self.assertEqual(code, 0, error)
            self.assertTrue(output_path.exists())
