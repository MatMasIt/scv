"""Queue list and file management panel component for the Encoder."""

from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QLabel,
    QLineEdit,
    QFileDialog,
)
from scv.i18n import t
from scv.i18n import I18nManager


class QueuePanel(QWidget):
    """Component managing the list of queued videos and their output destinations."""

    filesSelected = Signal(list)
    removeSelected = Signal()
    clearRequested = Signal()
    customOutputRequested = Signal(int)
    defaultFolderChanged = Signal(str)

    def __init__(self, default_folder: str, parent=None):
        super().__init__(parent)
        self.default_folder = default_folder
        self._language_listener = self._on_language_changed
        self._setup_ui()
        I18nManager.get_instance().add_listener(self._language_listener)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Action Buttons
        btn_row = QHBoxLayout()
        self._button_row = btn_row
        self.add_btn = QPushButton(t("add_videos"))
        self.add_btn.clicked.connect(self._browse_files)
        btn_row.addWidget(self.add_btn)

        self.remove_btn = QPushButton(t("remove_selected"))
        self.remove_btn.clicked.connect(self.removeSelected.emit)
        btn_row.addWidget(self.remove_btn)

        self.clear_btn = QPushButton(t("clear"))
        self.clear_btn.clicked.connect(self.clearRequested.emit)
        btn_row.addWidget(self.clear_btn)
        layout.addLayout(btn_row)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setToolTip(t("double_click_set_output"))
        self.list_widget.setMinimumHeight(180)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.itemDoubleClicked.connect(lambda item: self._on_double_clicked())
        layout.addWidget(self.list_widget, 2)

        # Custom Item Output Row
        path_row = QHBoxLayout()
        self._path_hint = QLabel()
        self.set_output_btn = QPushButton(t("set_output_selected"))
        self.set_output_btn.clicked.connect(self._on_double_clicked)
        path_row.addWidget(self.set_output_btn)
        path_row.addWidget(self._path_hint)
        layout.addLayout(path_row)

        # Default Folder Row
        out_row = QHBoxLayout()
        self._output_label = QLabel()
        out_row.addWidget(self._output_label)
        self.output_edit = QLineEdit(self.default_folder)
        self.output_edit.editingFinished.connect(
            lambda: self.defaultFolderChanged.emit(self.output_edit.text())
        )
        out_row.addWidget(self.output_edit, 1)

        self.browse_btn = QPushButton(t("browse"))
        self.browse_btn.clicked.connect(self._browse_folder)
        out_row.addWidget(self.browse_btn)
        layout.addLayout(out_row)
        self.retranslate_ui()

    def _on_language_changed(self, _language: str):
        self.retranslate_ui()

    def retranslate_ui(self):
        """Refresh visible strings after the active language changes."""
        self.add_btn.setText(t("add_videos"))
        self.remove_btn.setText(t("remove_selected"))
        self.clear_btn.setText(t("clear"))
        self.list_widget.setToolTip(t("double_click_set_output"))
        self.set_output_btn.setText(t("set_output_selected"))
        self._path_hint.setText(t("double_click_set_output"))
        self._output_label.setText(t("default_output_folder"))
        self.browse_btn.setText(t("browse"))

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            t("add_videos"),
            str(Path.home()),
            "Videos (*.mp4 *.mkv *.mov *.webm *.avi *.m4v);;All files (*)",
        )
        if files:
            self.filesSelected.emit(files)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, t("default_output_folder"), self.output_edit.text()
        )
        if folder:
            self.output_edit.setText(folder)
            self.defaultFolderChanged.emit(folder)

    def _on_double_clicked(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.customOutputRequested.emit(row)

    def set_enabled_state(self, enabled: bool):
        self.add_btn.setEnabled(enabled)
        self.remove_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self.list_widget.setEnabled(enabled)
        self.set_output_btn.setEnabled(enabled)
        self.output_edit.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)

    def selected_row(self) -> int:
        """Return the selected queue row, or ``-1`` when there is none."""
        return self.list_widget.currentRow()

    def add_item(self, text: str):
        """Append a display item to the queue list."""
        self.list_widget.addItem(text)

    def set_item_text(self, row: int, text: str):
        """Update a queue row when it still exists."""
        item = self.list_widget.item(row)
        if item is not None:
            item.setText(text)

    def remove_rows(self, rows: list[int]):
        """Remove queue rows in descending order."""
        for row in sorted(rows, reverse=True):
            self.list_widget.takeItem(row)

    def clear_items(self):
        """Remove all displayed queue items."""
        self.list_widget.clear()
