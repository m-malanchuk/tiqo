"""Static checks for the Arch package's install contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGING = ROOT / "packaging"


def test_arch_package_installs_application_and_widget_together() -> None:
    pkbuild = (PACKAGING / "PKGBUILD").read_text(encoding="utf-8")
    assert "python-hatchling" in pkbuild
    assert "python-installer" in pkbuild
    assert "pyside6" in pkbuild
    assert "/usr/share/plasma/plasmoids/org.tiqo.work" in pkbuild
    assert "/usr/share/applications/tiqo.desktop" in pkbuild
    assert "/usr/share/tiqo/tiqo-autostart.desktop" in pkbuild
    assert "/etc/xdg/autostart/tiqo.desktop" not in pkbuild
    assert "/usr/share/icons/hicolor/scalable/apps/tiqo.svg" in pkbuild


def test_desktop_entries_target_tiqo() -> None:
    desktop = (PACKAGING / "tiqo.desktop").read_text(encoding="utf-8")
    autostart = (PACKAGING / "tiqo-autostart.desktop").read_text(encoding="utf-8")
    assert "Exec=tiqo\n" in desktop
    assert "Icon=tiqo\n" in desktop
    assert "Exec=tiqo\n" in autostart
    assert "OnlyShowIn=KDE;" in autostart
