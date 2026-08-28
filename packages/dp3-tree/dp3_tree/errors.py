"""Errors raised by the DP3 tree contract."""

from __future__ import annotations


class DP3Error(Exception):
    """Base class for expected DP3 input and contract failures."""


class SchemaError(DP3Error):
    """An input object does not match the exact DP3 interchange schema."""


class TreeContractError(DP3Error):
    """The canonical tree violates a structural invariant."""
