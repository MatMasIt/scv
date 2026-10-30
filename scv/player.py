"""SCV Player facade maintaining full backward compatibility.

The player implementation has been modularized under :mod:`scv.ui.player`.
"""

from __future__ import annotations
import sys

from scv.ui.common.utils import fmt_time
from scv.ui.widgets import ZoomableViewer, TimelineSlider
from scv.ui.player import PlayerWindow, main

__all__ = ["fmt_time", "ZoomableViewer", "TimelineSlider", "PlayerWindow", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
