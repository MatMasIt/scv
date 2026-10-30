"""Timeline slider widget with slide boundary and bookmark/note markers."""

from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QPaintEvent
from PySide6.QtWidgets import QSlider, QWidget


class TimelineSlider(QSlider):
    """Horizontal slider that paints slide-change and study markers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create a timeline slider with empty marker lists."""
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.markers: list[float] = []
        self.bookmark_markers: list[float] = []
        self.note_markers: list[float] = []

    def set_markers(self, markers: list[float]) -> None:
        """Set slide transition marker positions as fractions between 0 and 1."""
        self.markers = markers
        self.update()

    def set_study_markers(self, bookmarks: list[float], notes: list[float]) -> None:
        """Set bookmark and note positions as fractions between 0 and 1."""
        self.bookmark_markers = bookmarks
        self.note_markers = notes
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the standard slider with custom overlay markers."""
        super().paintEvent(event)
        if not self.maximum():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        # Slide transition ticks (orange)
        painter.setPen(QPen(QColor("#f59e0b"), 1))
        for marker in self.markers:
            x = round(marker * (self.width() - 1))
            painter.drawLine(x, 2, x, self.height() - 2)
        # Bookmark ticks (blue)
        painter.setPen(QPen(QColor("#60a5fa"), 2))
        for marker in self.bookmark_markers:
            x = round(marker * (self.width() - 1))
            painter.drawLine(x, 1, x, self.height() - 1)
        # Note ticks (purple)
        painter.setPen(QPen(QColor("#a78bfa"), 2))
        for marker in self.note_markers:
            x = round(marker * (self.width() - 1))
            painter.drawLine(x, 1, x, self.height() - 1)
