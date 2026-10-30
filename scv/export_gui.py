"""SCV Exporter GUI facade maintaining full backward compatibility.

The exporter GUI implementation has been modularized under :mod:`scv.ui.exporter`.
"""

from __future__ import annotations
import sys
from scv.ui.exporter import ExportWindow, ExportWorker, main

__all__ = ["ExportWindow", "ExportWorker", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
