"""Shipped tiqo icons resolve and load into QIcon from SVG."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from app.ui.app_icons import (
    ROLE_APP,
    ROLE_TRAY_DARK,
    ROLE_TRAY_LIGHT,
    app_icon,
    app_icon_url,
    clear_icon_cache,
    ensure_desktop_app_icon,
    icon_for_role,
    icons_root,
    is_dark_color_scheme,
    svg_path_for_role,
    tray_icon,
)
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        assert isinstance(existing, QApplication)
        return existing
    return QApplication([])


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    clear_icon_cache()
    yield
    clear_icon_cache()


def test_source_svgs_exist_and_png_trees_gone() -> None:
    root = icons_root()
    assert (root / "README.md").is_file()
    for role in (ROLE_APP, ROLE_TRAY_DARK, ROLE_TRAY_LIGHT):
        svg = svg_path_for_role(role)
        assert svg.is_file(), role
        assert svg.read_text(encoding="utf-8").lstrip().startswith("<")
        png_dir = root / role
        assert not png_dir.exists(), f"PNG tree should be removed: {png_dir}"


def test_qicons_not_null(qapp: QApplication) -> None:
    _ = qapp
    assert not app_icon().isNull()
    assert not icon_for_role(ROLE_APP).isNull()
    assert not icon_for_role(ROLE_TRAY_DARK).isNull()
    assert not icon_for_role(ROLE_TRAY_LIGHT).isNull()
    assert not tray_icon(dark=True).isNull()
    assert not tray_icon(dark=False).isNull()
    assert not tray_icon(variant="color").isNull()
    assert isinstance(is_dark_color_scheme(), bool)


def test_app_icon_url_and_desktop_install(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = qapp
    url = app_icon_url()
    assert url.startswith("file:")
    assert url.endswith("app.svg")

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr("app.ui.app_icons.Path.home", lambda: fake_home)

    installed = ensure_desktop_app_icon()
    assert installed is not None
    assert installed.is_file()
    assert installed.read_bytes() == svg_path_for_role(ROLE_APP).read_bytes()
    desktop = fake_home / ".local/share/applications/tiqo.desktop"
    assert desktop.is_file()
    assert "Icon=tiqo" in desktop.read_text(encoding="utf-8")
    # Sized PNGs for Plasma task manager (not scalable-only).
    png48 = fake_home / ".local/share/icons/hicolor/48x48/apps/tiqo.png"
    assert png48.is_file() and png48.stat().st_size > 0
    # Must not plant a broken local hicolor index.theme.
    assert not (fake_home / ".local/share/icons/hicolor/index.theme").is_file()
