"""Settings and preferences dialog."""

from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QFormLayout,
)

from scv.config import ConfigManager, AppSettings
from scv.core import PRESETS
from scv.i18n import t, get_available_languages


class SettingsDialog(QDialog):
    """Application preferences dialog with tabbed categories."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize this component and its state."""
        super().__init__(parent)
        self.setWindowTitle(t("settings_title"))
        self.resize(520, 380)
        self.setModal(True)

        self.config_mgr = ConfigManager.get_instance()
        self.current_settings = self.config_mgr.settings

        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        """Build and arrange this widget’s controls."""
        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_general_tab(), t("tab_general"))
        self.tabs.addTab(self._create_player_tab(), t("tab_player"))
        self.tabs.addTab(self._create_encoding_tab(), t("tab_encoding_export"))
        main_layout.addWidget(self.tabs, 1)

        # Dialog buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        self.cancel_btn = QPushButton(t("btn_cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton(t("btn_save"))
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(self.save_btn)

        main_layout.addLayout(btn_layout)

    def _create_general_tab(self) -> QWidget:
        """Build the tab for language and theme preferences."""
        widget = QWidget()
        form = QFormLayout(widget)

        self.lang_combo = QComboBox()
        for code, name in get_available_languages().items():
            self.lang_combo.addItem(name, code)
        form.addRow(t("setting_language"), self.lang_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(t("setting_theme_system"), "system")
        self.theme_combo.addItem(t("setting_theme_dark"), "dark")
        self.theme_combo.addItem(t("setting_theme_light"), "light")
        form.addRow(t("setting_theme"), self.theme_combo)

        return widget

    def _create_player_tab(self) -> QWidget:
        """Build the tab for playback, seeking, and study preferences."""
        widget = QWidget()
        form = QFormLayout(widget)

        self.speed_combo = QComboBox()
        for s in ("0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"):
            self.speed_combo.addItem(s, float(s[:-1]))
        form.addRow(t("setting_playback_speed"), self.speed_combo)

        self.seek_step = QSpinBox()
        self.seek_step.setRange(1, 60)
        self.seek_step.setSuffix(" s")
        form.addRow(t("setting_seek_step"), self.seek_step)

        self.note_duration = QSpinBox()
        self.note_duration.setRange(5, 120)
        self.note_duration.setSuffix(" s")
        form.addRow(t("setting_note_duration"), self.note_duration)

        self.auto_save_check = QCheckBox(t("setting_auto_save"))
        form.addRow("", self.auto_save_check)

        self.resume_playback_check = QCheckBox(t("setting_resume_playback"))
        form.addRow("", self.resume_playback_check)

        return widget

    def _create_encoding_tab(self) -> QWidget:
        """Build the tab for encoding, export, and OCR defaults."""
        widget = QWidget()
        form = QFormLayout(widget)

        dir_row = QHBoxLayout()
        self.output_dir = QLineEdit()
        dir_row.addWidget(self.output_dir, 1)
        browse_btn = QPushButton(t("browse"))
        browse_btn.clicked.connect(self._browse_output_dir)
        dir_row.addWidget(browse_btn)
        form.addRow(t("setting_output_dir"), dir_row)

        self.preset_combo = QComboBox()
        for p in PRESETS:
            self.preset_combo.addItem(p, p)
        form.addRow(t("setting_default_preset"), self.preset_combo)

        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        form.addRow(t("setting_default_crf"), self.crf_spin)

        self.ocr_lang_combo = QComboBox()
        self.ocr_lang_combo.addItem("English", "eng")
        self.ocr_lang_combo.addItem("Italian", "ita")
        self.ocr_lang_combo.addItem("French", "fra")
        self.ocr_lang_combo.addItem("German", "deu")
        self.ocr_lang_combo.addItem("Spanish", "spa")
        self.ocr_lang_combo.addItem("Portuguese", "por")
        form.addRow(t("setting_default_ocr_lang"), self.ocr_lang_combo)

        return widget

    def _browse_output_dir(self) -> None:
        """Choose an output directory and update the path field."""
        folder = QFileDialog.getExistingDirectory(
            self, t("setting_output_dir"), self.output_dir.text()
        )
        if folder:
            self.output_dir.setText(folder)

    def _load_values(self) -> None:
        """Populate preference controls from the current settings."""
        s = self.current_settings

        # General
        idx = self.lang_combo.findData(s.language)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        idx = self.theme_combo.findData(s.theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        # Player
        idx = self.speed_combo.findData(s.default_playback_rate)
        if idx >= 0:
            self.speed_combo.setCurrentIndex(idx)
        self.seek_step.setValue(s.seek_step_seconds)
        self.note_duration.setValue(s.note_display_duration_seconds)
        self.auto_save_check.setChecked(s.auto_save_notes)
        self.resume_playback_check.setChecked(s.resume_playback)

        # Encoding
        self.output_dir.setText(s.default_output_dir)
        idx = self.preset_combo.findData(s.default_preset)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.crf_spin.setValue(s.default_crf)
        idx = self.ocr_lang_combo.findData(s.default_ocr_lang)
        if idx >= 0:
            self.ocr_lang_combo.setCurrentIndex(idx)

    def _save_and_close(self) -> None:
        """Persist edited preferences and accept the dialog."""
        self.config_mgr.update(
            language=self.lang_combo.currentData(),
            theme=self.theme_combo.currentData(),
            default_playback_rate=self.speed_combo.currentData(),
            seek_step_seconds=self.seek_step.value(),
            note_display_duration_seconds=self.note_duration.value(),
            auto_save_notes=self.auto_save_check.isChecked(),
            resume_playback=self.resume_playback_check.isChecked(),
            default_output_dir=self.output_dir.text(),
            default_preset=self.preset_combo.currentData(),
            default_crf=self.crf_spin.value(),
            default_ocr_lang=self.ocr_lang_combo.currentData(),
        )
        self.accept()
