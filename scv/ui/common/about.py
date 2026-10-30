"""Centralized credits and license notices."""

from PySide6.QtWidgets import QMessageBox, QWidget
from scv.core import VERSION

ABOUT = """SCV Suite {version} - Slide Compressed Video
Copyright © 2026 Mattia Mascarello
SCV source code and original icon: MIT License (see LICENSE).

Third-party software - independently licensed:
• FFmpeg / FFprobe: LGPL-2.1-or-later by default, but GPL-2.0-or-later for builds with GPL options. Check YOUR bundled build's configuration and notices. https://ffmpeg.org/legal.html
• PySide6 / Qt for Python / Qt: LGPL-3.0-only, GPL licenses or commercial terms depending on components and distribution. https://www.qt.io/licensing
• Pillow: HPND license. https://python-pillow.github.io/
• NumPy: BSD-3-Clause. https://numpy.org/
• Opus: BSD-style license (codec implementation/library where bundled). https://opus-codec.org/
• PyInstaller: GPL-2.0-or-later with bootloader exception (build tool). https://pyinstaller.org/

Redistribution requires including relevant copyright notices and license texts for the exact versions and binaries shipped. SCV's MIT license does not relicense dependencies.
"""


def show_about(parent: QWidget, product: str = "Suite") -> None:
    """Display the license and third-party notices for an application."""
    QMessageBox.about(parent, f"About SCV {product}", ABOUT.format(version=VERSION))
