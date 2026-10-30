"""Progress reporting and conversion control panel for the Encoder."""

from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
    QLabel,
    QPushButton,
)
from scv.i18n import t
from scv.i18n import I18nManager


class ProgressPanel(QWidget):
    """Component showing overall queue progress, current file progress, and action buttons."""

    startRequested = Signal()
    cancelRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize this component and its state."""
        super().__init__(parent)
        self._language_listener = self._on_language_changed
        self._setup_ui()
        I18nManager.get_instance().add_listener(self._language_listener)

    def _setup_ui(self) -> None:
        """Build and arrange this widget’s controls."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)

        self.total_progress = QProgressBar()
        self.total_progress.setRange(0, 100)
        layout.addWidget(self.total_progress)

        self.file_progress = QProgressBar()
        self.file_progress.setRange(0, 100)
        self.file_progress.setFormat(t("current_file"))
        layout.addWidget(self.file_progress)

        self.status_label = QLabel(t("ready"))
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton(t("convert_queue"))
        self.start_btn.clicked.connect(self.startRequested.emit)
        btn_row.addWidget(self.start_btn)

        self.cancel_btn = QPushButton(t("cancel"))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancelRequested.emit)
        btn_row.addWidget(self.cancel_btn)

        layout.addLayout(btn_row)

    def _on_language_changed(self, _language: str) -> None:
        """Handle changes to language."""
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        """Refresh visible strings after the active language changes."""
        self.file_progress.setFormat(t("current_file"))
        self.start_btn.setText(t("convert_queue"))
        self.cancel_btn.setText(t("cancel"))
        if not self.start_btn.isEnabled() and self.cancel_btn.isEnabled():
            return
        self.status_label.setText(t("ready"))

    def set_running_state(self, is_running: bool) -> None:
        """Switch progress controls between idle and running states."""
        self.start_btn.setEnabled(not is_running)
        self.cancel_btn.setEnabled(is_running)

    def update_progress(self, total_percent: int, file_percent: int, status_text: str) -> None:
        """Update the progress state."""
        self.total_progress.setValue(total_percent)
        self.file_progress.setValue(file_percent)
        self.status_label.setText(status_text)
