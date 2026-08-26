import unittest

from dp2_sources.customs8534 import FREEZE_FIELDS, PENDING_HUMAN, PENDING_UNFROZEN, check_8534_freeze


class Customs8534Tests(unittest.TestCase):
    def test_each_required_field_missing_keeps_definition_unfrozen(self):
        complete = {field: "set" for field in FREEZE_FIELDS}
        for field in FREEZE_FIELDS:
            row = dict(complete)
            row[field] = ""
            result = check_8534_freeze(row)
            self.assertEqual(result.status, PENDING_UNFROZEN, field)
            self.assertIn(field, result.missing_fields)
            self.assertFalse(result.is_frozen)

    def test_complete_fields_still_need_human_decision(self):
        result = check_8534_freeze({field: "set" for field in FREEZE_FIELDS})
        self.assertEqual(result.status, PENDING_HUMAN)
        self.assertFalse(result.is_frozen)

    def test_human_freeze_requires_audit_fields(self):
        row = {field: "set" for field in FREEZE_FIELDS}
        row["freeze_decision"] = "已人工冻结"
        result = check_8534_freeze(row)
        self.assertFalse(result.is_frozen)
        self.assertTrue(result.errors)
