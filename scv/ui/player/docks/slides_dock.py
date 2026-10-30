"""Slide thumbnails and timeline navigation dock widget."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import TypedDict

from PySide6.QtCore import Qt, Signal, QSize, QPoint, QTimer
from PySide6.QtGui import QIcon, QPixmap, QImage, QResizeEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QListWidget,
    QListWidgetItem,
)
from scv.ui.common.utils import fmt_time
from scv.i18n import t
from scv.core import LectureSession
from ..workers import AsyncImageLoader


class SlideInfo(TypedDict):
    """Fields needed by the timeline list for one lecture slide."""

    time: float
    image: str
    text: str


class SlidesDockWidget(QWidget):
    """Panel presenting the sequential slide thumbnails and playback progress."""

    slideSelected = Signal(int)

    def __init__(
        self,
        parent: QWidget | None = None,
        image_loader: AsyncImageLoader | None = None,
    ) -> None:
        """Initialize the slide timeline and its bounded thumbnail cache."""
        super().__init__(parent)
        self._image_loader = image_loader or AsyncImageLoader(self)
        self._image_loader.image_loaded.connect(self._on_thumbnail_loaded)
        self._slide_paths: list[Path] = []
        self._resource_owner: LectureSession | None = None
        self._generation = 0
        self._wanted_indices: list[int] = []
        self._active_thumbnail_requests: set[tuple[str, int, int]] = set()
        self._failed_indices: set[int] = set()
        self._icon_rows: set[int] = set()
        self._thumbnail_cache: OrderedDict[int, QImage] = OrderedDict()
        self._thumbnail_cache_limit = 48
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the timeline progress display and scrollable slide list."""
        layout = QVBoxLayout(self)

        timeline_title = QLabel(t("timeline_title"))
        timeline_title.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(timeline_title)

        self.timeline_progress = QProgressBar()
        self.timeline_progress.setRange(0, 1)
        self.timeline_progress.setValue(0)
        self.timeline_progress.setTextVisible(False)
        self.timeline_progress.hide()
        layout.addWidget(self.timeline_progress)

        self.timeline_position = QLabel(t("no_lecture_loaded"))
        self.timeline_position.setStyleSheet("color: #6b7280;")
        layout.addWidget(self.timeline_position)

        self.thumbs = QListWidget()
        self.thumbs.setIconSize(QSize(240, 135))
        self.thumbs.setMinimumWidth(290)
        self.thumbs.setSpacing(9)
        self.thumbs.setStyleSheet("QListWidget::item { padding: 8px; margin: 4px; }")
        self.thumbs.currentRowChanged.connect(self._on_row_changed)
        self.thumbs.verticalScrollBar().valueChanged.connect(self._schedule_thumbnail_refresh)
        layout.addWidget(self.thumbs, 1)

    def load_slides(
        self,
        slides: list[SlideInfo],
        root_path: Path,
        resource_owner: LectureSession | None = None,
    ) -> None:
        """Populate rows immediately and load visible thumbnails in the background."""
        self._generation += 1
        self._thumbnail_cache.clear()
        self._failed_indices.clear()
        self._wanted_indices.clear()
        for row in self._icon_rows:
            item = self.thumbs.item(row)
            if item:
                item.setIcon(QIcon())
        self._icon_rows.clear()
        self._slide_paths = [root_path / slide["image"] for slide in slides]
        self._resource_owner = resource_owner

        self.thumbs.blockSignals(True)
        self.thumbs.clear()
        for i, slide in enumerate(slides):
            item = QListWidgetItem(
                f'{t("slide_counter", current=i + 1, total=len(slides))}   •   {fmt_time(slide["time"] * 1000)}'
            )
            item.setData(Qt.ItemDataRole.UserRole, slide.get("text", ""))
            if slide.get("text"):
                item.setToolTip(slide.get("text", ""))
            self.thumbs.addItem(item)
        self.thumbs.blockSignals(False)

        self.timeline_progress.show()
        self._schedule_thumbnail_refresh()

    def set_current_slide(self, index: int) -> None:
        """Highlight a slide without triggering recursion."""
        if 0 <= index < self.thumbs.count():
            self.thumbs.blockSignals(True)
            self.thumbs.setCurrentRow(index)
            self.thumbs.blockSignals(False)
            self._schedule_thumbnail_refresh()

    def update_progress(
        self, position_ms: int, duration_ms: int, slide_index: int, total_slides: int
    ) -> None:
        """Update progress bar range, current value, and descriptive label."""
        self.timeline_progress.setRange(0, duration_ms)
        self.timeline_progress.setValue(position_ms)
        self.timeline_position.setText(
            f"{t('slide_counter', current=slide_index + 1, total=total_slides)} · "
            f"{fmt_time(position_ms)} / {fmt_time(duration_ms)}"
        )

    def count(self) -> int:
        """Return the number of slide rows in the timeline."""
        return self.thumbs.count()

    def item(self, index: int) -> QListWidgetItem | None:
        """Return the timeline item at ``index`` when it exists."""
        return self.thumbs.item(index)

    def clear(self) -> None:
        """Reset the slides list to empty state."""
        self._generation += 1
        self._slide_paths.clear()
        self._resource_owner = None
        self._thumbnail_cache.clear()
        self._wanted_indices.clear()
        self._failed_indices.clear()
        self._icon_rows.clear()
        self.thumbs.blockSignals(True)
        self.thumbs.clear()
        self.thumbs.blockSignals(False)
        self.timeline_progress.hide()
        self.timeline_position.setText(t("no_lecture_loaded"))

    def _on_row_changed(self, row: int) -> None:
        """Emit the selected slide index and refresh visible thumbnails."""
        if row >= 0:
            self.slideSelected.emit(row)
            self._schedule_thumbnail_refresh()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Refresh thumbnail requests after the dock is resized."""
        super().resizeEvent(event)
        self._schedule_thumbnail_refresh()

    def _schedule_thumbnail_refresh(self, *_: object) -> None:
        """Schedule a coalesced visible-thumbnail refresh on the event loop."""
        QTimer.singleShot(0, self._refresh_visible_thumbnails)

    def _refresh_visible_thumbnails(self) -> None:
        """Load thumbnails around the visible rows and evict offscreen icons."""
        if not self._slide_paths or not self.thumbs.count():
            return

        viewport = self.thumbs.viewport()
        first = self.thumbs.indexAt(QPoint(8, 2)).row()
        last = self.thumbs.indexAt(QPoint(8, max(2, viewport.height() - 2))).row()
        if first < 0:
            first = max(0, self.thumbs.currentRow())
        if last < first:
            last = min(self.thumbs.count() - 1, first + 8)

        start = max(0, first - 3)
        end = min(self.thumbs.count(), last + 4)
        self._wanted_indices = list(range(start, end))
        wanted = set(self._wanted_indices)

        for row in self._icon_rows - wanted:
            item = self.thumbs.item(row)
            if item:
                item.setIcon(QIcon())
        self._icon_rows.intersection_update(wanted)

        for index in self._wanted_indices:
            cached = self._thumbnail_cache.get(index)
            if cached is not None:
                self._thumbnail_cache.move_to_end(index)
                self._set_thumbnail_icon(index, cached)

        self._pump_thumbnail_requests()

    def _queue_thumbnail(self, generation: int, index: int) -> None:
        """Queue one thumbnail decode for the requested generation and row."""
        key = ("thumbnail", generation, index)
        if key in self._active_thumbnail_requests:
            return
        # The pump only queues a small visible batch, keeping the worker queue bounded.
        self._active_thumbnail_requests.add(key)
        self._image_loader.load(
            key,
            self._slide_paths[index],
            QSize(240, 135),
            resource_owner=self._resource_owner,
        )

    def _pump_thumbnail_requests(self) -> None:
        """Keep at most two thumbnail decode tasks active at once."""
        active_count = len(self._active_thumbnail_requests)
        for index in self._wanted_indices:
            if active_count >= 2:
                break
            key = ("thumbnail", self._generation, index)
            if (
                index in self._thumbnail_cache
                or index in self._failed_indices
                or key in self._active_thumbnail_requests
            ):
                continue
            self._queue_thumbnail(self._generation, index)
            active_count += 1

    def _on_thumbnail_loaded(
        self, key: object, image: QImage, error: str
    ) -> None:
        """Cache a thumbnail result and display it if its row is visible."""
        if not isinstance(key, tuple) or len(key) != 3 or key[0] != "thumbnail":
            return
        _, generation, index = key
        self._active_thumbnail_requests.discard(key)
        if generation != self._generation:
            self._pump_thumbnail_requests()
            return
        if image.isNull():
            self._failed_indices.add(index)
        else:
            self._thumbnail_cache[index] = image
            self._thumbnail_cache.move_to_end(index)
            while len(self._thumbnail_cache) > self._thumbnail_cache_limit:
                self._thumbnail_cache.popitem(last=False)
            if index in self._wanted_indices:
                self._set_thumbnail_icon(index, image)
        self._pump_thumbnail_requests()

    def _set_thumbnail_icon(self, index: int, image: QImage) -> None:
        """Set a row's icon once from its decoded thumbnail image."""
        item = self.thumbs.item(index)
        if item is None or index in self._icon_rows:
            return
        item.setIcon(QIcon(QPixmap.fromImage(image)))
        self._icon_rows.add(index)
