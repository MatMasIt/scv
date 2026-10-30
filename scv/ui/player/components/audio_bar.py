"""Audio and slide information bar component."""

from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QSlider,
)
from scv.i18n import t


class AudioBar(QWidget):
    """Component managing playback speed, volume, mute, and slide count labels."""

    playbackRateChanged = Signal(float)
    mutedChanged = Signal(bool)
    volumeChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        self.slide_label = QLabel(t("slide_counter", current=0, total=0))
        layout.addWidget(self.slide_label)
        layout.addStretch(1)

        speed_label = QLabel(t("speed"))
        layout.addWidget(speed_label)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "0.75x", "1x", "1.25x", "1.5x", "2x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(
            lambda text: self.playbackRateChanged.emit(float(text[:-1]))
        )
        layout.addWidget(self.speed_combo)

        self.mute_check = QCheckBox(t("mute"))
        self.mute_check.toggled.connect(self.mutedChanged.emit)
        layout.addWidget(self.mute_check)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setMaximumWidth(110)
        self.volume_slider.valueChanged.connect(self.volumeChanged.emit)
        layout.addWidget(self.volume_slider)

    def update_slide_info(self, current_slide_index: int, total_slides: int):
        self.slide_label.setText(
            t("slide_counter", current=current_slide_index + 1, total=total_slides)
        )

