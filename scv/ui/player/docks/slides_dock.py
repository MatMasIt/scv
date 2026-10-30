"""Slide thumbnails and timeline navigation dock widget."""

from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
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


class SlidesDockWidget(QWidget):
    """Panel presenting the sequential slide thumbnails and playback progress."""

    slideSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
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
        layout.addWidget(self.thumbs, 1)

    def load_slides(self, slides: list[dict], root_path: Path):
        """Populate the thumbnail list from manifest slides and extracted images."""
        self.thumbs.blockSignals(True)
        self.thumbs.clear()
        for i, slide in enumerate(slides):
            icon = QIcon()
            pix = QPixmap(str(root_path / slide["image"]))
            if not pix.isNull():
                icon = QIcon(
                    pix.scaled(
                        240,
                        135,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            item = QListWidgetItem(
                icon, f'{t("slide_counter", current=i + 1, total=len(slides))}   •   {fmt_time(slide["time"] * 1000)}'
            )
            item.setData(Qt.ItemDataRole.UserRole, slide.get("text", ""))
            if slide.get("text"):
                item.setToolTip(slide.get("text", ""))
            self.thumbs.addItem(item)
        self.thumbs.blockSignals(False)

        self.timeline_progress.show()

    def set_current_slide(self, index: int):
        """Highlight a slide without triggering recursion."""
        if 0 <= index < self.thumbs.count():
            self.thumbs.blockSignals(True)
            self.thumbs.setCurrentRow(index)
            self.thumbs.blockSignals(False)

    def update_progress(self, position_ms: int, duration_ms: int, slide_index: int, total_slides: int):
        """Update progress bar range, current value, and descriptive label."""
        self.timeline_progress.setRange(0, duration_ms)
        self.timeline_progress.setValue(position_ms)
        self.timeline_position.setText(
            f"{t('slide_counter', current=slide_index + 1, total=total_slides)} · "
            f"{fmt_time(position_ms)} / {fmt_time(duration_ms)}"
        )

    def count(self) -> int:
        return self.thumbs.count()

    def item(self, index: int) -> QListWidgetItem | None:
        return self.thumbs.item(index)

    def clear(self):
        """Reset the slides list to empty state."""
        self.thumbs.blockSignals(True)
        self.thumbs.clear()
        self.thumbs.blockSignals(False)
        self.timeline_progress.hide()
        self.timeline_position.setText(t("no_lecture_loaded"))

    def _on_row_changed(self, row: int):
        if row >= 0:
            self.slideSelected.emit(row)
