"""Encoding settings and options panel component for the Encoder."""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QGroupBox,
    QPushButton,
)

from scv.core import PRESETS, Settings, tesseract_bin
from scv.i18n import t
from scv.i18n import I18nManager


class OptionsPanel(QWidget):
    """Component managing presets, codec controls, and OCR settings."""

    def __init__(self, default_preset: str = "Balanced", default_ocr_lang: str = "eng", parent=None):
        super().__init__(parent)
        self.default_preset = default_preset
        self.default_ocr_lang = default_ocr_lang
        self._language_listener = self._on_language_changed
        self._setup_ui()
        I18nManager.get_instance().add_listener(self._language_listener)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)

        # Mode & Preset Selector Row
        mode_row = QHBoxLayout()
        self._mode_label = QLabel()
        mode_row.addWidget(self._mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([t("mode_simple"), t("mode_advanced")])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo)

        self._preset_label = QLabel()
        mode_row.addWidget(self._preset_label)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(PRESETS)
        self.preset_combo.setCurrentText(self.default_preset)
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        mode_row.addWidget(self.preset_combo, 1)
        layout.addLayout(mode_row)

        # Advanced options form (hidden by default in simple mode)
        self.options_container = QWidget()
        form = QFormLayout(self.options_container)

        self.bitrate = QSpinBox()
        self.bitrate.setRange(6, 256)
        self.bitrate.setSuffix(" kbps")

        self.quality = QSpinBox()
        self.quality.setRange(1, 100)

        self.fps = QDoubleSpinBox()
        self.fps.setRange(0.2, 12)
        self.fps.setDecimals(1)

        self.change = QDoubleSpinBox()
        self.change.setRange(0.1, 100)

        self.stable = QDoubleSpinBox()
        self.stable.setRange(0, 100)

        self.settle = QSpinBox()
        self.settle.setRange(1, 20)

        self.stereo = QCheckBox(t("keep_stereo"))

        form.addRow(t("voice_bitrate"), self.bitrate)
        form.addRow(t("webp_quality"), self.quality)
        form.addRow(t("slide_samples_second"), self.fps)
        form.addRow(t("slide_change_threshold"), self.change)
        form.addRow(t("stability_threshold"), self.stable)
        form.addRow(t("stable_samples"), self.settle)
        form.addRow(t("audio_channels"), self.stereo)

        self._form_labels = [
            form.labelForField(self.bitrate),
            form.labelForField(self.quality),
            form.labelForField(self.fps),
            form.labelForField(self.change),
            form.labelForField(self.stable),
            form.labelForField(self.settle),
            form.labelForField(self.stereo),
        ]

        layout.addWidget(self.options_container)
        self.options_container.setVisible(False)

        # OCR Group
        self.ocr_group = QGroupBox()
        ocr_row = QHBoxLayout(self.ocr_group)

        self.ocr_check = QCheckBox()
        self.ocr_check.setToolTip(t("extract_ocr_tip"))
        self.ocr_check.toggled.connect(self._on_ocr_toggled)

        self.ocr_lang = QComboBox()
        self.ocr_lang.addItem("English", "eng")
        self.ocr_lang.addItem("Italian", "ita")
        self.ocr_lang.addItem("French", "fra")
        self.ocr_lang.addItem("German", "deu")
        self.ocr_lang.addItem("Spanish", "spa")
        self.ocr_lang.addItem("Portuguese", "por")
        idx = self.ocr_lang.findData(self.default_ocr_lang)
        if idx >= 0:
            self.ocr_lang.setCurrentIndex(idx)

        self.ocr_check_btn = QPushButton()
        self.ocr_check_btn.clicked.connect(self.check_tesseract)
        self.ocr_status = QLabel()

        ocr_row.addWidget(self.ocr_check)
        self._ocr_language_label = QLabel()
        ocr_row.addWidget(self._ocr_language_label)
        ocr_row.addWidget(self.ocr_lang)
        ocr_row.addWidget(self.ocr_check_btn)
        ocr_row.addWidget(self.ocr_status)
        ocr_row.addStretch(1)
        layout.addWidget(self.ocr_group)

        self.apply_preset(self.default_preset)
        self._on_ocr_toggled(False)
        self.retranslate_ui()

    def _on_language_changed(self, _language: str):
        self.retranslate_ui()

    def retranslate_ui(self):
        """Refresh visible strings after the active language changes."""
        self._mode_label.setText(t("mode"))
        self._preset_label.setText(t("preset"))
        self.mode_combo.setItemText(0, t("mode_simple"))
        self.mode_combo.setItemText(1, t("mode_advanced"))
        for label, key in zip(
            self._form_labels,
            (
                "voice_bitrate", "webp_quality", "slide_samples_second",
                "slide_change_threshold", "stability_threshold",
                "stable_samples", "audio_channels",
            ),
        ):
            label.setText(t(key))
        self.ocr_group.setTitle(t("slide_text_search"))
        self.ocr_check.setText(t("extract_ocr"))
        self.ocr_check.setToolTip(t("extract_ocr_tip"))
        self._ocr_language_label.setText(t("language"))
        self.ocr_check_btn.setText(t("check_tesseract"))
        if self.ocr_check.isChecked():
            self.check_tesseract()
        else:
            self.ocr_status.setText(t("ocr_disabled"))

    def _on_mode_changed(self, index: int):
        self.options_container.setVisible(index == 1)

    def _on_ocr_toggled(self, enabled: bool):
        self.ocr_check_btn.setEnabled(enabled)
        self.ocr_lang.setEnabled(enabled)
        if enabled:
            self.check_tesseract()
        else:
            self.ocr_status.setText(t("ocr_disabled"))
            self.ocr_status.setStyleSheet("")

    def check_tesseract(self) -> bool:
        try:
            path = tesseract_bin()
        except RuntimeError as exc:
            self.ocr_status.setText(t("ocr_not_available"))
            self.ocr_status.setToolTip(str(exc))
            self.ocr_status.setStyleSheet("color: #b91c1c;")
            return False
        self.ocr_status.setText(t("ocr_available"))
        self.ocr_status.setToolTip(path)
        self.ocr_status.setStyleSheet("color: #15803d;")
        return True

    def apply_preset(self, name: str):
        if name in PRESETS:
            p = PRESETS[name]
            self.bitrate.setValue(p["bitrate"])
            self.quality.setValue(p["quality"])
            self.fps.setValue(p["fps"])
            self.change.setValue(p["change"])
            self.stable.setValue(p["stable"])
            self.settle.setValue(p["settle"])
            self.stereo.setChecked(p["stereo"])

    def get_settings(self) -> Settings:
        return Settings(
            bitrate=self.bitrate.value(),
            quality=self.quality.value(),
            fps=self.fps.value(),
            change=self.change.value(),
            stable=self.stable.value(),
            settle=self.settle.value(),
            stereo=self.stereo.isChecked(),
            ocr=self.ocr_check.isChecked(),
            ocr_lang=self.ocr_lang.currentData(),
        )
