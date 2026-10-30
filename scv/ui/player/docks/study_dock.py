"""Study dock widget for bookmarks, notes, and slide annotations."""

from __future__ import annotations
from dataclasses import dataclass
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QButtonGroup,
    QGroupBox,
    QMenu,
)

from scv.models.study import StudyDocument
from scv.models.tools import DrawingTool
from scv.ui.common.utils import fmt_time
from scv.i18n import t


@dataclass(frozen=True)
class StudyItemTarget:
    """Strongly-typed reference to a study item in a document."""

    kind: str  # "bookmark", "note", "annotation"
    index: int
    slide_index: int = 0

    @property
    def is_annotation(self) -> bool:
        return self.kind == "annotation"

    @property
    def is_bookmark(self) -> bool:
        return self.kind == "bookmark"

    @property
    def is_note(self) -> bool:
        return self.kind == "note"


class StudyDockWidget(QDockWidget):
    """Panel providing study tools: notes, bookmarks, marks, and drawing tools."""

    jumpToBookmarkRequested = Signal(int)
    jumpToNoteRequested = Signal(int)
    jumpToSlideAnnotationRequested = Signal(int, int)  # slide_index, annotation_index
    addBookmarkRequested = Signal()
    addNoteRequested = Signal()
    editItemRequested = Signal()
    deleteItemRequested = Signal()
    clearMarksRequested = Signal()
    toolSelected = Signal(object)  # DrawingTool
    noteVisibilityChanged = Signal(int, bool)
    selectionChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(t("study"), parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.tool_buttons: dict[DrawingTool, QToolButton] = {}
        self._setup_ui()

    def _setup_ui(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.study_tabs = QTabWidget()
        self.bookmark_list = QListWidget()
        self.note_list = QListWidget()
        self.annotation_list = QListWidget()

        self.study_tabs.addTab(self.bookmark_list, t("tab_bookmarks"))
        self.study_tabs.addTab(self.note_list, t("tab_notes"))
        self.study_tabs.addTab(self.annotation_list, t("tab_slide_marks"))
        self.study_tabs.currentChanged.connect(self._on_tab_changed)

        for widget in (self.bookmark_list, self.note_list, self.annotation_list):
            widget.itemDoubleClicked.connect(self._on_item_clicked)
            widget.itemClicked.connect(self._on_item_clicked)
            widget.itemSelectionChanged.connect(self._on_selection_changed)
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            widget.customContextMenuRequested.connect(self._on_context_menu)
            widget.installEventFilter(self)

        self.note_list.itemChanged.connect(self._on_note_item_changed)
        layout.addWidget(self.study_tabs, 1)

        # Action buttons
        actions = QHBoxLayout()
        add_bm_btn = QPushButton(t("add_bookmark_action"))
        add_bm_btn.clicked.connect(self.addBookmarkRequested.emit)
        add_note_btn = QPushButton(t("add_note_action"))
        add_note_btn.clicked.connect(self.addNoteRequested.emit)
        self.edit_btn = QPushButton(t("edit_action"))
        self.edit_btn.clicked.connect(self.editItemRequested.emit)
        self.delete_btn = QPushButton(t("delete_action"))
        self.delete_btn.clicked.connect(self.deleteItemRequested.emit)

        actions.addWidget(add_bm_btn)
        actions.addWidget(add_note_btn)
        actions.addWidget(self.edit_btn)
        actions.addWidget(self.delete_btn)
        layout.addLayout(actions)

        # Drawing tools box
        toolbox = QGroupBox(t("slide_drawing_tools"))
        toolbox_layout = QHBoxLayout(toolbox)
        toolbox_layout.setContentsMargins(6, 6, 6, 6)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        for tool in DrawingTool:
            btn = QToolButton()
            btn.setText(tool.icon_symbol)
            btn.setToolTip(tool.display_name)
            btn.setCheckable(True)
            btn.setFixedSize(38, 34)
            btn.setStyleSheet(
                f"QToolButton {{ color: {tool.color}; font-size: 19px; }}"
                "QToolButton:checked { background: #dbeafe; border: 2px solid #2563eb; "
                "border-radius: 4px; }"
            )
            btn.clicked.connect(lambda checked=False, t=tool: self.toolSelected.emit(t))
            self.button_group.addButton(btn)
            toolbox_layout.addWidget(btn)
            self.tool_buttons[tool] = btn

            if tool == DrawingTool.SELECT_PAN:
                btn.setChecked(True)

        toolbox_layout.addStretch(1)
        layout.addWidget(toolbox)

        clear_marks_btn = QPushButton(t("clear_marks_current"))
        clear_marks_btn.clicked.connect(self.clearMarksRequested.emit)
        layout.addWidget(clear_marks_btn)

        self.setWidget(panel)
        self._refresh_actions()

    def set_active_tool(self, tool: DrawingTool):
        btn = self.tool_buttons.get(tool)
        if btn:
            btn.setChecked(True)

    def current_target(self) -> StudyItemTarget | None:
        """Return the target descriptor for the currently selected study item."""
        widget = self.study_tabs.currentWidget()
        if not isinstance(widget, QListWidget):
            return None
        item = widget.currentItem()
        if not item:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, StudyItemTarget) else None

    def refresh_from_document(self, document: StudyDocument):
        """Populate list widgets with typed items from ``document``."""
        for widget in (self.bookmark_list, self.note_list, self.annotation_list):
            widget.blockSignals(True)
            widget.clear()
            widget.blockSignals(False)

        # 1. Bookmarks
        for index, bm in enumerate(document.bookmarks):
            row = QListWidgetItem(f"{fmt_time(bm.time * 1000)}  {bm.label}")
            row.setData(Qt.ItemDataRole.UserRole, StudyItemTarget(kind="bookmark", index=index))
            row.setForeground(QColor("#60a5fa"))
            self.bookmark_list.addItem(row)

        # 2. Notes
        self.note_list.blockSignals(True)
        for index, note in enumerate(document.notes):
            row = QListWidgetItem(f"{fmt_time(note.time * 1000)}  {note.label}")
            row.setData(Qt.ItemDataRole.UserRole, StudyItemTarget(kind="note", index=index))
            row.setFlags(row.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            row.setCheckState(Qt.CheckState.Checked if note.show else Qt.CheckState.Unchecked)
            row.setForeground(QColor("#a78bfa"))
            self.note_list.addItem(row)
        self.note_list.blockSignals(False)

        # 3. Slide Annotations
        for slide_idx, strokes in sorted(document.annotations.items()):
            for anno_idx, stroke in enumerate(strokes):
                label = document.annotation_label(stroke, slide_idx, anno_idx)
                row = QListWidgetItem(label)
                row.setData(
                    Qt.ItemDataRole.UserRole,
                    StudyItemTarget(kind="annotation", index=anno_idx, slide_index=slide_idx),
                )
                row.setForeground(QColor(stroke.color))
                self.annotation_list.addItem(row)

        self._refresh_actions()

    def select_annotation(self, slide_index: int, annotation_index: int):
        self.study_tabs.setCurrentWidget(self.annotation_list)
        for row in range(self.annotation_list.count()):
            item = self.annotation_list.item(row)
            target = item.data(Qt.ItemDataRole.UserRole)
            if (
                isinstance(target, StudyItemTarget)
                and target.slide_index == slide_index
                and target.index == annotation_index
            ):
                self.annotation_list.setCurrentItem(item)
                return

    def select_note_at_index(self, index: int):
        self.study_tabs.setCurrentWidget(self.note_list)
        if 0 <= index < self.note_list.count():
            self.note_list.setCurrentRow(index)

    def eventFilter(self, watched, event):
        if (
            watched in (self.bookmark_list, self.note_list, self.annotation_list)
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Delete
            and watched.currentItem() is not None
        ):
            self.study_tabs.setCurrentWidget(watched)
            self.deleteItemRequested.emit()
            return True
        return super().eventFilter(watched, event)

    def _on_tab_changed(self):
        self._refresh_actions()

    def _on_selection_changed(self):
        self._refresh_actions()

    def _refresh_actions(self):
        has_item = self.current_target() is not None
        self.edit_btn.setEnabled(has_item)
        self.delete_btn.setEnabled(has_item)
        self.selectionChanged.emit(has_item)

    def _on_item_clicked(self, item: QListWidgetItem):
        target = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(target, StudyItemTarget):
            return

        if target.is_annotation:
            self.jumpToSlideAnnotationRequested.emit(target.slide_index, target.index)
        elif target.is_bookmark:
            self.jumpToBookmarkRequested.emit(target.index)
        elif target.is_note:
            self.jumpToNoteRequested.emit(target.index)

    def _on_note_item_changed(self, item: QListWidgetItem):
        target = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(target, StudyItemTarget) and target.is_note:
            show = item.checkState() == Qt.CheckState.Checked
            self.noteVisibilityChanged.emit(target.index, show)

    def _on_context_menu(self, position):
        widget = self.sender()
        if not isinstance(widget, QListWidget):
            return
        item = widget.itemAt(position)
        if not item:
            return
        widget.setCurrentItem(item)
        menu = QMenu(self)
        menu.addAction(t("jump_to_action"), lambda: self._on_item_clicked(item))
        menu.addAction(t("edit_action"), self.editItemRequested.emit)
        menu.addAction(t("delete_action"), self.deleteItemRequested.emit)
        menu.exec(widget.viewport().mapToGlobal(position))
