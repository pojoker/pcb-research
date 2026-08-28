"""Conservative cross-domain numeric-echo clustering.

Clusters are review drafts.  A shared number does not prove a shared source;
the operator supplies a claim key and provenance/independence metadata.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Iterable
from urllib.parse import urlparse


ECHO_MENTION_FIELDS = (
    "mention_id",
    "carrier_url",
    "origin_source_id",
    "independence_group",
    "claim_key",
    "text",
)


# Put the comma-grouped form first and require a complete token; otherwise the
# first alternative can truncate an ungrouped ``1234`` to ``123``.
NUMBER_RE = re.compile(r"(?<![\w.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")


def _domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def numeric_signature(text: str) -> tuple[str, ...]:
    """Normalize numbers so ``1,234.0`` and ``1234`` compare equal."""

    values: list[str] = []
    for raw in NUMBER_RE.findall(text):
        try:
            value = Decimal(raw.replace(",", "")).normalize()
        except InvalidOperation:
            continue
        values.append(format(value, "f"))
    return tuple(values)


@dataclass(frozen=True)
class EchoMention:
    mention_id: str
    carrier_url: str
    origin_source_id: str
    independence_group: str
    claim_key: str
    text: str

    @property
    def domain(self) -> str:
        return _domain(self.carrier_url)

    @property
    def signature(self) -> tuple[str, ...]:
        return numeric_signature(self.text)


@dataclass(frozen=True)
class EchoCluster:
    claim_key: str
    numeric_signature: tuple[str, ...]
    carrier_domains: tuple[str, ...]
    origin_source_ids: tuple[str, ...]
    independence_groups: tuple[str, ...]
    mention_ids: tuple[str, ...]
    counted_source_count: int
    review_status: str = "待人工复核-数字回声草稿"


def cluster_numeric_echoes(mentions: Iterable[EchoMention]) -> list[EchoCluster]:
    """Return only same-claim, same-number clusters spanning two domains.

    Count is the number of distinct ``independence_group`` values, never the
    number of articles/domains.  Empty claim keys and numberless text are not
    clustered, avoiding automatic semantic judgements.
    """

    buckets: dict[tuple[str, tuple[str, ...]], list[EchoMention]] = defaultdict(list)
    for mention in mentions:
        if mention.claim_key and mention.signature and mention.domain:
            buckets[(mention.claim_key, mention.signature)].append(mention)
    clusters: list[EchoCluster] = []
    for (claim_key, signature), bucket in sorted(buckets.items()):
        domains = tuple(sorted({item.domain for item in bucket}))
        if len(domains) < 2:
            continue
        clusters.append(
            EchoCluster(
                claim_key=claim_key,
                numeric_signature=signature,
                carrier_domains=domains,
                origin_source_ids=tuple(sorted({item.origin_source_id for item in bucket})),
                independence_groups=tuple(sorted({item.independence_group for item in bucket})),
                mention_ids=tuple(sorted(item.mention_id for item in bucket)),
                counted_source_count=len({item.independence_group for item in bucket}),
            )
        )
    return clusters
