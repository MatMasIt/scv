"""Configuration manager handling persistence and change notifications."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Callable

from .paths import get_config_file
from .settings import AppSettings


class ConfigManager:
    """Singleton manager for application settings persistence and notifications."""

    _instance: ConfigManager | None = None

    def __init__(self, config_path: Path | None = None) -> None:
        """Load settings from the configured path and initialize listeners."""
        self.config_path = config_path or get_config_file()
        self.settings = AppSettings()
        self._listeners: list[Callable[[AppSettings], None]] = []
        self.load()

    @classmethod
    def get_instance(cls) -> ConfigManager:
        """Return the process-wide configuration manager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_listener(self, callback: Callable[[AppSettings], None]) -> None:
        """Register a callback invoked whenever settings are saved."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[AppSettings], None]) -> None:
        """Unregister a settings-change callback."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def load(self) -> None:
        """Read settings from the JSON configuration file."""
        if self.config_path.is_file():
            try:
                content = self.config_path.read_text(encoding="utf-8")
                data = json.loads(content)
                self.settings = AppSettings.from_dict(data)
            except Exception:
                self.settings = AppSettings()
        else:
            self.settings = AppSettings()
            self.save()

        try:
            from scv.i18n import set_language
            set_language(self.settings.language)
        except Exception:
            pass

    def save(self) -> None:
        """Persist current settings to the JSON configuration file."""
        self.settings.validate()
        data = self.settings.to_dict()
        tmp_file = self.config_path.with_suffix(".tmp")
        try:
            tmp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp_file.replace(self.config_path)
        except Exception:
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)
            raise

        self._notify_listeners()
        try:
            from scv.i18n import set_language
            set_language(self.settings.language)
        except Exception:
            pass

    def update(self, **kwargs: object) -> None:
        """Update specific settings attributes and persist."""
        for key, value in kwargs.items():
            if not hasattr(self.settings, key):
                raise AttributeError(f"Unknown application setting: {key}")
            setattr(self.settings, key, value)
        self.save()

    def _notify_listeners(self) -> None:
        """Notify registered callbacks of the current settings."""
        for listener in list(self._listeners):
            try:
                listener(self.settings)
            except Exception:
                pass


def get_app_settings() -> AppSettings:
    """Convenience helper to retrieve active settings."""
    return ConfigManager.get_instance().settings
