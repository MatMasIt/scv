"""Translation and internationalization manager."""

from __future__ import annotations
from typing import Callable
from .locales.en import CATALOG as EN_CATALOG
from .locales.it import CATALOG as IT_CATALOG
from .locales.fr import CATALOG as FR_CATALOG

CATALOGS: dict[str, dict[str, str]] = {
    "en": EN_CATALOG,
    "it": IT_CATALOG,
    "fr": FR_CATALOG,
}

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "it": "Italiano",
    "fr": "Français",
}


class I18nManager:
    """Manages active language catalog and text translation lookups."""

    _instance: I18nManager | None = None

    def __init__(self, default_lang: str = "en") -> None:
        """Select a valid initial language and initialize listeners."""
        self._current_lang = default_lang if default_lang in CATALOGS else "en"
        self._listeners: list[Callable[[str], None]] = []

    @classmethod
    def get_instance(cls) -> I18nManager:
        """Return the process-wide translation manager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_language(self) -> str:
        """Return the active language code."""
        return self._current_lang

    @property
    def available_languages(self) -> dict[str, str]:
        """Return the available language codes and display names."""
        return dict(LANGUAGE_NAMES)

    def set_language(self, lang: str) -> None:
        """Set the active language and notify listeners."""
        if lang in CATALOGS and lang != self._current_lang:
            self._current_lang = lang
            self._notify_listeners()

    def add_listener(self, callback: Callable[[str], None]) -> None:
        """Register a callback for language changes."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str], None]) -> None:
        """Unregister a language-change callback."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def translate(self, key: str, **kwargs: object) -> str:
        """Translate a string key into the active language with optional kwargs formatting."""
        catalog = CATALOGS.get(self._current_lang, EN_CATALOG)
        text = catalog.get(key)
        if text is None:
            # Fallback to English catalog
            text = EN_CATALOG.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def _notify_listeners(self) -> None:
        """Notify registered callbacks of the active language."""
        for listener in list(self._listeners):
            try:
                listener(self._current_lang)
            except Exception:
                pass


def t(key: str, **kwargs: object) -> str:
    """Translate string key into the active language."""
    return I18nManager.get_instance().translate(key, **kwargs)


def tr(key: str, **kwargs: object) -> str:
    """Alias for :func:`t`."""
    return t(key, **kwargs)


def set_language(lang: str) -> None:
    """Set the active language through the shared manager."""
    I18nManager.get_instance().set_language(lang)


def get_language() -> str:
    """Return the active language code."""
    return I18nManager.get_instance().current_language


def get_available_languages() -> dict[str, str]:
    """Return the available language codes and display names."""
    return I18nManager.get_instance().available_languages

