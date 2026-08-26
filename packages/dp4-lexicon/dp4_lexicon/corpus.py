"""Offline corpus measurement and collision reporting."""

from __future__ import annotations

import itertools
import json
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .validation import CompiledEntry


@dataclass(frozen=True)
class CorpusDocument:
    document_id: str
    text: str


@dataclass(frozen=True)
class Measurement:
    """The required four-key vocabulary measurement record."""

    keyword: str
    scope: str
    date: str
    hit_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "keyword": self.keyword,
            "scope": self.scope,
            "date": self.date,
            "hit_count": self.hit_count,
        }


@dataclass(frozen=True)
class CorpusScan:
    measurements: tuple[Measurement, ...]
    document_matches: dict[str, tuple[str, ...]]
    collision_documents: tuple[dict[str, object], ...]
    pair_counts: dict[str, int]

    def collision_report(self) -> dict[str, object]:
        matched = sum(bool(terms) for terms in self.document_matches.values())
        return {
            "status": "pending_review",
            "measurements": [record.as_dict() for record in self.measurements],
            "collision_statistics": {
                "documents_scanned": len(self.document_matches),
                "documents_with_any_match": matched,
                "documents_with_collisions": len(self.collision_documents),
                "term_hit_counts": {
                    measurement.keyword: measurement.hit_count
                    for measurement in self.measurements
                },
                "pair_counts": dict(sorted(self.pair_counts.items())),
            },
            "collisions": list(self.collision_documents),
            "review_note": "Mechanical candidate report only; no accept/reject or canonical write was performed.",
        }

    def as_json(self) -> str:
        return json.dumps(self.collision_report(), ensure_ascii=False, indent=2) + "\n"


class CorpusScanner:
    def __init__(self, entries: Iterable[CompiledEntry]):
        self.entries = tuple(entries)

    def scan(self, documents: Iterable[CorpusDocument], *, scope: str, date: str) -> CorpusScan:
        docs = tuple(documents)
        document_ids = [doc.document_id for doc in docs]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("corpus document ids must be unique")
        document_matches: dict[str, tuple[str, ...]] = {}
        term_counts: Counter[str] = Counter()
        for document in docs:
            terms = tuple(
                entry.entry.term for entry in self.entries if entry.matches(document.text)
            )
            document_matches[document.document_id] = terms
            term_counts.update(terms)

        measurements = tuple(
            Measurement(
                keyword=entry.entry.term,
                scope=scope,
                date=date,
                hit_count=term_counts[entry.entry.term],
            )
            for entry in self.entries
        )
        collisions: list[dict[str, object]] = []
        pair_counts: Counter[str] = Counter()
        for document_id, terms in document_matches.items():
            if len(terms) < 2:
                continue
            collisions.append(
                {"document_id": document_id, "terms": list(terms), "match_count": len(terms)}
            )
            for left, right in itertools.combinations(sorted(terms), 2):
                pair_counts[f"{left} <> {right}"] += 1
        return CorpusScan(
            measurements=measurements,
            document_matches=document_matches,
            collision_documents=tuple(collisions),
            pair_counts=dict(pair_counts),
        )


def load_corpus_jsonl(path: str) -> list[CorpusDocument]:
    """Load ``{"id": ..., "text": ...}`` JSONL corpus rows."""

    documents: list[CorpusDocument] = []
    with open(path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not isinstance(record.get("text"), str):
                raise ValueError(f"{path}:{line_number}: expected JSON object with string id and text")
            documents.append(CorpusDocument(record["id"], record["text"]))
    return documents
