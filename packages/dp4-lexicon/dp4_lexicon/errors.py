"""Typed failures for the DP4 mechanical gates."""


class LexiconError(ValueError):
    """Base class for invalid or unmeasurable DP4 input."""


class SchemaError(LexiconError):
    """A lexicon or fixture record does not satisfy its schema."""


class RegexCompilationError(SchemaError):
    """An include or exclude pattern cannot be compiled by :mod:`re`."""


class BareAbbreviationError(SchemaError):
    """A bare abbreviation was submitted without contextual qualification."""


class CellIdCollisionError(SchemaError):
    """A term occupies a reserved cell-id namespace word."""


class FixtureError(LexiconError):
    """A golden fixture is malformed or does not produce its expected result."""
