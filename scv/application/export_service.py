"""Application service for SCV-to-MP4 export."""

from __future__ import annotations

from pathlib import Path

from scv.core import Job, Progress
from scv.exporter import export_video


class ExportService:
    """Execute MP4 exports without depending on Qt."""

    def export(
        self,
        source: Path | str,
        destination: Path | str,
        crf: int = 20,
        progress: Progress | None = None,
        job: Job | None = None,
    ) -> Path:
        """Export an SCV archive to MP4."""
        return export_video(
            source,
            destination,
            crf=crf,
            progress=progress,
            job=job,
        )
