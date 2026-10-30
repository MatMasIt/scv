"""Timed note banner widget displayed during lecture playback."""

from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QLabel, QWidget
from scv.i18n import t


class NoteBand(QLabel):
    """Notification bar displaying an active note over the video/slides."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize this component and its state."""
        super().__init__(parent)
        self.setWordWrap(True)
        self.setStyleSheet(
            "background: #312e81; color: #eef2ff; padding: 8px 12px; "
            "border-radius: 4px; font-size: 13px; font-weight: 500;"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(t("study_tip"))
        self.hide()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Emit clicked signal when user presses the note banner."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
