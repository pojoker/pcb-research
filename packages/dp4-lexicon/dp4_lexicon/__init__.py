"""DP4 lexicon measurement utilities.

The package is deliberately limited to mechanical validation and measurement.
It never promotes a candidate into a canonical vocabulary.
"""

from .corpus import CorpusDocument, CorpusScan, CorpusScanner, Measurement
from .errors import (
    BareAbbreviationError,
    CellIdCollisionError,
    FixtureError,
    LexiconError,
    RegexCompilationError,
    SchemaError,
)
from .fixtures import Fixture, GoldenResult, run_golden_fixtures
from .schema import LexiconEntry, load_lexicon, load_json_records
from .validation import (
    RESERVED_CELL_IDS,
    SPECIAL_TARGET_CELLS,
    compile_gate,
    validate_cell_id,
    validate_entries,
)

__all__ = [
    "BareAbbreviationError",
    "CellIdCollisionError",
    "CorpusDocument",
    "CorpusScan",
    "CorpusScanner",
    "Fixture",
    "FixtureError",
    "GoldenResult",
    "LexiconEntry",
    "LexiconError",
    "Measurement",
    "RegexCompilationError",
    "RESERVED_CELL_IDS",
    "SPECIAL_TARGET_CELLS",
    "SchemaError",
    "compile_gate",
    "load_json_records",
    "load_lexicon",
    "run_golden_fixtures",
    "validate_cell_id",
    "validate_entries",
]
