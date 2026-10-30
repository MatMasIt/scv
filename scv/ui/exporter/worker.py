"""Background worker thread for MP4 export."""

from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from scv.core import Job
from scv.application import ExportService


class ExportWorker(QThread):
    """Run one SCV-to-MP4 conversion outside the GUI thread."""

    progress = Signal(float, str)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, src: Path | str, dest: Path | str, crf: int) -> None:
        """Initialize this component and its state."""
        super().__init__()
        self.src, self.dest, self.crf = src, dest, crf
        self.job = Job()
        self.service = ExportService()

    def run(self) -> None:
        """Run this background operation."""
        try:
            self.service.export(
                self.src,
                self.dest,
                crf=self.crf,
                progress=lambda n, m: self.progress.emit(n, m),
                job=self.job,
            )
            self.finished_ok.emit(str(self.dest))
        except Exception as exc:
            self.failed.emit(str(exc))
