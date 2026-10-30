"""Background workers for loading lecture archives and slide images."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, QSize
from PySide6.QtGui import QImage, QImageReader

from scv.core import LectureSession

ImageLoadKey = tuple[str, int, int]


class _ImageTaskSignals(QObject):
    finished = Signal(int, object, object, str)


class _ImageTask(QRunnable):
    def __init__(
        self,
        task_id: int,
        key: ImageLoadKey,
        path: Path,
        size: QSize | None,
        resource_owner: LectureSession | None = None,
    ) -> None:
        """Prepare one image read without performing work on the UI thread."""
        super().__init__()
        self.task_id = task_id
        self.key = key
        self.path = path
        self.size = size
        self.resource_owner = resource_owner
        self.signals = _ImageTaskSignals()

    def run(self) -> None:
        """Decode the source image and emit the result through the task signal."""
        reader = QImageReader(str(self.path))
        reader.setAutoTransform(True)
        if self.size and not reader.size().isEmpty():
            reader.setScaledSize(
                reader.size().scaled(self.size, Qt.AspectRatioMode.KeepAspectRatio)
            )
        image = reader.read()
        self.signals.finished.emit(
            self.task_id,
            self.key,
            image,
            "" if not image.isNull() else reader.errorString(),
        )


class AsyncImageLoader(QObject):
    """Read images off the UI thread and return QImages to the owning thread."""

    image_loaded = Signal(object, object, str)

    def __init__(self, parent: QObject | None = None) -> None:
        """Create an image loader backed by Qt's shared worker pool."""
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._next_task_id = 0
        self._tasks: dict[int, _ImageTask] = {}

    def load(
        self,
        key: ImageLoadKey,
        path: Path,
        size: QSize | None = None,
        priority: int = 0,
        resource_owner: LectureSession | None = None,
    ) -> None:
        """Queue an image decode and emit its key and result on completion."""
        self._next_task_id += 1
        task_id = self._next_task_id
        task = _ImageTask(task_id, key, path, size, resource_owner)
        task.signals.finished.connect(self._on_task_finished)
        self._tasks[task_id] = task
        self._pool.start(task, priority)

    def _on_task_finished(
        self, task_id: int, key: object, image: QImage, error: str
    ) -> None:
        """Remove a completed task and forward its image result."""
        self._tasks.pop(task_id, None)
        self.image_loaded.emit(key, image, error)

    def has_active_loads_under(self, root: Path) -> bool:
        """Return whether an active decode still reads from ``root``."""
        root = root.resolve()
        for task in self._tasks.values():
            try:
                task.path.resolve().relative_to(root)
            except ValueError:
                continue
            return True
        return False


class _LectureTaskSignals(QObject):
    finished = Signal(int, object, object)


class _LectureTask(QRunnable):
    def __init__(self, request_id: int, path: Path) -> None:
        """Prepare one archive-open task."""
        super().__init__()
        self.request_id = request_id
        self.path = path
        self.signals = _LectureTaskSignals()

    def run(self) -> None:
        """Open the lecture archive and report either its session or error."""
        try:
            session = LectureSession.open(self.path)
            error = None
        except Exception as exc:
            session = None
            error = exc
        self.signals.finished.emit(self.request_id, session, error)


class AsyncLectureLoader(QObject):
    """Open and extract SCV archives without blocking the player window."""

    lecture_loaded = Signal(int, object, object)

    def __init__(self, parent: QObject | None = None) -> None:
        """Create a serialized asynchronous lecture archive loader."""
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._tasks: dict[int, _LectureTask] = {}
        self._active = False
        self._queued_request: tuple[int, Path] | None = None

    def load(self, request_id: int, path: Path) -> None:
        """Load a lecture now or replace the single queued request."""
        if self._active:
            self._queued_request = (request_id, path)
            return
        self._start(request_id, path)

    def _start(self, request_id: int, path: Path) -> None:
        """Start archive extraction in the shared worker pool."""
        task = _LectureTask(request_id, path)
        task.signals.finished.connect(self._on_task_finished)
        self._tasks[request_id] = task
        self._active = True
        self._pool.start(task)

    def _on_task_finished(
        self,
        request_id: int,
        session: LectureSession | None,
        error: Exception | None,
    ) -> None:
        """Forward a finished load and then start the latest queued request."""
        self._tasks.pop(request_id, None)
        self._active = False
        queued_request = self._queued_request
        self._queued_request = None
        self.lecture_loaded.emit(request_id, session, error)
        if queued_request is not None and not self._active:
            queued_request_id, queued_path = queued_request
            self._start(queued_request_id, queued_path)
