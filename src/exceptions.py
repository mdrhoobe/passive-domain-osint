"""Typed errors used at the CLI and collection boundaries."""

class ValidationError(ValueError):
    """Domain input is not a supported DNS name or bare HTTPS/HTTP URL."""

class CollectorError(RuntimeError):
    """A source could not be queried or parsed."""

class SourceUnavailable(CollectorError):
    """A public data source timed out or could not be reached."""

class SourceResponseError(CollectorError):
    """A public source returned unusable data."""
