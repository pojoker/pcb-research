"""DP2 source registry for the PCB research project.

This package records provenance and produces reviewable drafts.  It never
decides that a source is load-bearing, that a T1 endpoint is authoritative, or
that a customs definition is frozen.
"""

from .accessibility import ProbeRecord, probe_t1_sources
from .customs8534 import FreezeCheck, check_8534_freeze
from .echoes import EchoCluster, EchoMention, cluster_numeric_echoes
from .schema import LedgerValidation, validate_ledger_record

__all__ = [
    "EchoCluster",
    "EchoMention",
    "FreezeCheck",
    "LedgerValidation",
    "ProbeRecord",
    "check_8534_freeze",
    "cluster_numeric_echoes",
    "probe_t1_sources",
    "validate_ledger_record",
]
