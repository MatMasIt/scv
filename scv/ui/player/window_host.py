"""Typed host contract shared by the player window behavior mixins."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap, QShortcut
from PySide6.QtWidgets import QMainWindow, QLabel, QPushButton, QSplitter, QTabWidget, QWidget

from scv.config import ConfigManager
from scv.config.settings import AppSettings
from scv.core import LectureSession
from scv.application import StudyCoordinator
from scv.models.study import StudyDocument
from scv.ui.widgets import ZoomableViewer, TimelineSlider, NoteBand

if TYPE_CHECKING:
    from .components import AudioBar, PlayerMenuBar, TransportBar
    from .controller import PlayerController
    from .docks import SearchDockWidget, SlidesDockWidget, StudyDockWidget
    from .workers import AsyncImageLoader, AsyncLectureLoader


class PlayerWindowHost(QMainWindow):
    """Provide typed component state and cross-mixin method signatures.

    The behavior mixins inherit this host instead of relying on attributes that
    are only assigned by ``PlayerWindow.__init__``. This keeps component access
    visible to static type checkers while retaining QMainWindow's Qt API.
    """

    session: LectureSession | None
    source_path: Path | None
    last_index: int
    original_pixmap: QPixmap | None
    seeking: bool
    _resume_position_seconds: float | None
    _pending_resume_position: float | None
    _last_saved_progress: tuple[float, int] | None
    _session_generation: int
    _open_request_id: int
    _study_switch_snapshot: dict[str, object] | None
    _closing: bool
    _frame_load_running: bool
    _requested_slide_index: int | None
    _slide_pixmap_cache: OrderedDict[int, QPixmap]
    _slide_pixmap_cache_bytes: int
    _slide_pixmap_cache_limit: int
    _retired_sessions: list[LectureSession]

    config_mgr: ConfigManager
    _resume_setting_enabled: bool
    _config_listener: Callable[[AppSettings], None]
    study: StudyCoordinator
    controller: PlayerController
    image_loader: AsyncImageLoader
    lecture_loader: AsyncLectureLoader
    shortcuts: list[QShortcut]
    progress_timer: QTimer
    _resume_dismiss_remaining_ms: int
    resume_dismiss_timer: QTimer

    resume_banner: QWidget
    resume_label: QLabel
    resume_button: QPushButton
    start_over_button: QPushButton
    splitter: QSplitter
    viewer: ZoomableViewer
    slide_tabs: QTabWidget
    slides_dock: SlidesDockWidget
    search_dock: SearchDockWidget
    time_label: QLabel
    seek: TimelineSlider
    duration_label: QLabel
    audio_bar: AudioBar
    note_band: NoteBand
    transport_bar: TransportBar
    study_dock: StudyDockWidget
    player_menu: PlayerMenuBar

    @property
    def document(self) -> StudyDocument:
        """Return the current study document supplied by the player window."""
        ...

    def _cleanup_retired_sessions(self) -> None:
        """Release sessions whose background image loads have completed."""
        ...

    def _refresh_note_band(self, position_seconds: float) -> None:
        """Refresh the note banner for a playback position."""
        ...

    def _refresh_study_ui(self) -> None:
        """Refresh controls that display study document state."""
        ...

    def _sync_current_annotations(self) -> None:
        """Persist the visible slide annotations into the study document."""
        ...

    def _update_action_states(self) -> None:
        """Update menu action enablement from the current player state."""
        ...

    def _draw_slide(self, index: int) -> None:
        """Display the requested slide image."""
        ...

    def _cancel_resume_prompt_dismissal(self) -> None:
        """Cancel the active-playback countdown for the resume prompt."""
        ...

    def _on_playback_position(self, ms: int) -> None:
        """Refresh playback UI for the supplied millisecond position."""
        ...

    def _prepare_resume_prompt(self) -> None:
        """Show the resume prompt when saved playback progress is available."""
        ...

    def _save_playback_progress(
        self,
        position_seconds: float | None = None,
        force: bool = False,
    ) -> None:
        """Save the current playback position when progress tracking is enabled."""
        ...

    def save_document(self) -> None:
        """Save the current study document."""
        ...

    def _confirm_study_changes_before_close(self) -> bool:
        """Resolve unsaved study changes before closing the player."""
        ...

    def _jump_slide(self, direction: int) -> None:
        """Move playback to the adjacent slide."""
        ...

    def _on_transport_seek(self, delta_ms: int) -> None:
        """Seek by the signed step requested by the transport controls."""
        ...

    def _seek_step_ms(self) -> int:
        """Return the configured keyboard seek step in milliseconds."""
        ...

    def _toggle_playback(self) -> None:
        """Toggle playback when a lecture is loaded."""
        ...

    def open_file(self, path: Path | str) -> None:
        """Load the selected lecture after resolving pending study changes."""
        ...

    def _close_session(self) -> None:
        """Release the active lecture session and reset player state."""
        ...

    def _seek_to_slide(self, index: int) -> None:
        """Seek to the first timestamp associated with the requested slide."""
        ...
