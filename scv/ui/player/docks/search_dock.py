"""Slide search dock widget with OCR text matching and preview."""

from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)
from scv.i18n import t


class SearchDockWidget(QWidget):
    """Panel for querying slides by slide number or recognized OCR text."""

    slideSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        search_title = QLabel(t("slide_search_title"))
        search_title.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(search_title)

        search_hint = QLabel(t("slide_search_hint"))
        search_hint.setStyleSheet("color: #6b7280;")
        layout.addWidget(search_hint)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_placeholder"))
        self.search_input.setClearButtonEnabled(True)
        layout.addWidget(self.search_input)

        self.search_results = QListWidget()
        self.search_results.setIconSize(QSize(180, 100))
        self.search_results.setSpacing(6)
        self.search_results.setStyleSheet(
            "QListWidget::item { padding: 6px; margin: 2px; }"
        )
        self.search_results.itemDoubleClicked.connect(self._on_item_activated)
        layout.addWidget(self.search_results, 1)

    def filter_from_slides_dock(self, slides_dock, query: str) -> int:
        """Filter slides from ``slides_dock`` matching ``query`` and return match count."""
        clean_query = query.casefold().strip()
        self.search_results.clear()
        if not clean_query:
            return 0

        count = slides_dock.count()
        match_count = 0
        for index in range(count):
            item = slides_dock.item(index)
            if not item:
                continue
            searchable = item.text().casefold()
            slide_text = str(item.data(Qt.ItemDataRole.UserRole) or "")
            searchable_text = slide_text.casefold()

            if clean_query in searchable or clean_query in searchable_text:
                match_count += 1
                slide_number = index + 1
                timestamp = item.text().split("•", 1)[-1].strip()
                excerpt = " ".join(slide_text.split())
                if len(excerpt) > 180:
                    excerpt = excerpt[:177].rstrip() + "..."

                result = QListWidgetItem("")
                result.setData(Qt.ItemDataRole.UserRole, index)
                result.setToolTip(slide_text)
                self.search_results.addItem(result)

                result_widget = QWidget()
                result_layout = QHBoxLayout(result_widget)
                result_layout.setContentsMargins(8, 4, 8, 4)

                thumbnail = QLabel()
                thumbnail.setFixedSize(180, 100)
                thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
                thumbnail.setPixmap(
                    item.icon().pixmap(
                        180,
                        100,
                        QIcon.Mode.Normal,
                        QIcon.State.Off,
                    )
                )
                result_layout.addWidget(thumbnail)

                details = QVBoxLayout()
                heading = QLabel(f"{t('slide_counter', current=slide_number, total=slides_dock.count())}  ·  {timestamp}")
                heading.setStyleSheet("font-weight: 600;")
                details.addWidget(heading)

                text = QLabel(excerpt or t("no_ocr_text"))
                text.setWordWrap(True)
                text.setStyleSheet("color: #6b7280;")
                details.addWidget(text)
                details.addStretch(1)

                result_layout.addLayout(details, 1)
                self.search_results.setItemWidget(result, result_widget)
                result.setSizeHint(QSize(0, 132))

        return match_count

    def clear(self):
        self.search_input.clear()
        self.search_results.clear()

    def _on_item_activated(self, item: QListWidgetItem):
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is not None:
            self.slideSelected.emit(index)
