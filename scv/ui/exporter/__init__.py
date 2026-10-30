"""SCV Exporter package."""

import sys
from PySide6.QtWidgets import QApplication
from .window import ExportWindow
from .worker import ExportWorker


def main(argv=None) -> int:
    """Create the exporter application and start its Qt event loop."""
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication(sys.argv if argv is None else [sys.argv[0]] + list(argv))
        owns_app = True
    app.setApplicationName("SCV Exporter")

    args = sys.argv[1:] if argv is None else list(argv)
    window = ExportWindow(args[0] if args else None)
    window.show()

    if owns_app:
        return app.exec()
    return 0


__all__ = ["ExportWindow", "ExportWorker", "main"]
