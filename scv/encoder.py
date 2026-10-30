"""Batch encoder facade maintaining full backward compatibility.

The encoder implementation has been modularized under :mod:`scv.ui.encoder`.
"""

from __future__ import annotations
import sys
from scv.ui.encoder import EncoderWindow, QueueWorker, main

__all__ = ["EncoderWindow", "QueueWorker", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
