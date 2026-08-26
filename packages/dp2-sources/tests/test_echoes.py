import json
from pathlib import Path
import unittest

from dp2_sources.echoes import EchoMention, cluster_numeric_echoes, numeric_signature


class EchoTests(unittest.TestCase):
    def test_three_layers_reproduce_one_independent_source(self):
        fixture = Path(__file__).parents[1] / "fixtures" / "prismark_three_layers.json"
        mentions = [EchoMention(**row) for row in json.loads(fixture.read_text(encoding="utf-8"))]
        clusters = cluster_numeric_echoes(mentions)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0].carrier_domains), 3)
        self.assertEqual(clusters[0].counted_source_count, 1)
        self.assertEqual(clusters[0].independence_groups, ("prismark",))

    def test_number_formatting_normalizes(self):
        self.assertEqual(numeric_signature("1,234.0; 8.50%"), numeric_signature("1234; 8.5%"))

    def test_same_numbers_need_a_supplied_claim_key(self):
        mentions = [
            EchoMention("a", "https://one.invalid/a", "a", "a", "", "100"),
            EchoMention("b", "https://two.invalid/a", "b", "b", "", "100"),
        ]
        self.assertEqual(cluster_numeric_echoes(mentions), [])
