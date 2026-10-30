"""Shared UI utilities and dialogs.

Qt-heavy modules are imported lazily so headless utilities remain usable by
the CLI and test suite without requiring a running desktop environment.
"""

from typing import Any

from .utils import fmt_time, get_asset_path, load_app_icon

__all__ = [
    "fmt_time",
    "get_asset_path",
    "load_app_icon",
    "show_about",
    "SettingsDialog",
]


def __getattr__(name: str) -> Any:
    if name == "show_about":
        from .about import show_about

        return show_about
    if name == "SettingsDialog":
        from .settings_dialog import SettingsDialog

        return SettingsDialog
    raise AttributeError(name)
