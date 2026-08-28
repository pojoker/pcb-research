from __future__ import annotations

import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from scan import ROOT, validate_graph


class GraphValidationTests(unittest.TestCase):
    def copy_graph(self) -> Path:
        temporary = Path(tempfile.mkdtemp())
        shutil.copy(ROOT / "tree.yaml", temporary / "tree.yaml")
        shutil.copytree(ROOT / "graph", temporary / "graph")
        self.addCleanup(shutil.rmtree, temporary)
        return temporary

    @staticmethod
    def rewrite_csv(path: Path, mutate) -> None:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
        mutate(rows)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def test_current_graph_is_structurally_valid(self):
        report = validate_graph(ROOT)
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(report.counts["cells"], 30)
        self.assertEqual(report.counts["claims"], 40)

    def test_application_claim_cannot_be_supported_without_exact_company_evidence(self):
        root = self.copy_graph()

        def mutate_relations(rows):
            relation = next(row for row in rows if row["claim_id"] == "CLM-024" and row["relation"] == "supports")
            relation["scope_match"] = "generic_only"

        self.rewrite_csv(root / "graph/claim_evidence.csv", mutate_relations)
        report = validate_graph(root)
        self.assertFalse(report.ok)
        self.assertTrue(any("CLM-024: supported application claim requires" in error for error in report.errors))

    def test_dangling_concept_edge_is_rejected(self):
        root = self.copy_graph()

        def mutate(rows):
            rows[0]["to_concept_id"] = "CON-NOT-FOUND"

        self.rewrite_csv(root / "graph/knowledge_edges.csv", mutate)
        report = validate_graph(root)
        self.assertFalse(report.ok)
        self.assertTrue(any("dangling to_concept_id" in error for error in report.errors))

    def test_publicly_unverifiable_claim_requires_open_question(self):
        root = self.copy_graph()

        def mutate_claims(rows):
            next(row for row in rows if row["claim_id"] == "CLM-027")["verdict"] = "publicly_unverifiable"

        def mutate_questions(rows):
            rows[:] = [row for row in rows if row["claim_id"] != "CLM-027"]

        self.rewrite_csv(root / "graph/claims.csv", mutate_claims)
        self.rewrite_csv(root / "graph/open_questions.csv", mutate_questions)
        report = validate_graph(root)
        self.assertFalse(report.ok)
        self.assertTrue(any("publicly_unverifiable requires an open question" in error for error in report.errors))

    def test_analysis_annotation_cannot_masquerade_as_supported_fact(self):
        root = self.copy_graph()

        def mutate(rows):
            next(row for row in rows if row["claim_id"] == "CLM-028")["verdict"] = "supported"

        self.rewrite_csv(root / "graph/claims.csv", mutate)
        report = validate_graph(root)
        self.assertFalse(report.ok)
        self.assertTrue(any("cannot masquerade as a factual verdict" in error for error in report.errors))

    def test_search_log_rejects_dangling_question(self):
        root = self.copy_graph()

        def mutate(rows):
            rows.append(
                {
                    "search_id": "SRCH-999",
                    "question_id": "Q-999",
                    "searched_at": "2026-08-28",
                    "search_scope": "official sources",
                    "search_expression": "example",
                    "result": "no_candidate_found",
                    "candidate_source_url": "-",
                    "notes": "negative search is not refutation",
                }
            )

        self.rewrite_csv(root / "graph/search_log.csv", mutate)
        report = validate_graph(root)
        self.assertFalse(report.ok)
        self.assertTrue(any("dangling question_id" in error for error in report.errors))

    def test_candidate_search_result_requires_public_url(self):
        root = self.copy_graph()

        def mutate(rows):
            rows.append(
                {
                    "search_id": "SRCH-998",
                    "question_id": "Q-001",
                    "searched_at": "2026-08-28",
                    "search_scope": "official sources",
                    "search_expression": "example",
                    "result": "candidate_not_scope_matched",
                    "candidate_source_url": "-",
                    "notes": "candidate needs a locator",
                }
            )

        self.rewrite_csv(root / "graph/search_log.csv", mutate)
        report = validate_graph(root)
        self.assertFalse(report.ok)
        self.assertTrue(any("requires candidate_source_url" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
