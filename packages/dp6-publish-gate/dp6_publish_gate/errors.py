class DP6InputError(ValueError):
    """Raised only when the document cannot be decoded as JSON."""


class NonFiniteNumber:
    """Marker used by the JSON loader for NaN/Infinity tokens."""

    def __init__(self, token: str):
        self.token = token

    def __repr__(self) -> str:
        return self.token
