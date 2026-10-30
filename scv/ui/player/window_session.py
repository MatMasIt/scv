"""Session behavior for the player window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox

from scv.core import LectureSession
from scv.i18n import t
from scv.ui.common.utils import fmt_time
from .dialogs import PlayerDialogs, SaveCloseResult
from .docks.slides_dock import SlideInfo
from .window_host import PlayerWindowHost


class PlayerWindowSessionMixin(PlayerWindowHost):
    """Focused behavior mixed into PlayerWindow."""

    def pick(self) -> None:
        """Open a file picker and start loading the selected lecture."""
        path, _ = QFileDialog.getOpenFileName(
            self, t("menu_open_lecture"), str(Path.home()), "SCV lectures (*.scv)"
        )
        if path:
            self.open_file(path)

    def open_file(self, path: Path | str) -> None:
        """Validate pending study changes and request an asynchronous lecture load."""
        source_path = Path(path).expanduser().resolve()
        if self.session and source_path == self.session.source_path:
            return

        if not self._confirm_study_changes_before_switch():
            return

        self._study_switch_snapshot = self.document.to_dict()
        self._open_request_id += 1
        request_id = self._open_request_id
        self.statusBar().showMessage(t("opening_lecture", name=source_path.name))
        self.lecture_loader.load(request_id, source_path)

    def _on_lecture_loaded(
        self,
        request_id: int,
        session: LectureSession | None,
        error: Exception | None,
    ) -> None:
        """Attach a completed lecture load and refresh all session-bound widgets."""
        if request_id != self._open_request_id or self._closing:
            if session:
                session.close()
            return
        if error:
            self._study_switch_snapshot = None
            self.statusBar().clearMessage()
            QMessageBox.critical(self, t("cannot_open_scv"), str(error))
            return
        if session is None:
            self._study_switch_snapshot = None
            return

        # Re-prompt only if the current document changed while extraction ran.
        self._sync_current_annotations()
        changed_while_loading = (
            self.study.dirty
            and self.document.to_dict() != self._study_switch_snapshot
        )
        if changed_while_loading and not self._confirm_study_changes_before_switch():
            self._study_switch_snapshot = None
            self.statusBar().clearMessage()
            session.close()
            return
        self._study_switch_snapshot = None

        if self.session:
            self._save_playback_progress(force=True)
        self.controller.stop()
        self.controller.clear()
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

        slide_infos: list[SlideInfo] = [
            {
                "time": slide.time,
                "image": str(slide.image),
                "text": slide.text or "",
            }
            for slide in session.slide_models
        ]
        self.slides_dock.load_slides(
            slide_infos,
            session.root,
            resource_owner=session,
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
        self._draw_slide(0)

    def _confirm_study_changes_before_switch(self) -> bool:
        """Resolve edits before replacing the active study document."""
        self._sync_current_annotations()
        if not self.study.dirty:
            return True

        if self.config_mgr.settings.auto_save_notes:
            return self._save_study_before_leaving()

        choice = PlayerDialogs.confirm_save_before_switch(self)
        if choice == SaveCloseResult.CANCEL:
            return False
        if choice == SaveCloseResult.DISCARD:
            return True
        return self._save_study_before_leaving()

    def _confirm_study_changes_before_close(self) -> bool:
        """Resolve dirty study edits before allowing the player window to close."""
        self._sync_current_annotations()
        if not self.study.dirty:
            return True
        if self.config_mgr.settings.auto_save_notes:
            return self._save_study_before_leaving()

        choice = PlayerDialogs.confirm_save_on_close(self)
        if choice == SaveCloseResult.CANCEL:
            return False
        if choice == SaveCloseResult.DISCARD:
            return True
        return self._save_study_before_leaving()

    def _save_study_before_leaving(self) -> bool:
        """Save dirty study data and report whether the save succeeded."""
        try:
            self.save_document()
        except Exception as exc:
            QMessageBox.critical(self, t("cannot_save_study"), str(exc))
            return False
        return not self.study.dirty

    def _update_recent_menu(self) -> None:
        """Refresh the recent lecture menu from the persisted settings."""
        self.player_menu.populate_recent_files(
            self.config_mgr.settings.recent_files, self.open_file
        )

    def _close_session(self) -> None:
        """Release the active lecture resources and reset archive state."""
        self._session_generation += 1
        self._slide_pixmap_cache.clear()
        self._slide_pixmap_cache_bytes = 0
        self._requested_slide_index = None
        self.progress_timer.stop()
        self._cancel_resume_prompt_dismissal()
        self.resume_banner.hide()
        self._resume_position_seconds = None
        self._pending_resume_position = None
        self._last_saved_progress = None
        if self.session:
            if self.image_loader.has_active_loads_under(self.session.root):
                self._retired_sessions.append(self.session)
            else:
                self.session.close()
        self.session = None
        self.source_path = None
        self.last_index = -1
        self.original_pixmap = QPixmap()
        self.viewer.setEnabled(False)
        self.viewer.setPixmap(QPixmap())
        self.viewer.set_annotations([])
        self.slides_dock.clear()
        self.search_dock.clear()
        self.seek.setMaximum(0)
        self.seek.setValue(0)
        self.seek.set_markers([])
        self.seek.set_study_markers([], [])
        self.time_label.setText("00:00:00")
        self.duration_label.setText("00:00:00")

    def _cleanup_retired_sessions(self) -> None:
        """Release retired lecture archives after their image loads complete."""
        still_loading = []
        for session in self._retired_sessions:
            if self.image_loader.has_active_loads_under(session.root):
                still_loading.append(session)
            else:
                session.close()
        self._retired_sessions = still_loading
