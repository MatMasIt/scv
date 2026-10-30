"""SCV Studio application entry point."""

from __future__ import annotations
import sys
from scv.ui.studio import StudioWindow, main

__all__ = ["StudioWindow", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
