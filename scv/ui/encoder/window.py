"""Desktop batch encoder window assembled from focused UI components."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QFileDialog,
    QMessageBox,
)

from scv.config import ConfigManager
from scv.core import Settings
from scv.i18n import t
from scv.models import EncodeTask
from scv.ui.common.about import show_about
from scv.ui.common.utils import load_app_icon

from .components import OptionsPanel, ProgressPanel, QueuePanel
from .worker import QueueWorker


class EncoderWindow(QMainWindow):
    """Coordinate encoder panels, queue validation, and the worker lifecycle."""

    VIDEO_FILTER = "Videos (*.mp4 *.mkv *.mov *.webm *.avi *.m4v);;All files (*)"
    SCV_FILTER = "SCV (*.scv)"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize this component and its state."""
        super().__init__(parent)
        self.setWindowTitle(t("encoder_title"))
        self.resize(820, 650)
        self.setAcceptDrops(True)
        self.setWindowIcon(load_app_icon())

        self.config_mgr = ConfigManager.get_instance()
        self.worker: QueueWorker | None = None
        self.queue: list[EncodeTask] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build and arrange this widget’s controls."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header = QLabel(t("encoder_title"))
        header.setStyleSheet("font-size: 22px; font-weight: 700; margin: 8px 0;")
        layout.addWidget(header)
        layout.addWidget(QLabel(t("encoder_drag_hint")))

        settings = self.config_mgr.settings
        self.queue_panel = QueuePanel(
            settings.default_output_dir or str(Path.home() / "Videos")
        )
        self.options_panel = OptionsPanel(
            settings.default_preset,
            settings.default_ocr_lang,
        )
        self.progress_panel = ProgressPanel()

        layout.addWidget(self.queue_panel, 2)
        layout.addWidget(self.options_panel)
        layout.addWidget(self.progress_panel)

        self._connect_panels()
        self._setup_menu()

        # Compatibility aliases for callers that accessed the old window fields.
        self.list = self.queue_panel.list_widget
        self.output = self.queue_panel.output_edit
        self.add_btn = self.queue_panel.add_btn
        self.start_btn = self.progress_panel.start_btn
        self.cancel_btn = self.progress_panel.cancel_btn
        self.progress = self.progress_panel.total_progress
        self.file_progress = self.progress_panel.file_progress
        self.status = self.progress_panel.status_label

    def _connect_panels(self) -> None:
        """Connect panel signals to queue and worker operations."""
        self.queue_panel.filesSelected.connect(self.add_paths)
        self.queue_panel.removeSelected.connect(self.remove_selected)
        self.queue_panel.clearRequested.connect(self.clear_queue)
        self.queue_panel.customOutputRequested.connect(self.set_item_output)
        self.queue_panel.defaultFolderChanged.connect(self._set_output_directory)
        self.progress_panel.startRequested.connect(self.start)
        self.progress_panel.cancelRequested.connect(self.cancel)

    def _setup_menu(self) -> None:
        """Create the Help menu and its About action."""
        about_action = QAction(t("about_and_licenses"), self)
        about_action.triggered.connect(lambda: show_about(self, "Encoder"))
        self.menuBar().addMenu(t("help")).addAction(about_action)

    def _set_output_directory(self, directory: str) -> None:
        """Persist a changed default output directory."""
        if directory != self.config_mgr.settings.default_output_dir:
            self.config_mgr.update(default_output_dir=directory)

    def add_files(self) -> None:
        """Add the requested files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            t("select_video_files"),
            str(Path.home()),
            self.VIDEO_FILTER,
        )
        self.add_paths(files)

    def add_paths(self, paths: list[str | Path]) -> None:
        """Add the requested paths."""
        output_dir = Path(self.queue_panel.output_edit.text()).expanduser()
        for path in paths:
            source = Path(path).expanduser()
            if not source.is_file() or any(item.source == source for item in self.queue):
                continue
            destination = output_dir / f"{source.stem}.scv"
            self.queue.append(EncodeTask(source, destination))
            self.queue_panel.add_item(self._waiting_text(source, destination))

    def set_item_output(self, row: int | None = None) -> None:
        """Choose and apply a custom output path for one queued video."""
        if self._is_running():
            return
        row = self.queue_panel.selected_row() if row is None else row
        if row < 0 or row >= len(self.queue):
            return

        task = self.queue[row]
        source, destination = task.source, task.destination
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("output_scv_for", name=source.name),
            str(destination),
            self.SCV_FILTER,
        )
        if path:
            target = Path(path)
            if target.suffix.lower() != ".scv":
                target = target.with_suffix(".scv")
            task.destination = target
            self.queue_panel.set_item_text(row, self._waiting_text(source, target))

    def remove_selected(self) -> None:
        """Remove the requested selected."""
        if self._is_running():
            return
        rows = [self.queue_panel.list_widget.row(item) for item in self.queue_panel.list_widget.selectedItems()]
        self.queue_panel.remove_rows(rows)
        for row in sorted(rows, reverse=True):
            self.queue.pop(row)

    def clear_queue(self) -> None:
        """Clear the current queue state."""
        if self._is_running():
            return
        self.queue.clear()
        self.queue_panel.clear_items()

    def pick_output(self) -> None:
        """Choose and display the default output directory."""
        folder = QFileDialog.getExistingDirectory(
            self,
            t("output_folder"),
            self.queue_panel.output_edit.text(),
        )
        if folder:
            self.queue_panel.output_edit.setText(folder)

    def current_settings(self) -> Settings:
        """Return validated settings represented by the options panel."""
        return self.options_panel.get_settings()

    def apply_preset(self, name: str) -> None:
        """Apply a named preset through the options component."""
        self.options_panel.apply_preset(name)

    def change_mode(self, index: int) -> None:
        """Change the advanced-options visibility through the options component."""
        self.options_panel.mode_combo.setCurrentIndex(index)

    def ocr_toggled(self, enabled: bool) -> None:
        """Toggle OCR through the options component."""
        self.options_panel.ocr_check.setChecked(enabled)

    def check_tesseract(self) -> bool:
        """Check Tesseract through the options component."""
        return self.options_panel.check_tesseract()

    def start(self) -> None:
        """Validate the queue and start the encoder worker."""
        if not self.queue:
            QMessageBox.information(self, t("no_videos"), t("add_videos_first"))
            return

        try:
            output_dir = Path(self.queue_panel.output_edit.text()).expanduser()
            output_dir.mkdir(parents=True, exist_ok=True)
            if not output_dir.is_dir():
                raise ValueError(t("output_not_directory"))
            settings = self.current_settings()
            settings.validate()
            if settings.ocr and not self.options_panel.check_tesseract():
                raise ValueError(t("tesseract_unavailable"))
            self._validate_destinations()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, t("settings_error"), str(exc))
            return

        if any(task.destination.exists() for task in self.queue):
            response = QMessageBox.question(
                self, t("overwrite"), t("overwrite_outputs")
            )
            if response != QMessageBox.StandardButton.Yes:
                return

        self.worker = QueueWorker(self.queue, settings)
        self.worker.progress.connect(self._update_progress)
        self.worker.item_done.connect(self._complete_item)
        self.worker.item_failed.connect(self._fail_item)
        self.worker.queue_done.connect(self._finish_queue)
        self.worker.queue_failed.connect(self._fail_queue)
        self.queue_panel.set_enabled_state(False)
        self.progress_panel.set_running_state(True)
        self.worker.start()

    def cancel(self) -> None:
        """Request cancellation of the active queue worker."""
        if self.worker:
            self.worker.stop()
        self.progress_panel.set_running_state(False)
        self.progress_panel.status_label.setText(t("cancelling"))

    def _validate_destinations(self) -> None:
        """Reject duplicate output destinations in the current queue."""
        destinations = [str(task.destination.resolve()) for task in self.queue]
        if len(set(destinations)) != len(destinations):
            raise ValueError(t("duplicate_output_msg"))

    def _update_progress(self, index: int, value: float, description: str) -> None:
        """Update the progress state."""
        total = round(100 * (index + value) / len(self.queue))
        self.progress_panel.update_progress(total, round(value * 100), f"{index + 1}/{len(self.queue)} · {description}")
        source = self.queue[index].source
        self.queue_panel.set_item_text(index, f"Encoding {value * 100:.0f}%  •  {source.name}")

    def update_progress(self, index: int, value: float, description: str) -> None:
        """Compatibility entry point for worker progress callbacks."""
        self._update_progress(index, value, description)

    def _complete_item(self, index: int, destination: str) -> None:
        """Mark one queue item as successfully encoded."""
        source = self.queue[index].source
        self.queue_panel.set_item_text(index, f"✓  {source.name}  →  {Path(destination).name}")

    def done_one(self, index: int, destination: str) -> None:
        """Compatibility entry point for completed queue items."""
        self._complete_item(index, destination)

    def _fail_item(self, index: int, error: str) -> None:
        """Display the failure details for one queue item."""
        source = self.queue[index].source
        self.queue_panel.set_item_text(index, f"✕  {source.name}  -  {error[:110]}")
        self.progress_panel.status_label.setText(error[:200])

    def failed_one(self, index: int, error: str) -> None:
        """Compatibility entry point for failed queue items."""
        self._fail_item(index, error)

    def _finish_queue(self) -> None:
        """Restore queue controls after the worker finishes."""
        self.queue_panel.set_enabled_state(True)
        self.progress_panel.set_running_state(False)
        if not (self.worker and self.worker.stop_requested):
            self.progress_panel.status_label.setText(t("queue_finished"))

    def finished(self) -> None:
        """Compatibility entry point for successful queue completion."""
        self._finish_queue()

    def _fail_queue(self) -> None:
        """Restore queue controls after the worker reports a queue error."""
        self.queue_panel.set_enabled_state(True)
        self.progress_panel.set_running_state(False)
        self.progress_panel.status_label.setText(t("queue_stopped_error"))

    def failed(self) -> None:
        """Compatibility entry point for failed queue completion."""
        self._fail_queue()

    def _is_running(self) -> bool:
        """Return whether the encoder worker is currently running."""
        return bool(self.worker and self.worker.isRunning())

    @staticmethod
    def _waiting_text(source: Path, destination: Path) -> str:
        """Format the initial queue label for one encoding task."""
        return f"Waiting • {source.name} → {destination}"

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept supported file drag operations."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle supported files dropped onto this window."""
        self.add_paths(
            [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle a request to close this window."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        super().closeEvent(event)
