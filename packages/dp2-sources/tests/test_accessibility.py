from datetime import date
import unittest

from dp2_sources.accessibility import probe_t1_sources


class AccessibilityTests(unittest.TestCase):
    def setUp(self):
        self.records = [{"origin_source_id": "t1-demo", "carrier_url": "https://t1.example.invalid/page"}]

    def test_network_is_disabled_unless_explicitly_enabled(self):
        called = False

        def fetcher(url, timeout):
            nonlocal called
            called = True
            return 200

        result = probe_t1_sources(self.records, fetcher=fetcher, today=date(2026, 8, 26))
        self.assertFalse(called)
        self.assertIsNone(result[0].reachable)
        self.assertEqual(result[0].error_type, "network_disabled")
        self.assertEqual(result[0].bearing_decision, "待人工裁决")

    def test_success_is_not_a_bearing_decision(self):
        result = probe_t1_sources(
            self.records,
            enable_network=True,
            fetcher=lambda url, timeout: 200,
            today=date(2026, 8, 26),
        )
        self.assertTrue(result[0].reachable)
        self.assertEqual(result[0].http_status, 200)
        self.assertEqual(result[0].bearing_decision, "待人工裁决")

    def test_http_failure_is_recorded(self):
        result = probe_t1_sources(
            self.records,
            enable_network=True,
            fetcher=lambda url, timeout: 503,
            today=date(2026, 8, 26),
        )
        self.assertFalse(result[0].reachable)
        self.assertEqual(result[0].http_status, 503)
