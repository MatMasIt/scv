"""Unified SCV Studio desktop application window."""

from __future__ import annotations
from pathlib import Path
import sys
from collections.abc import Callable

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QStackedWidget,
    QToolButton,
)

from scv.core import VERSION
from scv.ui.common.about import show_about
from scv.ui.common.utils import load_app_icon
from scv.ui.player import PlayerWindow
from scv.ui.encoder import EncoderWindow
from scv.ui.exporter import ExportWindow
from scv.i18n import t


class StudioWindow(QMainWindow):
    """Central unified application shell for SCV Studio."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize this component and its state."""
        super().__init__(parent)
        self.setWindowTitle(f"SCV Studio {VERSION}")
        self.resize(920, 620)
        self.setAcceptDrops(True)
        self.setWindowIcon(load_app_icon())

        self.settings = QSettings("SCV", "Studio")
        self.active_tool_windows: list[QMainWindow] = []

        self._setup_ui()
        self._setup_menus()
        self.refresh_recent_lectures()

    def _setup_ui(self) -> None:
        """Build and arrange this widget’s controls."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)

        # Header banner
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title = QLabel(t("app_title"))
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)

        subtitle = QLabel(
            t("app_subtitle")
        )
        subtitle.setStyleSheet("color: #6b7280; font-size: 14px;")
        header_layout.addWidget(subtitle)
        main_layout.addWidget(header)

        # Quick Actions Card Grid
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        # 1. Play Card
        play_card = self._create_action_card(
            title=t("card_player_title"),
            description=t("card_player_desc"),
            button_text=t("card_player_btn"),
            callback=self.launch_player,
            accent_color="#2563eb",
        )
        cards_layout.addWidget(play_card)

        # 2. Encode Card
        encode_card = self._create_action_card(
            title=t("card_encoder_title"),
            description=t("card_encoder_desc"),
            button_text=t("card_encoder_btn"),
            callback=self.launch_encoder,
            accent_color="#059669",
        )
        cards_layout.addWidget(encode_card)

        # 3. Export Card
        export_card = self._create_action_card(
            title=t("card_exporter_title"),
            description=t("card_exporter_desc"),
            button_text=t("card_exporter_btn"),
            callback=self.launch_exporter,
            accent_color="#7c3aed",
        )
        cards_layout.addWidget(export_card)

        main_layout.addLayout(cards_layout)

        # Recent Lectures Section
        recent_header = QLabel(t("recent_lectures"))
        recent_font = QFont()
        recent_font.setPointSize(14)
        recent_font.setBold(True)
        recent_header.setFont(recent_font)
        main_layout.addWidget(recent_header)

        self.recent_list = QListWidget()
        self.recent_list.setStyleSheet(
            "QListWidget { border: 1px solid #e5e7eb; border-radius: 6px; padding: 4px; }"
            "QListWidget::item { padding: 8px 12px; margin: 2px 0; border-radius: 4px; }"
            "QListWidget::item:hover { background: #f3f4f6; }"
        )
        self.recent_list.itemDoubleClicked.connect(self._on_recent_double_clicked)
        main_layout.addWidget(self.recent_list, 1)

        # Drag & drop hint bar
        drop_hint = QLabel(t("tip_drag_drop"))
        drop_hint.setStyleSheet("color: #6b7280; font-size: 12px; margin-top: 4px;")
        main_layout.addWidget(drop_hint)

    def _create_action_card(
        self,
        title: str,
        description: str,
        button_text: str,
        callback: Callable[[], None],
        accent_color: str,
    ) -> QFrame:
        """Build a launch card with a title, description, and action button."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            f"QFrame {{ background: #ffffff; border: 1px solid #e5e7eb; "
            f"border-top: 4px solid {accent_color}; border-radius: 8px; padding: 16px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        card_title = QLabel(title)
        card_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #111827;")
        layout.addWidget(card_title)

        card_desc = QLabel(description)
        card_desc.setWordWrap(True)
        card_desc.setStyleSheet("color: #4b5563; font-size: 13px; min-height: 40px;")
        layout.addWidget(card_desc, 1)

        btn = QPushButton(button_text)
        btn.setStyleSheet(
            f"QPushButton {{ background: {accent_color}; color: white; font-weight: 600; "
            f"border: none; border-radius: 6px; padding: 8px 16px; }}"
            f"QPushButton:hover {{ opacity: 0.9; }}"
        )
        btn.clicked.connect(callback)
        layout.addWidget(btn)

        return card

    def _setup_menus(self) -> None:
        """Create File, Tools, and Help menus for the studio window."""
        file_menu = self.menuBar().addMenu(t("menu_file"))
        open_action = QAction(t("menu_open_lecture"), self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.launch_player)
        file_menu.addAction(open_action)
        file_menu.addSeparator()

        exit_action = QAction(t("menu_exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = self.menuBar().addMenu(t("menu_tools"))
        player_act = QAction(t("player_title"), self)
        player_act.triggered.connect(self.launch_player)
        tools_menu.addAction(player_act)

        encoder_act = QAction(t("card_encoder_title"), self)
        encoder_act.triggered.connect(self.launch_encoder)
        tools_menu.addAction(encoder_act)

        exporter_act = QAction(t("card_exporter_title"), self)
        exporter_act.triggered.connect(self.launch_exporter)
        tools_menu.addAction(exporter_act)

        help_menu = self.menuBar().addMenu(t("menu_help"))
        about_act = QAction(t("menu_about"), self)
        about_act.triggered.connect(lambda: show_about(self, "Studio"))
        help_menu.addAction(about_act)

    def refresh_recent_lectures(self) -> None:
        """Refresh the recent lectures display."""
        player_settings = QSettings("SCV", "Player")
        recent = player_settings.value("recent", [], type=list)
        self.recent_list.clear()

        if not recent:
            item = QListWidgetItem(t("no_recent_lectures"))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.recent_list.addItem(item)
            return

        for path in recent:
            p = Path(path)
            item = QListWidgetItem(f"📹 {p.name}  —  {p.parent}")
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.recent_list.addItem(item)

    def launch_player(self, file_path: Path | str | None = None) -> None:
        """Open the player application window."""
        target = file_path
        if not target:
            path, _ = QFileDialog.getOpenFileName(
                self, t("open_scv_lecture"), str(Path.home()), t("scv_lectures_filter")
            )
            if not path:
                return
            target = path

        win = PlayerWindow(target)
        self.active_tool_windows.append(win)
        win.show()

    def launch_encoder(self) -> None:
        """Open the encoder application window."""
        win = EncoderWindow()
        self.active_tool_windows.append(win)
        win.show()

    def launch_exporter(self) -> None:
        """Open the exporter application window."""
        win = ExportWindow()
        self.active_tool_windows.append(win)
        win.show()

    def _on_recent_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle a click on recent double."""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and Path(path).exists():
            self.launch_player(path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept supported file drag operations."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle supported files dropped onto this window."""
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".scv"):
                self.launch_player(url.toLocalFile())
                break
