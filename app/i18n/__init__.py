"""Multi-locale message catalog for UI strings."""

from __future__ import annotations

from app.i18n.catalog import (
    DEFAULT_LOCALE,
    FALLBACK_LOCALE,
    LOCALES,
    MESSAGES,
    LocaleInfo,
)

__all__ = [
    "LocaleInfo",
    "available_locales",
    "get_locale",
    "list_title",
    "set_locale",
    "tr",
]

_locale: str = DEFAULT_LOCALE
_locale_codes = frozenset(info.code for info in LOCALES)


def available_locales() -> list[LocaleInfo]:
    return list(LOCALES)


def get_locale() -> str:
    return _locale


def set_locale(code: str) -> None:
    global _locale
    if code not in _locale_codes:
        raise ValueError(f"unsupported locale: {code}")
    _locale = code


def tr(msgid: str, **kwargs: object) -> str:
    catalog = MESSAGES.get(_locale, {})
    text = catalog.get(msgid)
    if text is None and _locale != FALLBACK_LOCALE:
        text = MESSAGES.get(FALLBACK_LOCALE, {}).get(msgid)
    if text is None:
        text = msgid
    if kwargs:
        return text.format(**kwargs)
    return text


def list_title(key: str | None, fallback_name: str) -> str:
    """Localize system lists (all/favorites/today/in_work).

    User-created groups have ``key is None`` — their ``name`` is shown as stored
    (any language), independent of the UI locale.
    """
    if key:
        return tr(f"list.{key}")
    return fallback_name
