"""Main SCV Player desktop window assembling modular components."""

from __future__ import annotations
from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QPixmap,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QPushButton,
)

from scv.bookmarks import load_progress, save_progress
from scv.config import ConfigManager
from scv.core import LectureSession
from scv.i18n import t
from scv.application import StudyCoordinator
from scv.models.timeline import SlideTimeline
from scv.models.tools import DrawingTool
from scv.ui.common.utils import fmt_time, load_app_icon
from scv.ui.widgets import ZoomableViewer, TimelineSlider, NoteBand
from .controller import PlayerController
from .dialogs import PlayerDialogs, SaveCloseResult
from .docks import StudyDockWidget, SlidesDockWidget, SearchDockWidget
from .components import TransportBar, AudioBar, PlayerMenuBar


class PlayerWindow(QMainWindow):
    """Desktop player coordinating viewer, docks, controller, and components."""

    def __init__(self, path: Path | str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("player_title"))
        self.resize(1100, 700)
        self.setAcceptDrops(True)
        self.setWindowIcon(load_app_icon())

        self.session: LectureSession | None = None
        self.source_path: Path | None = None
        self.last_index: int = -1
        self.original_pixmap: QPixmap | None = None
        self.seeking: bool = False
        self._resume_position_seconds: float | None = None
        self._pending_resume_position: float | None = None
        self._last_saved_progress: tuple[float, int] | None = None

        self.config_mgr = ConfigManager.get_instance()
        self._resume_setting_enabled = self.config_mgr.settings.resume_playback
        self._config_listener = self._on_config_changed
        self.study = StudyCoordinator()
        self.controller = PlayerController(self)
        self.shortcuts: list[QShortcut] = []

        self._build_ui()
        self._connect_signals()
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(10_000)
        self.progress_timer.timeout.connect(self._save_playback_progress)
        self.config_mgr.add_listener(self._config_listener)
        self._install_shortcuts()
        self._update_action_states()
        self._update_recent_menu()

        if path:
            QTimer.singleShot(0, lambda: self.open_file(path))

    @property
    def document(self):
        """Expose the active study document to existing UI handlers."""
        return self.study.document

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        self.resume_banner = QWidget()
        self.resume_banner.setObjectName("resumeBanner")
        self.resume_banner.setStyleSheet(
            "QWidget#resumeBanner { background: #eef2ff; border: 1px solid #c7d2fe; "
            "border-radius: 6px; }"
        )
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

        # 1. Central Splitter (Viewer + Side Tabs)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.viewer = ZoomableViewer()
        self.viewer.setMinimumSize(250, 160)
        self.splitter.addWidget(self.viewer)

        self.slide_tabs = QTabWidget()
        self.slide_tabs.setMinimumWidth(400)
        self.slides_dock = SlidesDockWidget()
        self.search_dock = SearchDockWidget()
        self.slide_tabs.addTab(self.slides_dock, t("tab_timeline"))
        self.slide_tabs.addTab(self.search_dock, t("tab_search"))
        self.splitter.addWidget(self.slide_tabs)
        self.splitter.setSizes([680, 420])
        outer.addWidget(self.splitter, 1)

        # 2. Timeline Seek Bar
        seek_row = QHBoxLayout()
        self.time_label = QLabel("00:00:00")
        seek_row.addWidget(self.time_label)
        self.seek = TimelineSlider()
        self.seek.setRange(0, 0)
        seek_row.addWidget(self.seek, 1)
        self.duration_label = QLabel("00:00:00")
        seek_row.addWidget(self.duration_label)
        outer.addLayout(seek_row)

        # 3. Audio & Info Bar Component
        self.audio_bar = AudioBar()
        outer.addWidget(self.audio_bar)

        # 4. Note Banner Overlay
        self.note_band = NoteBand()
        outer.addWidget(self.note_band)

        # 5. Playback Transport Bar Component
        self.transport_bar = TransportBar()
        outer.addWidget(self.transport_bar)

        # 6. Study Dock Widget
        self.study_dock = StudyDockWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.study_dock)
        self.study_dock.hide()

        # 7. Menu Bar Component
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

    def _connect_signals(self):
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

    def _install_shortcuts(self):
        bindings = {
            "Space": self._toggle_playback,
            "Left": lambda: self._on_transport_seek(-self._seek_step_ms()),
            "Right": lambda: self._on_transport_seek(self._seek_step_ms()),
            "Up": lambda: self._jump_slide(-1),
            "PageUp": lambda: self._jump_slide(-1),
            "Down": lambda: self._jump_slide(1),
            "PageDown": lambda: self._jump_slide(1),
            "F": self.toggle_fullscreen,
        }
        for sequence, callback in bindings.items():
            self._register_shortcut(QKeySequence(sequence), callback)

        media_bindings = {
            Qt.Key.Key_MediaPlay: self.controller.play,
            Qt.Key.Key_MediaPause: self.controller.pause,
            Qt.Key.Key_MediaTogglePlayPause: self._toggle_playback,
            Qt.Key.Key_MediaStop: self.controller.stop,
            Qt.Key.Key_MediaPrevious: lambda: self._jump_slide(-1),
            Qt.Key.Key_MediaNext: lambda: self._jump_slide(1),
        }
        for key, callback in media_bindings.items():
            self._register_shortcut(QKeySequence(key), callback)

    def _register_shortcut(self, sequence: QKeySequence, callback):
        """Register a window-local shortcut and retain it for the window lifetime."""
        shortcut = QShortcut(sequence, self)
        shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        shortcut.activated.connect(callback)
        self.shortcuts.append(shortcut)

    def _seek_step_ms(self) -> int:
        return self.config_mgr.settings.seek_step_seconds * 1000

    def _on_transport_seek(self, delta_ms: int):
        self._pending_resume_position = None
        sign = -1 if delta_ms < 0 else 1
        step = self._seek_step_ms() * sign
        self.controller.seek_by(step)

    def _jump_slide(self, direction: int):
        self._pending_resume_position = None
        self.controller.jump_slide(direction)

    def _seek_to_slide(self, index: int):
        self._pending_resume_position = None
        self.controller.seek_to_slide(index)

    # --- Lecture File Lifecycle ---
    def pick(self):
        path, _ = QFileDialog.getOpenFileName(
            self, t("menu_open_lecture"), str(Path.home()), "SCV lectures (*.scv)"
        )
        if path:
            self.open_file(path)

    def open_file(self, path: Path | str):
        try:
            session = LectureSession.open(path)
        except Exception as exc:
            QMessageBox.critical(self, t("cannot_open_scv"), str(exc))
            return

        if self.session:
            self._save_playback_progress(force=True)
        self.controller.stop()
        self._close_session()
        self.session = session
        self.source_path = session.source_path

        try:
            self.study.attach(self.source_path)
        except Exception as exc:
            self.study.attach(None)
            self.statusBar().showMessage(f"Bookmark file error: {exc}")

        self.config_mgr.settings.add_recent_file(self.source_path)
        self.config_mgr.save()
        self._update_recent_menu()

        self.last_index = -1

        self.slides_dock.load_slides(
            [
                {"time": slide.time, "image": str(slide.image), "text": slide.text or ""}
                for slide in session.slide_models
            ],
            session.root,
        )
        self.search_dock.clear()

        duration = session.duration_seconds
        duration_ms = int(duration * 1000)
        self.seek.setMaximum(duration_ms)
        self.duration_label.setText(fmt_time(duration_ms))
        self.seek.set_markers([t_val / duration for t_val in session.slide_times if duration])

        self._refresh_study_ui()
        self.controller.load_audio(session.audio_path, session.slide_times)
        self._prepare_resume_prompt()
        self.setWindowTitle(
            f'{session.manifest.get("title", session.source_path.stem)} - {t("player_title")}'
        )

        self._on_playback_position(0)
        self._update_action_states()
        self.statusBar().showMessage(
            f'{len(session.lecture.slides)} images · SCV v{session.lecture.format_version}'
        )

    def _prepare_resume_prompt(self):
        """Show the resume banner when this lecture has a saved position."""
        self.progress_timer.stop()
        self.resume_banner.hide()
        self._resume_position_seconds = None
        self._pending_resume_position = None
        self._last_saved_progress = None
        if (
            not self.session
            or not self.source_path
            or not self.config_mgr.settings.resume_playback
        ):
            return
        try:
            progress = load_progress(self.source_path)
        except Exception:
            return
        if progress is None:
            self.progress_timer.start()
            return

        position = progress["position_seconds"]
        if position <= 0 or position >= self.session.duration_seconds:
            self.progress_timer.start()
            return
        slide_index = SlideTimeline(self.session.slide_times).current_index(position)
        if slide_index < 0:
            self.progress_timer.start()
            return

        self._resume_position_seconds = position
        self._last_saved_progress = (round(position, 1), slide_index)
        self.resume_label.setText(
            t(
                "resume_prompt",
                time=fmt_time(round(position * 1000)),
                slide=slide_index + 1,
            )
        )
        self.resume_banner.show()

    def _resume_playback(self):
        """Seek to the saved position after the user chooses to resume."""
        if self._resume_position_seconds is None or not self.session:
            return
        position = self._resume_position_seconds
        slide_index = SlideTimeline(self.session.slide_times).current_index(position)
        self._resume_position_seconds = None
        self._pending_resume_position = position
        self.resume_banner.hide()
        self.controller.set_position(round(position * 1000))
        self._last_saved_progress = (round(position, 1), slide_index)
        self._start_progress_timer()

    def _start_from_beginning(self):
        """Dismiss the resume prompt and replace its saved point with zero."""
        if not self.session:
            return
        self._resume_position_seconds = None
        self._pending_resume_position = None
        self.resume_banner.hide()
        self.controller.set_position(0)
        self._draw_slide(0)
        self._save_playback_progress(position_seconds=0.0, force=True)
        self._start_progress_timer()

    def _start_progress_timer(self):
        if (
            self.session
            and self.config_mgr.settings.resume_playback
            and self.resume_banner.isHidden()
        ):
            self.progress_timer.start()

    def _on_config_changed(self, settings):
        """Apply resume preference changes while a lecture is open."""
        was_enabled = self._resume_setting_enabled
        self._resume_setting_enabled = settings.resume_playback
        if not settings.resume_playback:
            self.progress_timer.stop()
            self.resume_banner.hide()
            self._resume_position_seconds = None
            self._pending_resume_position = None
        elif not was_enabled and self.session:
            if not self.controller.is_playing() and self.controller.position_seconds() == 0:
                self._prepare_resume_prompt()
            else:
                self._start_progress_timer()
        else:
            self._start_progress_timer()

    def _save_playback_progress(
        self,
        position_seconds: float | None = None,
        force: bool = False,
    ):
        """Periodically save only playback progress, leaving study edits untouched."""
        if (
            not self.session
            or not self.source_path
            or not self.config_mgr.settings.resume_playback
            or not self.resume_banner.isHidden()
        ):
            return
        if position_seconds is None:
            position_seconds = (
                self._pending_resume_position
                if self._pending_resume_position is not None
                else self.controller.position_seconds()
            )
        position_seconds = max(0.0, min(position_seconds, self.session.duration_seconds))
        slide_index = SlideTimeline(self.session.slide_times).current_index(
            position_seconds
        )
        if slide_index < 0:
            return
        snapshot = (round(position_seconds, 1), slide_index)
        if not force and snapshot == self._last_saved_progress:
            return
        try:
            save_progress(self.source_path, position_seconds, slide_index)
        except Exception as exc:
            self.statusBar().showMessage(t("progress_save_error", error=str(exc)))
            return
        self._last_saved_progress = snapshot

    def _toggle_playback(self):
        if self.session:
            self.controller.toggle()

    def _on_playback_state(self, state):
        self.transport_bar.set_playing_state(self.controller.is_playing())

    def _on_seek_released(self):
        self.seeking = False
        self._pending_resume_position = None
        self.controller.set_position(self.seek.value())
        self._on_playback_position(self.seek.value())

    def _on_playback_position(self, ms: int):
        if not self.session:
            return
        if (
            self._pending_resume_position is not None
            and abs(ms / 1000.0 - self._pending_resume_position) <= 1.0
        ):
            self._pending_resume_position = None
        if not self.seeking:
            self.seek.setValue(ms)
        self.time_label.setText(fmt_time(ms))

        duration_ms = self.seek.maximum()
        ix = self.controller.current_slide_index
        total_slides = self.controller.slide_count
        self.audio_bar.update_slide_info(ix, total_slides)
        self.slides_dock.update_progress(ms, duration_ms, ix, total_slides)

        self._refresh_note_band(ms / 1000.0)
        self._draw_slide(ix)
        self._update_action_states()

    def _draw_slide(self, index: int):
        if not self.session or index == self.last_index or index < 0:
            return
        if self.last_index >= 0:
            self._sync_current_annotations()
        try:
            if not self.session:
                return
            im = self.session.frame_at(self.session.slide_times[index])
            self.original_pixmap = QPixmap.fromImage(ImageQt(im))
            self.last_index = index
            self.viewer.set_annotations(self.document.get_slide_annotations(index))
            self._refresh_slide_image()
            self.slides_dock.set_current_slide(index)
            self._refresh_study_ui()
        except Exception as exc:
            self.statusBar().showMessage(f"Image error: {exc}")

    def _refresh_slide_image(self):
        if self.original_pixmap:
            self.viewer.setPixmap(
                self.original_pixmap.scaled(
                    self.viewer.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_slide_image()

    # --- Search & Note Overlay ---
    def _on_search_text_changed(self, text: str):
        count = self.search_dock.filter_from_slides_dock(self.slides_dock, text)
        self.slide_tabs.setTabText(
            1, t("tab_search_with_count", count=count) if text.strip() else t("tab_search")
        )

    def _on_search_slide_selected(self, index: int):
        self.slide_tabs.setCurrentIndex(0)
        self.slides_dock.set_current_slide(index)
        self._seek_to_slide(index)

    def _refresh_note_band(self, position_seconds: float):
        duration = self.config_mgr.settings.note_display_duration_seconds
        active = self.document.active_notes_at(position_seconds, window_seconds=duration)
        if active:
            _, note = active[-1]
            self.note_band.setText(f"{t('note_prefix')} · {fmt_time(note.time * 1000)}\n{note.label}")
            self.note_band.show()
        else:
            self.note_band.hide()

    def _on_note_band_clicked(self):
        self.show_study_dock()
        active = self.document.active_notes_at(self.controller.position_seconds())
        if active:
            idx, _ = active[-1]
            self.study_dock.select_note_at_index(idx)

    # --- Tool & Annotation Handlers ---
    def _on_tool_selected(self, tool: DrawingTool):
        self.viewer.set_annotation_mode(tool)
        self.study_dock.set_active_tool(tool)

    def _on_viewer_annotation_clicked(self, index: int):
        self.show_study_dock()
        if self.last_index >= 0:
            self.study_dock.select_annotation(self.last_index, index)

    def _on_viewer_annotation_completed(self):
        if self.last_index < 0:
            return
        strokes = list(self.viewer.annotations)
        self.study.sync_annotations(self.last_index, strokes)
        self._refresh_study_ui()
        if strokes:
            self.study_dock.select_annotation(self.last_index, len(strokes) - 1)

    def _sync_current_annotations(self):
        if self.source_path and self.last_index >= 0:
            self.study.sync_annotations(self.last_index, self.viewer.annotations)

    def clear_annotations(self):
        if self.last_index < 0 or not self.source_path:
            return
        self.viewer.clear_annotations()
        self.document.clear_slide_annotations(self.last_index)
        self._refresh_study_ui()
        self._update_action_states()

    # --- Study Dock Management ---
    def toggle_study_dock(self):
        self.study_dock.setVisible(not self.study_dock.isVisible())

    def show_study_dock(self):
        self.study_dock.show()
        self.study_dock.raise_()

    def _refresh_study_ui(self):
        if not self.session:
            return
        duration = self.session.duration_seconds
        self.seek.set_study_markers(
            [b.time / duration for b in self.document.bookmarks if 0 <= b.time <= duration],
            [n.time / duration for n in self.document.notes if 0 <= n.time <= duration],
        )
        self.study_dock.refresh_from_document(self.document)
        self._refresh_note_band(self.controller.position_seconds())
        self._update_action_states()

    def _jump_to_bookmark(self, index: int):
        if 0 <= index < len(self.document.bookmarks):
            self._pending_resume_position = None
            self.controller.set_position(round(self.document.bookmarks[index].time * 1000))

    def _jump_to_note(self, index: int):
        if 0 <= index < len(self.document.notes):
            self._pending_resume_position = None
            self.controller.set_position(round(self.document.notes[index].time * 1000))

    def _jump_to_annotation(self, slide_index: int, annotation_index: int):
        self._seek_to_slide(slide_index)
        self.viewer.set_selected_annotation(annotation_index)

    def _on_note_visibility_changed(self, index: int, show: bool):
        self.document.set_note_visibility(index, show)
        self._refresh_note_band(self.controller.position_seconds())
        self._update_action_states()

    # --- Study Editing & Dialogs ---
    def add_bookmark(self):
        if not self.session or not self.source_path:
            return
        label = PlayerDialogs.prompt_add_bookmark(self)
        if label:
            self.document.add_bookmark(self.controller.position_seconds(), label)
            self._refresh_study_ui()
            self.statusBar().showMessage(f"Bookmark added: {label}")

    def add_note(self):
        if not self.session or not self.source_path:
            return
        text = PlayerDialogs.prompt_add_note(self)
        if text:
            self.document.add_note(self.controller.position_seconds(), text)
            self._refresh_study_ui()
            self.statusBar().showMessage("Note added")

    def edit_study_item(self):
        target = self.study_dock.current_target()
        if not target:
            return

        if target.is_annotation:
            entries = self.document.get_slide_annotations(target.slide_index)
            if 0 <= target.index < len(entries):
                new_tool = PlayerDialogs.prompt_edit_annotation_tool(self, entries[target.index].tool)
                if new_tool:
                    self.document.update_annotation_tool(target.slide_index, target.index, new_tool)
                    if target.slide_index == self.last_index:
                        self.viewer.set_annotations(self.document.get_slide_annotations(target.slide_index))
                    self._refresh_study_ui()
        elif target.is_bookmark:
            curr = self.document.bookmarks[target.index].label
            new_label = PlayerDialogs.prompt_edit_bookmark(self, curr)
            if new_label:
                self.document.edit_bookmark(target.index, new_label)
                self._refresh_study_ui()
        elif target.is_note:
            curr = self.document.notes[target.index].label
            new_text = PlayerDialogs.prompt_edit_note(self, curr)
            if new_text:
                self.document.edit_note(target.index, new_text)
                self._refresh_study_ui()

    def delete_study_item(self):
        target = self.study_dock.current_target()
        if not target or not PlayerDialogs.confirm_delete_study_item(self):
            return

        if target.is_annotation:
            self.document.delete_annotation(target.slide_index, target.index)
            if target.slide_index == self.last_index:
                self.viewer.set_annotations(self.document.get_slide_annotations(target.slide_index))
        elif target.is_bookmark:
            self.document.delete_bookmark(target.index)
        elif target.is_note:
            self.document.delete_note(target.index)

        self._refresh_study_ui()

    def show_bookmarks(self):
        idx = PlayerDialogs.pick_bookmark(self, self.document.bookmarks)
        if idx is not None:
            self._jump_to_bookmark(idx)

    def save_document(self):
        self._sync_current_annotations()
        if self.source_path:
            self.study.save()
            self.statusBar().showMessage(t("study_changes_saved"))
            self._update_action_states()

    def discard_document(self):
        if not self.source_path:
            return
        if self.study.dirty and not PlayerDialogs.confirm_discard_changes(self):
            return
        try:
            self.study.reload()
        except Exception as exc:
            QMessageBox.critical(self, t("cannot_reload_study"), str(exc))
            return

        if self.last_index >= 0:
            self.viewer.set_annotations(self.study.document.get_slide_annotations(self.last_index))
        self._refresh_study_ui()
        self.statusBar().showMessage(t("study_changes_discarded"))
        self._update_action_states()

    def _update_action_states(self):
        loaded = self.session is not None and self.source_path is not None
        current_slide = loaded and self.last_index >= 0
        has_selection = self.study_dock.current_target() is not None
        self.player_menu.update_action_states(
            has_lecture=loaded,
            has_slide=current_slide,
            has_selection=has_selection,
            is_dirty=self.document.dirty,
        )

    def _update_recent_menu(self):
        self.player_menu.populate_recent_files(
            self.config_mgr.settings.recent_files, self.open_file
        )

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
            self.statusBar().show()
        else:
            self.showFullScreen()
            self.menuBar().hide()
            self.statusBar().hide()

    def show_shortcuts(self):
        QMessageBox.information(
            self,
            t("menu_keyboard_shortcuts"),
            t("shortcuts_text"),
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".scv"):
                self.open_file(url.toLocalFile())
                break

    def closeEvent(self, event):
        self._sync_current_annotations()
        if self.study.dirty:
            if self.config_mgr.settings.auto_save_notes:
                self.save_document()
            else:
                match PlayerDialogs.confirm_save_on_close(self):
                    case SaveCloseResult.CANCEL:
                        event.ignore()
                        return
                    case SaveCloseResult.SAVE:
                        self.save_document()
                    case SaveCloseResult.DISCARD:
                        pass

        self.progress_timer.stop()
        self._save_playback_progress(force=True)
        self.config_mgr.remove_listener(self._config_listener)
        self.controller.stop()
        self.controller.clear()
        self._close_session()
        super().closeEvent(event)

    def _close_session(self):
        """Release the active lecture resources and reset archive state."""
        self.progress_timer.stop()
        self.resume_banner.hide()
        self._resume_position_seconds = None
        self._pending_resume_position = None
        self._last_saved_progress = None
        if self.session:
            self.session.close()
        self.session = None
        self.source_path = None
