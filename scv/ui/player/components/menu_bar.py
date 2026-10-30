"""Main menu bar component for the SCV Player."""

from __future__ import annotations
from collections.abc import Callable, Mapping
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenuBar, QMenu, QWidget

from scv.i18n import t
from scv.models.tools import DrawingTool
from scv.ui.common.about import show_about
from scv.ui.common.settings_dialog import SettingsDialog


class PlayerMenuBar(QMenuBar):
    """Component managing top-level menus, actions, and dynamic enabling."""

    def __init__(
        self,
        parent: QWidget,
        callbacks: Mapping[str, Callable[..., object]],
    ) -> None:
        """Create the player menus and connect their actions to callbacks."""
        super().__init__(parent)
        self.callbacks = callbacks
        self.actions_registry: dict[str, QAction] = {}
        self._setup_menus()

    def _setup_menus(self) -> None:
        """Create file, study, view, settings, and help menus."""
        cb = self.callbacks

        # 1. File Menu
        file_menu = self.addMenu(t("menu_file"))
        open_act = file_menu.addAction(t("menu_open"), cb.get("open"))
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        file_menu.addSeparator()

        save_study = file_menu.addAction(t("menu_save_study"), cb.get("save_study"))
        save_study.setShortcut(QKeySequence.StandardKey.Save)
        discard_study = file_menu.addAction(t("menu_discard_study"), cb.get("discard_study"))
        discard_study.setShortcut("Ctrl+Shift+Z")
        self.actions_registry.update(save_study=save_study, discard_study=discard_study)

        self.recent_menu = file_menu.addMenu(t("menu_recent_files"))
        file_menu.addSeparator()

        settings_act = file_menu.addAction(t("menu_preferences"), self._open_settings)
        settings_act.setShortcut("Ctrl+,")
        file_menu.addSeparator()

        close_act = file_menu.addAction(t("menu_close"), cb.get("close"))

        # 2. Study Menu
        study_menu = self.addMenu(t("study"))
        self.actions_registry["show_study"] = study_menu.addAction(
            t("show_study_panel"), cb.get("show_study")
        )
        self.actions_registry["add_bookmark"] = study_menu.addAction(
            t("add_bookmark"), cb.get("add_bookmark")
        )
        self.actions_registry["add_note"] = study_menu.addAction(
            t("add_note"), cb.get("add_note")
        )
        study_menu.addSeparator()

        self.actions_registry["edit_study"] = study_menu.addAction(
            t("edit_selected_item"), cb.get("edit_study")
        )
        self.actions_registry["delete_study"] = study_menu.addAction(
            t("delete_selected_item"), cb.get("delete_study")
        )
        study_menu.addSeparator()

        anno_menu = study_menu.addMenu(t("annotations"))
        tool_cb = cb.get("select_tool", lambda t: None)
        self.actions_registry["select_pan"] = anno_menu.addAction(
            t("select_pan"), lambda: tool_cb(DrawingTool.SELECT_PAN)
        )
        self.actions_registry["pen"] = anno_menu.addAction(
            t("pen"), lambda: tool_cb(DrawingTool.PEN)
        )
        self.actions_registry["yellow"] = anno_menu.addAction(
            t("yellow_highlighter"), lambda: tool_cb(DrawingTool.HIGHLIGHT_YELLOW)
        )
        self.actions_registry["green"] = anno_menu.addAction(
            t("green_highlighter"), lambda: tool_cb(DrawingTool.HIGHLIGHT_GREEN)
        )
        self.actions_registry["clear_marks"] = anno_menu.addAction(
            t("clear_marks_current"), cb.get("clear_annotations")
        )

        # 3. View Menu
        view_menu = self.addMenu(t("menu_view"))
        fs_act = view_menu.addAction(t("fullscreen"), cb.get("fullscreen"))
        fs_act.setShortcut("F11")
        fs_act.setShortcutContext(Qt.ShortcutContext.WindowShortcut)

        view_menu.addAction(t("zoom_in"), cb.get("zoom_in")).setShortcut("+")
        view_menu.addAction(t("zoom_out"), cb.get("zoom_out")).setShortcut("-")
        view_menu.addAction(t("reset_view"), cb.get("reset_view")).setShortcut("0")

        thumb_act = view_menu.addAction(t("toggle_thumbnails"), cb.get("toggle_thumbnails"))
        thumb_act.setShortcut("T")
        thumb_act.setShortcutContext(Qt.ShortcutContext.WindowShortcut)

        view_menu.addAction(t("study_panel"), cb.get("toggle_study"))
        view_menu.addAction(t("bookmarks"), cb.get("show_bookmarks")).setShortcut("B")

        # 4. Settings Menu
        settings_menu = self.addMenu(t("menu_settings"))
        settings_menu.addAction(t("menu_preferences"), self._open_settings).setShortcut("Ctrl+,")

        # 5. Help Menu
        help_menu = self.addMenu(t("menu_help"))
        help_menu.addAction(t("menu_keyboard_shortcuts"), cb.get("show_shortcuts"))
        help_menu.addAction(t("menu_about"), lambda: show_about(self.parent(), "Player"))

    def _open_settings(self) -> None:
        """Open the application preferences dialog."""
        """Open the application preferences dialog."""
        dlg = SettingsDialog(self.parent())
        dlg.exec()

    def update_action_states(
        self,
        has_lecture: bool,
        has_slide: bool,
        has_selection: bool,
        is_dirty: bool,
    ) -> None:
        """Enable menu actions according to lecture, selection, and edit state."""
        """Update the action states state."""
        for name in ("add_bookmark", "add_note", "select_pan", "pen", "yellow", "green", "show_study"):
            if name in self.actions_registry:
                self.actions_registry[name].setEnabled(has_lecture)
        if "edit_study" in self.actions_registry:
            self.actions_registry["edit_study"].setEnabled(has_selection)
        if "delete_study" in self.actions_registry:
            self.actions_registry["delete_study"].setEnabled(has_selection)
        if "clear_marks" in self.actions_registry:
            self.actions_registry["clear_marks"].setEnabled(has_slide)
        if "save_study" in self.actions_registry:
            self.actions_registry["save_study"].setEnabled(has_lecture and is_dirty)
        if "discard_study" in self.actions_registry:
            self.actions_registry["discard_study"].setEnabled(has_lecture and is_dirty)

    def populate_recent_files(
        self, paths: list[str], open_callback: Callable[[str], None]
    ) -> None:
        """Rebuild the recent lecture submenu and connect each path to its opener."""
        """Rebuild the recent lecture submenu and connect each path to its opener."""
        self.recent_menu.clear()
        for path in paths:
            action = self.recent_menu.addAction(path)
            action.triggered.connect(lambda checked=False, p=path: open_callback(p))
