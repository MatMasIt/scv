"""Playback behavior for the player window."""

from __future__ import annotations

from PySide6.QtGui import QImage, QPixmap
from PySide6.QtGui import QResizeEvent

from scv.ui.common.utils import fmt_time
from .window_host import PlayerWindowHost


class PlayerWindowPlaybackMixin(PlayerWindowHost):
    """Focused behavior mixed into PlayerWindow."""

    def _seek_step_ms(self) -> int:
        """Return the configured keyboard seek distance in milliseconds."""
        return self.config_mgr.settings.seek_step_seconds * 1000

    def _on_transport_seek(self, delta_ms: int) -> None:
        """Seek by the transport control's signed step request."""
        self._pending_resume_position = None
        sign = -1 if delta_ms < 0 else 1
        step = self._seek_step_ms() * sign
        self.controller.seek_by(step)

    def _jump_slide(self, direction: int) -> None:
        """Move to the adjacent slide in the requested direction."""
        self._pending_resume_position = None
        self.controller.jump_slide(direction)

    def _seek_to_slide(self, index: int) -> None:
        """Seek to the first timestamp associated with a slide."""
        self._pending_resume_position = None
        self.controller.seek_to_slide(index)

    def _toggle_playback(self) -> None:
        """Toggle playback when a lecture is loaded."""
        if self.session:
            self.controller.toggle()

    def _on_playback_state(self, state: str) -> None:
        """Update transport state and count active playback for the resume banner."""
        playing = self.controller.is_playing()
        self.transport_bar.set_playing_state(playing)
        if self.resume_banner.isHidden():
            return
        if playing:
            if not self.resume_dismiss_timer.isActive():
                self.resume_dismiss_timer.start(
                    max(1, self._resume_dismiss_remaining_ms)
                )
        elif self.resume_dismiss_timer.isActive():
            self._resume_dismiss_remaining_ms = max(
                1, self.resume_dismiss_timer.remainingTime()
            )
            self.resume_dismiss_timer.stop()

    def _on_seek_released(self) -> None:
        """Apply the seek slider's selected position after dragging ends."""
        self.seeking = False
        self._pending_resume_position = None
        self.controller.set_position(self.seek.value())
        self._on_playback_position(self.seek.value())

    def _on_playback_position(self, ms: int) -> None:
        """Refresh playback labels, slide selection, notes, and study controls."""
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

    def _draw_slide(self, index: int) -> None:
        """Display a slide from cache or request its image asynchronously."""
        if (
            not self.session
            or index < 0
            or index >= len(self.session.slide_models)
        ):
            return
        if (
            self.last_index >= 0
            and index != self.last_index
            and index != self._requested_slide_index
        ):
            self._sync_current_annotations()
        self._requested_slide_index = index
        cached = self._slide_pixmap_cache.get(index)
        if cached is not None:
            self._slide_pixmap_cache.move_to_end(index)
            self._show_slide(index, cached)
        elif not self._frame_load_running:
            self.viewer.setEnabled(False)
            self._start_frame_load()

    def _start_frame_load(self) -> None:
        """Queue decoding for the currently requested slide image."""
        if self.session is None or self._requested_slide_index is None:
            return
        index = self._requested_slide_index
        cached = self._slide_pixmap_cache.get(index)
        if cached is not None:
            self._slide_pixmap_cache.move_to_end(index)
            self._show_slide(index, cached)
            return
        slide = self.session.slide_models[index]
        path = self.session.root / slide.image.as_posix()
        key = ("frame", self._session_generation, index)
        self._frame_load_running = True
        self.image_loader.load(key, path, priority=1, resource_owner=self.session)

    def _on_image_loaded(self, key: object, image: QImage, error: str) -> None:
        """Cache a decoded frame and display it if it is still the requested slide."""
        self._cleanup_retired_sessions()
        if not isinstance(key, tuple) or len(key) != 3 or key[0] != "frame":
            return

        _, generation, index = key
        self._frame_load_running = False
        if generation == self._session_generation and not image.isNull():
            pixmap = QPixmap.fromImage(image)
            self._cache_slide_pixmap(index, pixmap)
            if self.session and index == self._requested_slide_index:
                self._show_slide(index, pixmap)
        elif (
            generation == self._session_generation
            and index == self._requested_slide_index
        ):
            self.viewer.setEnabled(True)
            self._requested_slide_index = None
            self.statusBar().showMessage(f"Image error: {error}")

        if self.session and self._requested_slide_index is not None:
            if (
                generation != self._session_generation
                or index != self._requested_slide_index
            ):
                self._start_frame_load()

    def _cache_slide_pixmap(self, index: int, pixmap: QPixmap) -> None:
        """Insert a pixmap into the bounded least-recently-used frame cache."""
        cost = self._pixmap_memory_cost(pixmap)
        if cost <= 0 or cost > self._slide_pixmap_cache_limit:
            return
        previous = self._slide_pixmap_cache.pop(index, None)
        if previous is not None:
            self._slide_pixmap_cache_bytes -= self._pixmap_memory_cost(previous)
        while (
            self._slide_pixmap_cache
            and self._slide_pixmap_cache_bytes + cost > self._slide_pixmap_cache_limit
        ):
            _, oldest = self._slide_pixmap_cache.popitem(last=False)
            self._slide_pixmap_cache_bytes -= self._pixmap_memory_cost(oldest)
        self._slide_pixmap_cache[index] = pixmap
        self._slide_pixmap_cache_bytes += cost

    @staticmethod
    def _pixmap_memory_cost(pixmap: QPixmap) -> int:
        """Estimate storage using Qt's 32-bit aligned scanline layout."""
        row_bytes = ((pixmap.width() * pixmap.depth() + 31) // 32) * 4
        return row_bytes * pixmap.height()

    def _show_slide(self, index: int, pixmap: QPixmap) -> None:
        """Install the slide image and synchronize its annotations and dock state."""
        if self.last_index >= 0 and index != self.last_index:
            self._sync_current_annotations()
        self.original_pixmap = pixmap
        self.last_index = index
        self.viewer.setEnabled(True)
        self.viewer.set_annotations(self.document.get_slide_annotations(index))
        self._refresh_slide_image()
        self.slides_dock.set_current_slide(index)

    def _refresh_slide_image(self) -> None:
        """Refresh the viewer with the current source pixmap."""
        if self.original_pixmap and not self.original_pixmap.isNull():
            self.viewer.setPixmap(self.original_pixmap)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Repaint the viewer after the main window changes size."""
        super().resizeEvent(event)
        self.viewer.update()
