import unittest

from dp2_sources.schema import LEDGER_FIELDS, validate_ledger_record


class SchemaTests(unittest.TestCase):
    def valid_row(self):
        row = {field: "x" for field in LEDGER_FIELDS}
        row.update(
            origin_source_id="origin-demo",
            carrier_url="https://issuer.example.invalid/disclosure",
            independence_group="issuer-demo",
            paywall="no",
            coverage_scope="issuer disclosure",
            source_role="direct",
            recorded_at="2026-08-26",
            review_status="待核",
            t1_bearing_decision="待人工裁决",
            reviewed_at="",
            review_note="",
            t1_bearing_decided_by="",
            t1_bearing_decided_at="",
        )
        return row

    def test_required_provenance_and_audit_fields_are_checked(self):
        row = self.valid_row()
        row["independence_group"] = ""
        result = validate_ledger_record(row)
        self.assertFalse(result.valid)
        self.assertIn("missing required field: independence_group", result.errors)

    def test_source_role_is_limited_to_four_allowed_values(self):
        row = self.valid_row()
        row["source_role"] = "T1"
        result = validate_ledger_record(row)
        self.assertFalse(result.valid)

    def test_t1_allowance_requires_human_audit(self):
        row = self.valid_row()
        row["t1_bearing_decision"] = "人工允许"
        result = validate_ledger_record(row)
        self.assertFalse(result.valid)
        self.assertIn("人工允许 requires t1_bearing_decided_by", result.errors)
