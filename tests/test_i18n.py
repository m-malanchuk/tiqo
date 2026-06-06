"""Multi-locale catalog API."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.i18n import available_locales, get_locale, set_locale, tr

EXPECTED_CODES = {"en", "ru", "fr", "uk", "pl", "de"}


@pytest.fixture(autouse=True)
def _restore_default_locale() -> Iterator[None]:
    previous = get_locale()
    set_locale("ru")
    yield
    set_locale(previous)


def test_all_locale_codes_present() -> None:
    codes = {info.code for info in available_locales()}
    assert codes == EXPECTED_CODES


def test_locale_metadata_non_empty() -> None:
    for info in available_locales():
        assert info.native_name.strip()
        assert info.flag_emoji.strip()


def test_tr_changes_after_set_locale() -> None:
    set_locale("ru")
    ru = tr("list.favorites")
    set_locale("en")
    en = tr("list.favorites")
    assert ru == "Избранное"
    assert en == "Favorites"
    assert ru != en


def test_english_fallback_for_missing_key() -> None:
    set_locale("de")
    # Unknown msgid: falls back to msgid itself (no English entry either).
    assert tr("missing.completely") == "missing.completely"

    # Locale with a hole falls back to English when present there.
    from app.i18n.catalog import MESSAGES

    hole = "list.favorites"
    saved = MESSAGES["de"].pop(hole)
    try:
        set_locale("de")
        assert tr(hole) == MESSAGES["en"][hole]
    finally:
        MESSAGES["de"][hole] = saved


def test_default_locale_is_ru() -> None:
    assert get_locale() == "ru"
    assert tr("list.today") == "Сегодня"


def test_format_kwargs() -> None:
    set_locale("en")
    assert tr("status.created", title="Demo") == "Task created: Demo"
