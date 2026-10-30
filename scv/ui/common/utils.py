"""Shared formatting and asset resolution utilities for Qt applications."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QIcon


def fmt_time(ms: float | int) -> str:
    """Format a millisecond position as an hours/minutes/seconds string."""
    sec = max(0, int(ms / 1000))
    return f"{sec // 3600:02}:{(sec // 60) % 60:02}:{sec % 60:02}"


def get_asset_path(filename: str) -> Path | None:
    """Resolve an asset file path from package directories or parent roots."""
    candidates = [
        Path(__file__).resolve().parents[2] / "assets" / filename,
        Path(__file__).resolve().parents[3] / "assets" / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_app_icon() -> QIcon | None:
    """Load the default application icon if available."""
    try:
        from PySide6.QtGui import QIcon
    except ImportError:
        return None
    icon_path = get_asset_path("scv.svg")
    if icon_path and icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()
