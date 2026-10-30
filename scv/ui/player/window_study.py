"""Study behavior for the player window."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from scv.i18n import t
from scv.models.tools import DrawingTool
from scv.ui.common.utils import fmt_time
from .dialogs import PlayerDialogs
from .window_host import PlayerWindowHost


class PlayerWindowStudyMixin(PlayerWindowHost):
    """Focused behavior mixed into PlayerWindow."""

    def _on_search_text_changed(self, text: str) -> None:
        """Filter slide results and update the search tab's match count."""
        count = self.search_dock.filter_from_slides_dock(self.slides_dock, text)
        self.slide_tabs.setTabText(
            1, t("tab_search_with_count", count=count) if text.strip() else t("tab_search")
        )

    def _on_search_slide_selected(self, index: int) -> None:
        """Switch to the timeline and seek to the selected search result."""
        self.slide_tabs.setCurrentIndex(0)
        self.slides_dock.set_current_slide(index)
        self._seek_to_slide(index)

    def _refresh_note_band(self, position_seconds: float) -> None:
        """Show the note banner active at the supplied playback position."""
        duration = self.config_mgr.settings.note_display_duration_seconds
        active = self.document.active_notes_at(position_seconds, window_seconds=duration)
        if active:
            _, note = active[-1]
            self.note_band.setText(f"{t('note_prefix')} · {fmt_time(note.time * 1000)}\n{note.label}")
            self.note_band.show()
        else:
            self.note_band.hide()

    def _on_note_band_clicked(self) -> None:
        """Open the study dock and select the note shown in the banner."""
        self.show_study_dock()
        active = self.document.active_notes_at(self.controller.position_seconds())
        if active:
            idx, _ = active[-1]
            self.study_dock.select_note_at_index(idx)

    def _on_tool_selected(self, tool: DrawingTool) -> None:
        """Apply a drawing tool to both the viewer and the study dock."""
        self.viewer.set_annotation_mode(tool)
        self.study_dock.set_active_tool(tool)

    def _on_study_dock_visibility_changed(self, visible: bool) -> None:
        """Return to pointer mode when the study tools panel is closed."""
        if not visible:
            self._on_tool_selected(DrawingTool.SELECT_PAN)

    def _on_viewer_annotation_clicked(self, index: int) -> None:
        """Open the study dock and select the clicked slide annotation."""
        self.show_study_dock()
        if self.last_index >= 0:
            self.study_dock.select_annotation(self.last_index, index)

    def _on_viewer_annotation_completed(self) -> None:
        """Persist a completed viewer stroke and refresh study controls."""
        if self.last_index < 0:
            return
        strokes = list(self.viewer.annotations)
        self.study.sync_annotations(self.last_index, strokes)
        self._refresh_study_ui()
        if strokes:
            self.study_dock.select_annotation(self.last_index, len(strokes) - 1)

    def _sync_current_annotations(self) -> None:
        """Copy the viewer's current annotations into the study document."""
        if self.source_path and self.last_index >= 0:
            self.study.sync_annotations(self.last_index, self.viewer.annotations)

    def clear_annotations(self) -> None:
        """Remove every annotation from the currently displayed slide."""
        if self.last_index < 0 or not self.source_path:
            return
        self.viewer.clear_annotations()
        self.document.clear_slide_annotations(self.last_index)
        self._refresh_study_ui()
        self._update_action_states()

    def toggle_study_dock(self) -> None:
        """Toggle visibility of the study dock."""
        self.study_dock.setVisible(not self.study_dock.isVisible())

    def show_study_dock(self) -> None:
        """Show and raise the study dock."""
        self.study_dock.show()
        self.study_dock.raise_()

    def _refresh_study_ui(self) -> None:
        """Refresh study markers, the notes banner, and action enablement."""
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

    def _jump_to_bookmark(self, index: int) -> None:
        """Seek playback to the selected bookmark."""
        if 0 <= index < len(self.document.bookmarks):
            self._pending_resume_position = None
            self.controller.set_position(round(self.document.bookmarks[index].time * 1000))

    def _jump_to_note(self, index: int) -> None:
        """Seek playback to the selected note."""
        if 0 <= index < len(self.document.notes):
            self._pending_resume_position = None
            self.controller.set_position(round(self.document.notes[index].time * 1000))

    def _jump_to_annotation(self, slide_index: int, annotation_index: int) -> None:
        """Seek to a slide and select one of its annotations."""
        self._seek_to_slide(slide_index)
        self.viewer.set_selected_annotation(annotation_index)

    def _on_note_visibility_changed(self, index: int, show: bool) -> None:
        """Update whether a note appears in the playback banner."""
        self.document.set_note_visibility(index, show)
        self._refresh_note_band(self.controller.position_seconds())
        self._update_action_states()

    def add_bookmark(self) -> None:
        """Prompt for and add a bookmark at the current playback position."""
        if not self.session or not self.source_path:
            return
        label = PlayerDialogs.prompt_add_bookmark(self)
        if label:
            self.document.add_bookmark(self.controller.position_seconds(), label)
            self._refresh_study_ui()
            self.statusBar().showMessage(f"Bookmark added: {label}")

    def add_note(self) -> None:
        """Prompt for and add a note at the current playback position."""
        if not self.session or not self.source_path:
            return
        text = PlayerDialogs.prompt_add_note(self)
        if text:
            self.document.add_note(self.controller.position_seconds(), text)
            self._refresh_study_ui()
            self.statusBar().showMessage("Note added")

    def edit_study_item(self) -> None:
        """Edit the currently selected bookmark, note, or annotation."""
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

    def delete_study_item(self) -> None:
        """Confirm and delete the selected study item."""
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

    def show_bookmarks(self) -> None:
        """Prompt for a bookmark and seek to it when selected."""
        idx = PlayerDialogs.pick_bookmark(self, self.document.bookmarks)
        if idx is not None:
            self._jump_to_bookmark(idx)

    def save_document(self) -> None:
        """Synchronize visible annotations and save the study document."""
        self._sync_current_annotations()
        if self.source_path:
            self.study.save()
            self.statusBar().showMessage(t("study_changes_saved"))
            self._update_action_states()

    def discard_document(self) -> None:
        """Reload saved study data after confirming any pending edits."""
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

    def _update_action_states(self) -> None:
        """Enable menu actions according to the active lecture and selection."""
        loaded = self.session is not None and self.source_path is not None
        current_slide = loaded and self.last_index >= 0
        has_selection = self.study_dock.current_target() is not None
        self.player_menu.update_action_states(
            has_lecture=loaded,
            has_slide=current_slide,
            has_selection=has_selection,
            is_dirty=self.document.dirty,
        )
