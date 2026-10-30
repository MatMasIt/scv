"""Domain model for queued encoding tasks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class EncodeTaskStatus(str, Enum):
    """Lifecycle state of one encoding task."""

    WAITING = "waiting"
    ENCODING = "encoding"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EncodeTask:
    """One source video and its destination archive."""

    source: Path
    destination: Path
    status: EncodeTaskStatus = EncodeTaskStatus.WAITING
    progress: float = 0.0
    error: str | None = None

    def mark_encoding(self, progress: float = 0.0):
        """Mark this task as active and update its progress."""
        self.status = EncodeTaskStatus.ENCODING
        self.progress = max(0.0, min(1.0, progress))
        self.error = None

    def mark_completed(self):
        """Mark this task as successfully completed."""
        self.status = EncodeTaskStatus.COMPLETED
        self.progress = 1.0
        self.error = None

    def mark_failed(self, error: str):
        """Mark this task as failed with a user-facing error."""
        self.status = EncodeTaskStatus.FAILED
        self.error = error
