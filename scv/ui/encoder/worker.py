"""Background worker thread for batch video encoding."""

from __future__ import annotations
from PySide6.QtCore import QThread, Signal
from scv.core import Job, Settings
from scv.application import EncodingService
from scv.models import EncodeTask


class QueueWorker(QThread):
    """Encode queue items sequentially without blocking the Qt event loop."""

    progress = Signal(int, float, str)
    item_done = Signal(int, str)
    item_failed = Signal(int, str)
    queue_done = Signal()
    queue_failed = Signal()

    def __init__(self, items: list[EncodeTask], settings: Settings):
        super().__init__()
        self.items = list(items)
        self.settings = settings
        self.job = Job()
        self.stop_requested = False
        self.service = EncodingService()

    def stop(self):
        """Cancel the current conversion and stop processing the queue."""
        self.stop_requested = True
        self.job.cancel()

    def run(self):
        """Encode queued items and emit progress and completion signals."""
        for index, task in enumerate(self.items):
            if self.stop_requested:
                break
            self.job = Job()
            try:
                self.service.encode_task(
                    task,
                    self.settings,
                    progress=lambda p, desc, i=index: self._report_progress(i, p, desc),
                    job=self.job,
                )
                self.item_done.emit(index, str(task.destination))
            except Exception as exc:
                self.item_failed.emit(index, str(exc))
                self.stop_requested = True
                self.queue_failed.emit()
                break
        self.queue_done.emit()

    def _report_progress(self, index: int, value: float, description: str):
        """Update the task model before forwarding progress to Qt."""
        self.items[index].progress = max(0.0, min(1.0, value))
        self.progress.emit(index, value, description)
