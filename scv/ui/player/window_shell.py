"""Shell behavior for the player window."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QMessageBox

from scv.i18n import t
from .window_host import PlayerWindowHost


class PlayerWindowShellMixin(PlayerWindowHost):
    """Focused behavior mixed into PlayerWindow."""

    def _install_shortcuts(self) -> None:
        """Register keyboard and media-key shortcuts for the player."""
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

    def _register_shortcut(
        self, sequence: QKeySequence, callback: Callable[[], None]
    ) -> None:
        """Register a window-local shortcut and retain it for the window lifetime."""
        shortcut = QShortcut(sequence, self)
        shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        shortcut.activated.connect(callback)
        self.shortcuts.append(shortcut)

    def toggle_fullscreen(self) -> None:
        """Toggle fullscreen while hiding or restoring window chrome."""
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
            self.statusBar().show()
        else:
            self.showFullScreen()
            self.menuBar().hide()
            self.statusBar().hide()

    def show_shortcuts(self) -> None:
        """Display the keyboard shortcut reference dialog."""
        QMessageBox.information(
            self,
            t("menu_keyboard_shortcuts"),
            t("shortcuts_text"),
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag operations that carry local-file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Open the first local SCV lecture dropped onto the player."""
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".scv"):
                self.open_file(url.toLocalFile())
                break

    def closeEvent(self, event: QCloseEvent) -> None:
        """Resolve unsaved study changes and release player resources."""
        if not self._confirm_study_changes_before_close():
            event.ignore()
            return

        self._closing = True
        self._open_request_id += 1
        self.progress_timer.stop()
        self._save_playback_progress(force=True)
        self.config_mgr.remove_listener(self._config_listener)
        self.controller.stop()
        self.controller.clear()
        self._close_session()
        super().closeEvent(event)
