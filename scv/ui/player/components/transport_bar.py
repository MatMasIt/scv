"""Playback transport control bar component."""

from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QToolButton,
    QMenu,
)
from scv.i18n import t


class TransportBar(QWidget):
    """Playback transport bar with play/pause, seek, slide jump, study and view controls."""

    seekRequested = Signal(int)  # delta milliseconds
    slideJumpRequested = Signal(int)  # -1 or +1
    playToggleRequested = Signal()
    studyToggleRequested = Signal()
    fullscreenRequested = Signal()
    zoomInRequested = Signal()
    zoomOutRequested = Signal()
    resetViewRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize playback, navigation, study, and viewer controls."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the transport buttons and the viewer action menu."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.addStretch(1)

        self.prev_5s = QToolButton()
        self.prev_5s.setText(t("seek_back_5s"))
        self.prev_5s.setToolTip(t("seek_back_tip"))
        self.prev_5s.clicked.connect(lambda: self.seekRequested.emit(-5000))
        layout.addWidget(self.prev_5s)

        self.slide_prev = QToolButton()
        self.slide_prev.setText("◀")
        self.slide_prev.setToolTip(t("prev_slide_tip"))
        self.slide_prev.clicked.connect(lambda: self.slideJumpRequested.emit(-1))
        layout.addWidget(self.slide_prev)

        self.play_btn = QPushButton(t("play"))
        self.play_btn.clicked.connect(self.playToggleRequested.emit)
        layout.addWidget(self.play_btn)

        self.slide_next = QToolButton()
        self.slide_next.setText("▶")
        self.slide_next.setToolTip(t("next_slide_tip"))
        self.slide_next.clicked.connect(lambda: self.slideJumpRequested.emit(1))
        layout.addWidget(self.slide_next)

        self.next_5s = QToolButton()
        self.next_5s.setText(t("seek_fwd_5s"))
        self.next_5s.setToolTip(t("seek_fwd_tip"))
        self.next_5s.clicked.connect(lambda: self.seekRequested.emit(5000))
        layout.addWidget(self.next_5s)

        self.study_btn = QPushButton(t("study"))
        self.study_btn.setToolTip(t("study_tip"))
        self.study_btn.clicked.connect(self.studyToggleRequested.emit)
        layout.addWidget(self.study_btn)

        self.view_btn = QToolButton()
        self.view_btn.setText(t("menu_view"))
        self.view_btn.setToolTip(t("view_tip"))
        self.view_menu = QMenu(self.view_btn)
        self.view_menu.addAction(t("zoom_in"), self.zoomInRequested.emit)
        self.view_menu.addAction(t("zoom_out"), self.zoomOutRequested.emit)
        self.view_menu.addAction(t("reset_view"), self.resetViewRequested.emit)
        self.view_menu.addSeparator()
        self.view_menu.addAction(t("fullscreen"), self.fullscreenRequested.emit)
        self.view_btn.setMenu(self.view_menu)
        self.view_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(self.view_btn)

        layout.addStretch(1)

    def set_playing_state(self, is_playing: bool) -> None:
        """Show Pause while playback is active and Play otherwise."""
        """Update the play button label to match the playback state."""
        self.play_btn.setText(t("pause") if is_playing else t("play"))
