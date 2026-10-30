"""Typed errors raised by SCV core services."""


class SCVError(ValueError):
    """Base class for expected SCV domain and format errors."""


class ArchiveError(SCVError):
    """Base class for invalid or unreadable SCV archives."""


class InvalidManifestError(ArchiveError):
    """Raised when an archive manifest violates the SCV format."""


class UnsafeArchiveError(ArchiveError):
    """Raised when an archive contains unsafe paths or oversized content."""
