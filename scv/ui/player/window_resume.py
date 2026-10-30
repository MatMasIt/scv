"""Resume behavior for the player window."""

from __future__ import annotations

from PySide6.QtGui import QPalette

from scv.bookmarks import load_progress, save_progress
from scv.config.settings import AppSettings
from scv.i18n import t
from scv.models.timeline import SlideTimeline
from scv.ui.common.utils import fmt_time
from .window_host import PlayerWindowHost


class PlayerWindowResumeMixin(PlayerWindowHost):
    """Focused behavior mixed into PlayerWindow."""

    def _prepare_resume_prompt(self) -> None:
        """Show the resume banner when this lecture has a saved position."""
        self._cancel_resume_prompt_dismissal()
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

    def _resume_playback(self) -> None:
        """Seek to the saved position after the user chooses to resume."""
        if self._resume_position_seconds is None or not self.session:
            return
        self._cancel_resume_prompt_dismissal()
        position = self._resume_position_seconds
        slide_index = SlideTimeline(self.session.slide_times).current_index(position)
        self._resume_position_seconds = None
        self._pending_resume_position = position
        self.resume_banner.hide()
        self.controller.set_position(round(position * 1000))
        self._last_saved_progress = (round(position, 1), slide_index)
        self._start_progress_timer()

    def _start_from_beginning(self) -> None:
        """Dismiss the resume prompt and replace its saved point with zero."""
        if not self.session:
            return
        self._cancel_resume_prompt_dismissal()
        self._resume_position_seconds = None
        self._pending_resume_position = None
        self.resume_banner.hide()
        self.controller.set_position(0)
        self._draw_slide(0)
        self._save_playback_progress(position_seconds=0.0, force=True)
        self._start_progress_timer()

    def _cancel_resume_prompt_dismissal(self) -> None:
        """Stop the active-playback countdown and reset its duration."""
        self.resume_dismiss_timer.stop()
        self._resume_dismiss_remaining_ms = 10_000

    def _dismiss_resume_prompt_after_playing(self) -> None:
        """Hide the prompt after ten seconds of playback and save the position."""
        if self.resume_banner.isHidden():
            return
        self._resume_position_seconds = None
        self._resume_dismiss_remaining_ms = 0
        self.resume_banner.hide()
        self._save_playback_progress(force=True)
        self._start_progress_timer()

    def _start_progress_timer(self) -> None:
        """Start periodic progress saves when resume tracking is enabled."""
        if (
            self.session
            and self.config_mgr.settings.resume_playback
            and self.resume_banner.isHidden()
        ):
            self.progress_timer.start()

    def _on_config_changed(self, settings: AppSettings) -> None:
        """Apply resume preference changes while a lecture is open."""
        self._apply_resume_banner_theme(settings.theme)
        was_enabled = self._resume_setting_enabled
        self._resume_setting_enabled = settings.resume_playback
        if not settings.resume_playback:
            self._cancel_resume_prompt_dismissal()
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

    def _apply_resume_banner_theme(self, theme: str | None = None) -> None:
        """Keep the resume prompt readable in the active color theme."""
        theme = theme or self.config_mgr.settings.theme
        if theme == "dark":
            background, border, foreground = "#1e293b", "#475569", "#e2e8f0"
        elif theme == "light":
            background, border, foreground = "#eef2ff", "#c7d2fe", "#1f2937"
        else:
            window_color = self.palette().color(QPalette.ColorRole.Window)
            if window_color.lightness() < 128:
                background, border, foreground = "#1e293b", "#475569", "#e2e8f0"
            else:
                background, border, foreground = "#eef2ff", "#c7d2fe", "#1f2937"

        self.resume_banner.setStyleSheet(
            "QWidget#resumeBanner { "
            f"background: {background}; border: 1px solid {border}; "
            "border-radius: 6px; "
            "} "
            "QWidget#resumeBanner QLabel, QWidget#resumeBanner QPushButton { "
            f"color: {foreground}; "
            "}"
        )

    def _save_playback_progress(
        self,
        position_seconds: float | None = None,
        force: bool = False,
    ) -> None:
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
