"""Application service for video-to-SCV encoding."""

from __future__ import annotations

from pathlib import Path

from scv.core import Job, Progress, Settings, encode
from scv.core.archive import LectureManifest
from scv.models import EncodeTask


class EncodingService:
    """Validate and execute encoding tasks without any Qt dependency."""

    def encode_task(
        self,
        task: EncodeTask,
        settings: Settings,
        progress: Progress | None = None,
        job: Job | None = None,
    ) -> LectureManifest:
        """Encode one task and update its domain lifecycle."""
        task.mark_encoding()
        try:
            manifest = encode(
                task.source,
                task.destination,
                settings,
                progress=progress,
                job=job,
            )
        except Exception as exc:
            task.mark_failed(str(exc))
            raise
        task.mark_completed()
        return manifest
