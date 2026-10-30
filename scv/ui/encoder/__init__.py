"""SCV Encoder package."""

import sys
from PySide6.QtWidgets import QApplication
from .window import EncoderWindow
from .worker import QueueWorker


def main(argv: list[str] | None = None) -> int:
    """Create the encoder application and start its Qt event loop."""
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication(sys.argv if argv is None else [sys.argv[0]] + list(argv))
        owns_app = True
    app.setApplicationName("SCV Encoder")

    window = EncoderWindow()
    window.show()

    args = sys.argv[1:] if argv is None else list(argv)
    if args:
        window.add_paths(args)

    if owns_app:
        return app.exec()
    return 0


__all__ = ["EncoderWindow", "QueueWorker", "main"]
