"""Main SCV Player desktop window assembling modular components."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QShortcut
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QTabWidget,
    QPushButton,
)

from scv.config import ConfigManager
from scv.config.settings import AppSettings
from scv.core import LectureSession
from scv.application import StudyCoordinator
from scv.i18n import t
from scv.ui.common.utils import load_app_icon
from scv.ui.widgets import ZoomableViewer, TimelineSlider, NoteBand
from scv.models.study import StudyDocument
from .controller import PlayerController
from .docks import StudyDockWidget, SlidesDockWidget, SearchDockWidget
from .components import TransportBar, AudioBar, PlayerMenuBar
from .workers import AsyncImageLoader, AsyncLectureLoader
from .window_session import PlayerWindowSessionMixin
from .window_resume import PlayerWindowResumeMixin
from .window_playback import PlayerWindowPlaybackMixin
from .window_study import PlayerWindowStudyMixin
from .window_shell import PlayerWindowShellMixin


class PlayerWindow(
    PlayerWindowSessionMixin,
    PlayerWindowResumeMixin,
    PlayerWindowPlaybackMixin,
    PlayerWindowStudyMixin,
    PlayerWindowShellMixin,
):
    """Desktop player coordinating viewer, docks, controller, and components."""

    def __init__(
        self, path: Path | str | None = None, parent: QWidget | None = None
    ) -> None:
        """Create the player window and initialize its services and controls."""
        super().__init__(parent)
        self.setWindowTitle(t("player_title"))
        self.resize(1100, 700)
        self.setAcceptDrops(True)
        app_icon = load_app_icon()
        if app_icon is not None:
            self.setWindowIcon(app_icon)

        self.session: LectureSession | None = None
        self.source_path: Path | None = None
        self.last_index: int = -1
        self.original_pixmap: QPixmap | None = None
        self.seeking: bool = False
        self._resume_position_seconds: float | None = None
        self._pending_resume_position: float | None = None
        self._last_saved_progress: tuple[float, int] | None = None
        self._session_generation: int = 0
        self._open_request_id: int = 0
        self._study_switch_snapshot: dict[str, object] | None = None
        self._closing: bool = False
        self._frame_load_running: bool = False
        self._requested_slide_index: int | None = None
        self._slide_pixmap_cache: OrderedDict[int, QPixmap] = OrderedDict()
        self._slide_pixmap_cache_bytes: int = 0
        self._slide_pixmap_cache_limit: int = 128 * 1024 * 1024
        self._retired_sessions: list[LectureSession] = []

        self.config_mgr: ConfigManager = ConfigManager.get_instance()
        self._resume_setting_enabled: bool = self.config_mgr.settings.resume_playback
        self._config_listener: Callable[[AppSettings], None] = self._on_config_changed
        self.study: StudyCoordinator = StudyCoordinator()
        self.controller: PlayerController = PlayerController(self)
        self.image_loader: AsyncImageLoader = AsyncImageLoader(self)
        self.image_loader.image_loaded.connect(self._on_image_loaded)
        self.lecture_loader: AsyncLectureLoader = AsyncLectureLoader(self)
        self.lecture_loader.lecture_loaded.connect(self._on_lecture_loaded)
        self.shortcuts: list[QShortcut] = []

        self._build_ui()
        self._connect_signals()
        self.progress_timer: QTimer = QTimer(self)
        self.progress_timer.setInterval(10_000)
        self.progress_timer.timeout.connect(self._save_playback_progress)
        self._resume_dismiss_remaining_ms: int = 10_000
        self.resume_dismiss_timer: QTimer = QTimer(self)
        self.resume_dismiss_timer.setSingleShot(True)
        self.resume_dismiss_timer.timeout.connect(
            self._dismiss_resume_prompt_after_playing
        )
        self.config_mgr.add_listener(self._config_listener)
        self._install_shortcuts()
        self._update_action_states()
        self._update_recent_menu()

        if path:
            QTimer.singleShot(0, lambda: self.open_file(path))

    @property
    def document(self) -> StudyDocument:
        """Return the active study document used by the player controls."""
        return self.study.document

    def _build_ui(self) -> None:
        """Create the player layout, controls, docks, and menu bar."""
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        self.resume_banner = QWidget()
        self.resume_banner.setObjectName("resumeBanner")
        self._apply_resume_banner_theme()
        resume_layout = QHBoxLayout(self.resume_banner)
        self.resume_label = QLabel()
        self.resume_label.setWordWrap(True)
        resume_layout.addWidget(self.resume_label, 1)
        self.resume_button = QPushButton(t("resume_button"))
        self.start_over_button = QPushButton(t("start_over_button"))
        resume_layout.addWidget(self.resume_button)
        resume_layout.addWidget(self.start_over_button)
        self.resume_banner.hide()
        outer.addWidget(self.resume_banner)

        # Central Splitter (Viewer + Side Tabs)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.viewer = ZoomableViewer()
        self.viewer.setMinimumSize(250, 160)
        self.splitter.addWidget(self.viewer)

        self.slide_tabs = QTabWidget()
        self.slide_tabs.setMinimumWidth(400)
        self.slides_dock = SlidesDockWidget(image_loader=self.image_loader)
        self.search_dock = SearchDockWidget()
        self.slide_tabs.addTab(self.slides_dock, t("tab_timeline"))
        self.slide_tabs.addTab(self.search_dock, t("tab_search"))
        self.splitter.addWidget(self.slide_tabs)
        self.splitter.setSizes([680, 420])
        outer.addWidget(self.splitter, 1)

        # Timeline Seek Bar
        seek_row = QHBoxLayout()
        self.time_label = QLabel("00:00:00")
        seek_row.addWidget(self.time_label)
        self.seek = TimelineSlider()
        self.seek.setRange(0, 0)
        seek_row.addWidget(self.seek, 1)
        self.duration_label = QLabel("00:00:00")
        seek_row.addWidget(self.duration_label)
        outer.addLayout(seek_row)

        # Audio & Info Bar Component
        self.audio_bar = AudioBar()
        outer.addWidget(self.audio_bar)

        # Note Banner Overlay
        self.note_band = NoteBand()
        outer.addWidget(self.note_band)

        # Playback Transport Bar Component
        self.transport_bar = TransportBar()
        outer.addWidget(self.transport_bar)

        # Study Dock Widget
        self.study_dock = StudyDockWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.study_dock)
        self.study_dock.hide()

        # Menu Bar Component
        menu_callbacks = {
            "open": self.pick,
            "save_study": self.save_document,
            "discard_study": self.discard_document,
            "close": self.close,
            "show_study": self.show_study_dock,
            "add_bookmark": self.add_bookmark,
            "add_note": self.add_note,
            "edit_study": self.edit_study_item,
            "delete_study": self.delete_study_item,
            "select_tool": self._on_tool_selected,
            "clear_annotations": self.clear_annotations,
            "fullscreen": self.toggle_fullscreen,
            "zoom_in": self.viewer.zoom_in,
            "zoom_out": self.viewer.zoom_out,
            "reset_view": self.viewer.reset_view,
            "toggle_thumbnails": lambda: self.slide_tabs.setVisible(not self.slide_tabs.isVisible()),
            "toggle_study": self.toggle_study_dock,
            "show_bookmarks": self.show_bookmarks,
            "show_shortcuts": self.show_shortcuts,
        }
        self.player_menu = PlayerMenuBar(self, menu_callbacks)
        self.setMenuBar(self.player_menu)

        self.statusBar().showMessage(t("tip_drag_drop"))

    def _connect_signals(self) -> None:
        """Connect the player controls and child widgets to their handlers."""
        # Playback controller
        self.controller.positionChanged.connect(self._on_playback_position)
        self.controller.stateChanged.connect(self._on_playback_state)
        self.controller.slideChanged.connect(self._draw_slide)
        self.controller.errorOccurred.connect(lambda msg: self.statusBar().showMessage(msg))
        self.resume_button.clicked.connect(self._resume_playback)
        self.start_over_button.clicked.connect(self._start_from_beginning)

        # Seek controls
        self.seek.sliderPressed.connect(lambda: setattr(self, "seeking", True))
        self.seek.sliderReleased.connect(self._on_seek_released)

        # Audio bar
        self.audio_bar.playbackRateChanged.connect(self.controller.set_playback_rate)
        self.audio_bar.mutedChanged.connect(self.controller.set_muted)
        self.audio_bar.volumeChanged.connect(self.controller.set_volume)

        # Transport bar
        self.transport_bar.seekRequested.connect(self._on_transport_seek)
        self.transport_bar.slideJumpRequested.connect(self._jump_slide)
        self.transport_bar.playToggleRequested.connect(self._toggle_playback)
        self.transport_bar.studyToggleRequested.connect(self.toggle_study_dock)
        self.transport_bar.fullscreenRequested.connect(self.toggle_fullscreen)
        self.transport_bar.zoomInRequested.connect(self.viewer.zoom_in)
        self.transport_bar.zoomOutRequested.connect(self.viewer.zoom_out)
        self.transport_bar.resetViewRequested.connect(self.viewer.reset_view)

        # Viewer & Notes
        self.viewer.annotationClicked.connect(self._on_viewer_annotation_clicked)
        self.viewer.annotationCompleted.connect(self._on_viewer_annotation_completed)
        self.note_band.clicked.connect(self._on_note_band_clicked)

        # Docks
        self.slides_dock.slideSelected.connect(self._seek_to_slide)
        self.search_dock.slideSelected.connect(self._on_search_slide_selected)
        self.search_dock.search_input.textChanged.connect(self._on_search_text_changed)

        # Study dock
        self.study_dock.jumpToBookmarkRequested.connect(self._jump_to_bookmark)
        self.study_dock.jumpToNoteRequested.connect(self._jump_to_note)
        self.study_dock.jumpToSlideAnnotationRequested.connect(self._jump_to_annotation)
        self.study_dock.addBookmarkRequested.connect(self.add_bookmark)
        self.study_dock.addNoteRequested.connect(self.add_note)
        self.study_dock.editItemRequested.connect(self.edit_study_item)
        self.study_dock.deleteItemRequested.connect(self.delete_study_item)
        self.study_dock.clearMarksRequested.connect(self.clear_annotations)
        self.study_dock.toolSelected.connect(self._on_tool_selected)
        self.study_dock.noteVisibilityChanged.connect(self._on_note_visibility_changed)
        self.study_dock.selectionChanged.connect(lambda _: self._update_action_states())
