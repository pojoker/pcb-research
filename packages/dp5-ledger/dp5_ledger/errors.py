"""Domain errors for the DP5 offline validator."""


class DP5Error(Exception):
    """Base class for a controlled DP5 input failure."""


class SchemaError(DP5Error):
    """Raised when an input cannot satisfy the exact DP5 contract."""
