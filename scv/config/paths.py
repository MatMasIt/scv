"""Cross-platform configuration and data paths."""

from __future__ import annotations
import os
from pathlib import Path
import sys


def get_config_dir() -> Path:
    """Return the cross-platform application configuration directory."""
    try:
        import platformdirs
        base = Path(platformdirs.user_config_dir("scvstudio"))
    except Exception:
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            base = Path(appdata) / "scvstudio" if appdata else Path.home() / ".scvstudio"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "scvstudio"
        else:
            xdg = os.environ.get("XDG_CONFIG_HOME")
            base = Path(xdg) / "scvstudio" if xdg else Path.home() / ".config" / "scvstudio"

    base.mkdir(parents=True, exist_ok=True)
    return base


def get_config_file() -> Path:
    """Return the primary configuration JSON file path."""
    return get_config_dir() / "config.json"

