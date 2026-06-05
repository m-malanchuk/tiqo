"""Settings bridge persistence and locale switch."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.i18n import get_locale, tr
from app.services import autostart
from app.services import settings_keys as keys
from app.storage.db import open_memory_database
from app.storage.settings_repo import SettingsRepo
from app.ui.viewmodels.settings_bridge import SettingsBridge
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    # Another test may have created a bare QCoreApplication — reuse if possible.
    if existing is not None:
        return existing  # type: ignore[return-value]
    return QApplication([])


def test_settings_defaults_and_language(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _ = qapp
    monkeypatch.setattr(
        autostart,
        "user_autostart_path",
        lambda: tmp_path / "config" / "autostart" / "tiqo.desktop",
    )
    from app.i18n import set_locale

    conn = open_memory_database()
    bridge = SettingsBridge(SettingsRepo(conn))
    assert bridge.closeToTray is True
    assert bridge.fontSize == keys.FONT_MEDIUM
    bridge.setLanguage("en")
    assert get_locale() == "en"
    assert tr("tray.settings") == "Settings"
    bridge.setCloseBehavior(keys.CLOSE_QUIT)
    assert bridge.closeToTray is False
    set_locale(keys.LANG_DEFAULT)


def test_autostart_setting_manages_user_entry(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _ = qapp
    destination = tmp_path / "config" / "autostart" / "tiqo.desktop"
    template = tmp_path / "tiqo-autostart.desktop"
    template.write_text("[Desktop Entry]\nExec=tiqo\n", encoding="utf-8")
    monkeypatch.setattr(autostart, "user_autostart_path", lambda: destination)
    monkeypatch.setattr(autostart, "template_path", lambda: template)

    bridge = SettingsBridge(SettingsRepo(open_memory_database()))
    assert bridge.autostart is False

    bridge.setAutostart(True)
    assert bridge.autostart is True
    assert destination.read_text(encoding="utf-8") == template.read_text(encoding="utf-8")

    bridge.setAutostart(False)
    assert bridge.autostart is False
    assert not destination.exists()
