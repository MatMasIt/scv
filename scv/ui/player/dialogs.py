"""Modal dialogs and user prompt abstractions for the SCV Player."""

from __future__ import annotations
from enum import Enum, auto
from PySide6.QtWidgets import QWidget, QInputDialog, QMessageBox, QLineEdit

from scv.models.tools import DrawingTool
from scv.ui.common.utils import fmt_time
from scv.i18n import t


class SaveCloseResult(Enum):
    SAVE = auto()
    DISCARD = auto()
    CANCEL = auto()


class PlayerDialogs:
    """User prompt helpers abstracting Qt modal dialog boilerplate."""

    @staticmethod
    def prompt_add_bookmark(parent: QWidget) -> str | None:
        text, ok = QInputDialog.getText(parent, t("add_bookmark_action"), t("label"))
        return text.strip() if ok and text.strip() else None

    @staticmethod
    def prompt_add_note(parent: QWidget) -> str | None:
        text, ok = QInputDialog.getMultiLineText(parent, t("add_note_action"), t("note"))
        return text.strip() if ok and text.strip() else None

    @staticmethod
    def prompt_edit_bookmark(parent: QWidget, current: str) -> str | None:
        text, ok = QInputDialog.getText(
            parent, t("edit_bookmark"), t("label"), QLineEdit.EchoMode.Normal, current
        )
        return text.strip() if ok and text.strip() else None

    @staticmethod
    def prompt_edit_note(parent: QWidget, current: str) -> str | None:
        text, ok = QInputDialog.getMultiLineText(
            parent, t("edit_note"), t("note"), current
        )
        return text.strip() if ok and text.strip() else None

    @staticmethod
    def prompt_edit_annotation_tool(
        parent: QWidget, current_tool: DrawingTool
    ) -> DrawingTool | None:
        tool_options = [
            DrawingTool.PEN,
            DrawingTool.HIGHLIGHT_YELLOW,
            DrawingTool.HIGHLIGHT_GREEN,
        ]
        labels = [t.display_name for t in tool_options]
        current_idx = tool_options.index(current_tool) if current_tool in tool_options else 0

        selected_label, ok = QInputDialog.getItem(
            parent, t("edit_slide_mark"), t("type"), labels, current_idx, False
        )
        if not ok or not selected_label:
            return None
        return tool_options[labels.index(selected_label)]

    @staticmethod
    def confirm_delete_study_item(parent: QWidget) -> bool:
        choice = QMessageBox.question(
            parent,
            t("delete_study_item_title"),
            t("delete_study_item_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return choice == QMessageBox.StandardButton.Yes

    @staticmethod
    def confirm_discard_changes(parent: QWidget) -> bool:
        choice = QMessageBox.question(
            parent,
            t("discard_study_title"),
            t("discard_study_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return choice == QMessageBox.StandardButton.Yes

    @staticmethod
    def confirm_save_on_close(parent: QWidget) -> SaveCloseResult:
        choice = QMessageBox.question(
            parent,
            t("save_study_title"),
            t("save_study_msg"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        match choice:
            case QMessageBox.StandardButton.Save:
                return SaveCloseResult.SAVE
            case QMessageBox.StandardButton.Discard:
                return SaveCloseResult.DISCARD
            case _:
                return SaveCloseResult.CANCEL

    @staticmethod
    def pick_bookmark(parent: QWidget, bookmarks: list) -> int | None:
        """Prompt user to pick a bookmark from a list and return its index."""
        if not bookmarks:
            QMessageBox.information(parent, t("bookmarks"), t("no_bookmarks_lecture"))
            return None
        entries = [
            f"{fmt_time(item.time * 1000)}  {item.label}" for item in bookmarks
        ]
        selected, ok = QInputDialog.getItem(
            parent, t("bookmarks"), t("jump_to"), entries, 0, False
        )
        if ok and selected:
            return entries.index(selected)
        return None
