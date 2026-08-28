#!/usr/bin/env python3
"""Validate the PCB claim-evidence knowledge graph.

The graph is deliberately strict about the difference between a source and an
evidence relation.  A URL in evidence.csv does not make a claim supported;
claim_evidence.csv must say what the source supports, refutes, or limits and
whether its scope matches the claim.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
ID_PATTERNS = {
    "concept_id": re.compile(r"^CON-[A-Z0-9-]+$"),
    "claim_id": re.compile(r"^CLM-\d{3}$"),
    "evidence_id": re.compile(r"^EVD-\d{3}$"),
    "relation_id": re.compile(r"^CER-\d{3}$"),
    "edge_id": re.compile(r"^KED-\d{3}$"),
    "question_id": re.compile(r"^Q-\d{3}$"),
}

SCHEMAS = {
    "concepts.csv": ("concept_id", "label", "kind", "system", "cell_id", "status", "notes"),
    "claims.csv": ("claim_id", "statement", "scope", "claim_class", "verdict", "confidence", "subject_concept_id", "conversation_turn_id", "verification_note"),
    "evidence.csv": ("evidence_id", "publisher", "title", "source_url", "publication_date", "retrieval_date", "source_role", "independence_group", "locator", "excerpt", "access_status"),
    "claim_evidence.csv": ("relation_id", "claim_id", "evidence_id", "relation", "scope_match", "weight", "notes"),
    "knowledge_edges.csv": ("edge_id", "from_concept_id", "relation", "to_concept_id", "claim_id", "polarity", "scope", "status"),
    "open_questions.csv": ("question_id", "claim_id", "missing_evidence_type", "status", "priority", "reopen_condition", "next_action"),
}

EXPECTED_CELLS = {
    "FAB1", "FAB2", "M1", "M2", "M3", "M4", "M5", "MSK", "M7", "FLX", "M9",
    "PM1", "PM2", "PM3", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9",
    "EQ1", "EQ2", "EQ3", "EQ4", "EQ5", "EQ6", "EQ7",
}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def _read_csv(path: Path, expected_header: tuple[str, ...], report: Report) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            actual = tuple(reader.fieldnames or ())
            if actual != expected_header:
                report.error(f"{path.name}: header mismatch; expected {expected_header}, got {actual}")
                return []
            rows: list[dict[str, str]] = []
            for line, row in enumerate(reader, 2):
                if None in row:
                    report.error(f"{path.name}:{line}: extra CSV fields")
                    continue
                normalized = {key: (value or "").strip() for key, value in row.items()}
                blanks = [key for key, value in normalized.items() if not value]
                if blanks:
                    report.error(f"{path.name}:{line}: blank fields must use '-' explicitly: {', '.join(blanks)}")
                rows.append(normalized)
            return rows
    except OSError as exc:
        report.error(f"{path}: cannot read: {exc}")
        return []


def _index(rows: Iterable[dict[str, str]], field: str, report: Report, filename: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    pattern = ID_PATTERNS[field]
    for line, row in enumerate(rows, 2):
        value = row.get(field, "")
        if not pattern.fullmatch(value):
            report.error(f"{filename}:{line}: invalid {field} {value!r}")
        if value in result:
            report.error(f"{filename}:{line}: duplicate {field} {value!r}")
        result[value] = row
    return result


def _absolute_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_graph(root: Path = ROOT) -> Report:
    report = Report()
    try:
        manifest = json.loads((root / "graph/manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.error(f"graph/manifest.json: {exc}")
        return report

    for relative in manifest.get("required_files", []):
        if not (root / relative).is_file():
            report.error(f"missing required file: {relative}")

    try:
        tree = json.loads((root / "tree.yaml").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.error(f"tree.yaml must be JSON-compatible YAML: {exc}")
        return report

    cells = tree.get("cells", [])
    cell_ids = [str(row.get("cell_id", "")) for row in cells]
    if len(cell_ids) != len(set(cell_ids)):
        report.error("tree.yaml: duplicate cell_id")
    if set(cell_ids) != EXPECTED_CELLS:
        report.error(
            "tree.yaml: cell set mismatch; missing="
            f"{sorted(EXPECTED_CELLS - set(cell_ids))}; extra={sorted(set(cell_ids) - EXPECTED_CELLS)}"
        )
    route_axis_ids = {str(row.get("axis_id", "")) for row in tree.get("route_axes", [])}
    if route_axis_ids != {"A", "B", "C", "D", "E", "F"}:
        report.error("tree.yaml: route axes must be exactly A-F")

    data: dict[str, list[dict[str, str]]] = {}
    for filename, schema in SCHEMAS.items():
        data[filename] = _read_csv(root / "graph" / filename, schema, report)

    concepts = _index(data["concepts.csv"], "concept_id", report, "concepts.csv")
    claims = _index(data["claims.csv"], "claim_id", report, "claims.csv")
    evidence = _index(data["evidence.csv"], "evidence_id", report, "evidence.csv")
    relations = _index(data["claim_evidence.csv"], "relation_id", report, "claim_evidence.csv")
    edges = _index(data["knowledge_edges.csv"], "edge_id", report, "knowledge_edges.csv")
    questions = _index(data["open_questions.csv"], "question_id", report, "open_questions.csv")

    allowed = manifest.get("enums", {})
    allowed_cells = set(cell_ids) | route_axis_ids | {"-"}
    for line, row in enumerate(data["concepts.csv"], 2):
        if row.get("cell_id") not in allowed_cells:
            report.error(f"concepts.csv:{line}: unknown cell or route axis {row.get('cell_id')!r}")

    expected_claims = set(manifest.get("expected_discussion_claim_ids", []))
    if set(claims) != expected_claims:
        report.error(
            "claims.csv: discussion coverage mismatch; missing="
            f"{sorted(expected_claims - set(claims))}; extra={sorted(set(claims) - expected_claims)}"
        )

    for line, row in enumerate(data["claims.csv"], 2):
        if row.get("subject_concept_id") not in concepts:
            report.error(f"claims.csv:{line}: dangling subject_concept_id {row.get('subject_concept_id')!r}")
        for field in ("claim_class", "verdict", "confidence"):
            if row.get(field) not in set(allowed.get(field, [])):
                report.error(f"claims.csv:{line}: invalid {field} {row.get(field)!r}")

    for line, row in enumerate(data["evidence.csv"], 2):
        if not _absolute_http_url(row.get("source_url", "")):
            report.error(f"evidence.csv:{line}: source_url must be absolute http(s)")
        if row.get("source_role") not in set(allowed.get("source_role", [])):
            report.error(f"evidence.csv:{line}: invalid source_role {row.get('source_role')!r}")
        if "turn" in row.get("source_url", "") and "search" in row.get("source_url", ""):
            report.error(f"evidence.csv:{line}: internal chat citation is not a public evidence URL")

    evidence_by_claim: dict[str, list[dict[str, str]]] = defaultdict(list)
    for line, row in enumerate(data["claim_evidence.csv"], 2):
        claim_id = row.get("claim_id", "")
        evidence_id = row.get("evidence_id", "")
        if claim_id not in claims:
            report.error(f"claim_evidence.csv:{line}: dangling claim_id {claim_id!r}")
        if evidence_id not in evidence:
            report.error(f"claim_evidence.csv:{line}: dangling evidence_id {evidence_id!r}")
        if row.get("relation") not in set(allowed.get("evidence_relation", [])):
            report.error(f"claim_evidence.csv:{line}: invalid relation {row.get('relation')!r}")
        if row.get("scope_match") not in set(allowed.get("scope_match", [])):
            report.error(f"claim_evidence.csv:{line}: invalid scope_match {row.get('scope_match')!r}")
        evidence_by_claim[claim_id].append(row)

    for line, row in enumerate(data["knowledge_edges.csv"], 2):
        if row.get("from_concept_id") not in concepts:
            report.error(f"knowledge_edges.csv:{line}: dangling from_concept_id {row.get('from_concept_id')!r}")
        if row.get("to_concept_id") not in concepts:
            report.error(f"knowledge_edges.csv:{line}: dangling to_concept_id {row.get('to_concept_id')!r}")
        if row.get("claim_id") not in claims:
            report.error(f"knowledge_edges.csv:{line}: dangling claim_id {row.get('claim_id')!r}")
        if row.get("polarity") not in set(allowed.get("edge_polarity", [])):
            report.error(f"knowledge_edges.csv:{line}: invalid polarity {row.get('polarity')!r}")
        if row.get("relation") == "does_not_imply" and row.get("polarity") != "negative":
            report.error(f"knowledge_edges.csv:{line}: does_not_imply must have negative polarity")

    question_claims: set[str] = set()
    for line, row in enumerate(data["open_questions.csv"], 2):
        claim_id = row.get("claim_id", "")
        if claim_id not in claims:
            report.error(f"open_questions.csv:{line}: dangling claim_id {claim_id!r}")
        question_claims.add(claim_id)

    for claim_id, claim in claims.items():
        verdict = claim.get("verdict")
        linked = evidence_by_claim.get(claim_id, [])
        relation_types = {row.get("relation") for row in linked}
        if verdict == "supported" and "supports" not in relation_types:
            report.error(f"{claim_id}: supported verdict requires a supports evidence relation")
        if verdict == "refuted" and "refutes" not in relation_types:
            report.error(f"{claim_id}: refuted verdict requires a refutes evidence relation")
        if verdict == "partially_supported":
            if "supports" not in relation_types or not ({"limits", "refutes"} & relation_types):
                report.error(f"{claim_id}: partially_supported requires supports plus limits/refutes")
        if verdict == "publicly_unverifiable" and claim_id not in question_claims:
            report.error(f"{claim_id}: publicly_unverifiable requires an open question")
        if verdict == "analyst_annotation" and claim.get("claim_class") != "analysis_annotation":
            report.error(f"{claim_id}: analyst_annotation verdict requires analysis_annotation claim class")
        if claim.get("claim_class") == "analysis_annotation" and verdict != "analyst_annotation":
            report.error(f"{claim_id}: analysis_annotation claim class cannot masquerade as a factual verdict")
        if verdict == "supported" and claim.get("claim_class") in {"application_observation", "application_inference"}:
            exact_company_support = any(
                row.get("relation") == "supports"
                and row.get("scope_match") == "exact"
                and evidence.get(row.get("evidence_id", ""), {}).get("source_role") == "primary_company"
                for row in linked
            )
            if not exact_company_support:
                report.error(f"{claim_id}: supported application claim requires exact primary_company evidence")

    verdict_counts = Counter(row.get("verdict", "") for row in claims.values())
    report.counts = {
        "cells": len(cell_ids),
        "concepts": len(concepts),
        "claims": len(claims),
        "evidence": len(evidence),
        "claim_evidence_relations": len(relations),
        "knowledge_edges": len(edges),
        "open_questions": len(questions),
        **{f"verdict_{key}": value for key, value in sorted(verdict_counts.items())},
    }
    if verdict_counts.get("pending", 0):
        report.warning(f"pending claims: {verdict_counts['pending']}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PCB claim-evidence graph")
    parser.add_argument("--check", action="store_true", help="validate canonical graph files")
    args = parser.parse_args()
    if not args.check:
        parser.error("only --check is currently supported")
    report = validate_graph(ROOT)
    print(json.dumps({"ok": report.ok, "counts": report.counts, "errors": report.errors, "warnings": report.warnings}, ensure_ascii=False, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
