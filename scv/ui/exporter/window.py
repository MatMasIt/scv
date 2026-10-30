"""Desktop MP4 export window."""

from __future__ import annotations
from pathlib import Path
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QSpinBox,
    QMessageBox,
)

from scv.ui.common.about import show_about
from scv.ui.common.utils import load_app_icon
from scv.i18n import t
from .worker import ExportWorker


class ExportWindow(QMainWindow):
    """Desktop interface for selecting and exporting an SCV archive to MP4."""

    def __init__(
        self,
        initial_src: Path | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize this component and its state."""
        super().__init__(parent)
        self.setWindowTitle(t("exporter_title"))
        self.resize(650, 260)
        self.setWindowIcon(load_app_icon())

        self.worker: ExportWorker | None = None
        self._setup_ui()

        if initial_src:
            self.set_source_path(initial_src)

    def _setup_ui(self) -> None:
        """Build and arrange this widget’s controls."""
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.addWidget(QLabel(t("exporter_desc")))

        self.src = QLineEdit()
        self.dst = QLineEdit()

        for label, line, cb in [
            (t("scv_file"), self.src, self.select_src),
            (t("output_mp4"), self.dst, self.select_dst),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(line, 1)
            button = QPushButton(t("browse"))
            button.clicked.connect(cb)
            row.addWidget(button)
            layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(t("video_quality_crf")))
        self.crf = QSpinBox()
        self.crf.setRange(0, 51)
        self.crf.setValue(20)
        row.addWidget(self.crf)
        layout.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setFormat(t("export_progress"))
        layout.addWidget(self.progress)

        self.status = QLabel(t("ready"))
        layout.addWidget(self.status)

        actions = QHBoxLayout()
        self.start_btn = QPushButton(t("export_mp4"))
        self.start_btn.clicked.connect(self.convert)
        self.cancel_btn = QPushButton(t("cancel"))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_export)
        actions.addWidget(self.start_btn)
        actions.addWidget(self.cancel_btn)
        layout.addLayout(actions)

        help_menu = self.menuBar().addMenu(t("help"))
        about = help_menu.addAction(t("about_and_licenses"))
        about.triggered.connect(lambda: show_about(self, "Exporter"))

    def set_source_path(self, path: Path | str) -> None:
        """Display a source archive and derive its default MP4 path."""
        src_path = str(path)
        self.src.setText(src_path)
        self.dst.setText(str(Path(src_path).with_suffix(".mp4")))

    def select_src(self) -> None:
        """Select the requested src."""
        name, _ = QFileDialog.getOpenFileName(self, t("open_scv"), "", "SCV (*.scv)")
        if name:
            self.set_source_path(name)

    def select_dst(self) -> None:
        """Select the requested dst."""
        name, _ = QFileDialog.getSaveFileName(
            self, t("save_mp4"), self.dst.text(), "MP4 (*.mp4)"
        )
        if name:
            self.dst.setText(name)

    def convert(self) -> QMessageBox.StandardButton | None:
        """Validate export paths and start the MP4 export worker."""
        src_file = Path(self.src.text())
        if not src_file.is_file() or not self.dst.text():
            return QMessageBox.warning(
                self, t("settings_error"), f"{t('scv_file')} {t('output_mp4')}"
            )
        target = Path(self.dst.text())
        if (
            target.exists()
            and QMessageBox.question(self, t("overwrite"), t("overwrite_file", path=target))
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.worker = ExportWorker(self.src.text(), self.dst.text(), self.crf.value())
        self.worker.progress.connect(
            lambda p, m: (
                self.progress.setValue(round(p * 100)),
                self.status.setText(m),
            )
        )
        self.worker.finished_ok.connect(lambda path: self.end(t("exported_msg", path=path)))
        self.worker.failed.connect(lambda error: self.end(t("error_prefix") + error))
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker.start()

    def cancel_export(self) -> None:
        """Cancel the current export."""
        if self.worker:
            self.worker.job.cancel()
        self.cancel_btn.setEnabled(False)

    def end(self, message: str) -> None:
        """Display the export result and restore the action buttons."""
        self.status.setText(message)
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle a request to close this window."""
        if self.worker and self.worker.isRunning():
            self.worker.job.cancel()
            self.worker.wait(3000)
        super().closeEvent(event)
