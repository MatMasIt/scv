"""SCV Studio application package."""

import sys
from PySide6.QtWidgets import QApplication
from .window import StudioWindow


def main(argv=None) -> int:
    """Create the SCV Studio application and start its Qt event loop."""
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication(sys.argv if argv is None else [sys.argv[0]] + list(argv))
        owns_app = True
    app.setApplicationName("SCV Studio")

    window = StudioWindow()
    window.show()

    if owns_app:
        return app.exec()
    return 0


__all__ = ["StudioWindow", "main"]
