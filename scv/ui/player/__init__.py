"""SCV Player package."""

import sys
from PySide6.QtWidgets import QApplication
from .window import PlayerWindow
from .document import StudyDocument
from .controller import PlayerController


def main(argv=None) -> int:
    """Create the player application and start its Qt event loop."""
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication(sys.argv if argv is None else [sys.argv[0]] + list(argv))
        owns_app = True
    app.setApplicationName("SCV Player")

    args = sys.argv[1:] if argv is None else list(argv)
    window = PlayerWindow(args[0] if args else None)
    window.show()

    if owns_app:
        return app.exec()
    return 0


__all__ = ["PlayerWindow", "StudyDocument", "PlayerController", "main"]
