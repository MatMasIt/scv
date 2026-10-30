"""Internationalization (i18n) package for SCV Studio."""

from .manager import (
    I18nManager,
    t,
    tr,
    set_language,
    get_language,
    get_available_languages,
    LANGUAGE_NAMES,
)

__all__ = [
    "I18nManager",
    "t",
    "tr",
    "set_language",
    "get_language",
    "get_available_languages",
    "LANGUAGE_NAMES",
]

