"""Load tiqo icons from SVG masters under ``app/assets/icons/source``.

Roles map 1:1 to files:

- ``app`` → ``source/app.svg`` (colour mark / window / «Цветная»)
- ``tray-dark`` → ``source/tray-dark.svg``
- ``tray-light`` → ``source/tray-light.svg``

Swap art by editing those SVGs — see ``app/assets/icons/README.md``.

On KDE/Wayland the task-manager / title-bar mark is resolved via the icon
theme name ``tiqo`` (``setDesktopFileName``). ``ensure_desktop_app_icon``
installs **PNG sizes** (and the colour SVG) into user hicolor — scalable-only
was showing up blank / glitchy in Plasma.
"""

from __future__ import annotations

import contextlib
import logging
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QUrl
from PySide6.QtGui import (
    QGuiApplication,
    QIcon,
    QImage,
    QPainter,
    QPalette,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer

log = logging.getLogger(__name__)

# Folder / settings role names — stable API.
ROLE_APP = "app"
ROLE_TRAY_DARK = "tray-dark"
ROLE_TRAY_LIGHT = "tray-light"

_ROLE_SVG = {
    ROLE_APP: "app.svg",
    ROLE_TRAY_DARK: "tray-dark.svg",
    ROLE_TRAY_LIGHT: "tray-light.svg",
}

# Common tray / window / HiDPI / hicolor sizes.
_SVG_SIZES = (16, 22, 24, 32, 48, 64, 128, 256)

# Freedesktop icon name matching ``setDesktopFileName("tiqo")`` / ``Icon=tiqo``.
DESKTOP_ICON_NAME = "tiqo"


def icons_root() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "icons"


def role_dir(role: str) -> Path:
    """Legacy helper: role folder path (PNG era). Prefer ``svg_path_for_role``."""
    return icons_root() / role


def svg_path_for_role(role: str) -> Path:
    name = _ROLE_SVG.get(role)
    if name is None:
        raise KeyError(f"unknown icon role: {role!r}")
    return icons_root() / "source" / name


def app_icon_url() -> str:
    """``file:`` URL for the colour SVG."""
    return QUrl.fromLocalFile(str(svg_path_for_role(ROLE_APP).resolve())).toString()


def _render_svg(path: Path, size: int) -> QPixmap:
    """Rasterise SVG to a premultiplied pixmap (avoids green fringe in compositors)."""
    renderer = QSvgRenderer(str(path))
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    if not renderer.isValid():
        return QPixmap.fromImage(image)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return QPixmap.fromImage(image)


def _icon_from_svg(path: Path) -> QIcon:
    icon = QIcon()
    if not path.is_file():
        return icon
    # Prefer explicit pixmaps for Plasma / Wayland window decorations.
    for size in _SVG_SIZES:
        icon.addPixmap(_render_svg(path, size))
    # Also register the SVG itself as a scalable file for Qt.
    icon.addFile(str(path))
    return icon


@lru_cache(maxsize=8)
def icon_for_role(role: str) -> QIcon:
    """Build a multi-resolution ``QIcon`` from ``icons/source/{role}.svg``."""
    return _icon_from_svg(svg_path_for_role(role))


def clear_icon_cache() -> None:
    """Drop cached icons (tests / after hot-replacing files in-process)."""
    icon_for_role.cache_clear()


def app_icon() -> QIcon:
    """Colour mark for the window / task switcher."""
    return icon_for_role(ROLE_APP)


def _hicolor_root() -> Path:
    return Path.home() / ".local" / "share" / "icons" / "hicolor"


def ensure_desktop_app_icon() -> Path | None:
    """Install colour mark into user hicolor (PNG sizes + SVG) and a ``.desktop``.

    Do **not** write a local ``hicolor/index.theme`` — that replaces the system
    theme directory list and made the task-manager icon go blank.

    Returns the installed scalable SVG path, or ``None`` if source is missing.
    """
    src = svg_path_for_role(ROLE_APP)
    if not src.is_file():
        log.warning("app icon SVG missing: %s", src)
        return None

    hicolor = _hicolor_root()
    scalable = hicolor / "scalable" / "apps" / f"{DESKTOP_ICON_NAME}.svg"
    desktop = Path.home() / ".local" / "share" / "applications" / f"{DESKTOP_ICON_NAME}.desktop"

    try:
        # Drop a previously-written broken local index (scalable-only).
        bad_index = hicolor / "index.theme"
        if bad_index.is_file():
            text = bad_index.read_text(encoding="utf-8", errors="replace")
            if "Directories=scalable/apps" in text and "16x16/apps" not in text:
                bad_index.unlink(missing_ok=True)
                (hicolor / "icon-theme.cache").unlink(missing_ok=True)

        scalable.parent.mkdir(parents=True, exist_ok=True)
        if not scalable.is_file() or scalable.read_bytes() != src.read_bytes():
            shutil.copy2(src, scalable)

        # Plasma task manager prefers sized PNGs over buggy SVG loaders.
        for size in _SVG_SIZES:
            png_dir = hicolor / f"{size}x{size}" / "apps"
            png_dir.mkdir(parents=True, exist_ok=True)
            png_path = png_dir / f"{DESKTOP_ICON_NAME}.png"
            pix = _render_svg(src, size)
            # Always rewrite so SVG edits show up without manual cache nuking.
            pix.save(str(png_path), "PNG")

        desktop.parent.mkdir(parents=True, exist_ok=True)
        body = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=tiqo\n"
            f"Icon={DESKTOP_ICON_NAME}\n"
            "Exec=tiqo\n"
            "Terminal=false\n"
            "Categories=Utility;Office;\n"
            "StartupWMClass=tiqo\n"
        )
        if not desktop.is_file() or "Icon=tiqo" not in desktop.read_text(encoding="utf-8"):
            desktop.write_text(body, encoding="utf-8")

        clear_icon_cache()
        QIcon.setThemeSearchPaths(QIcon.themeSearchPaths())
        # Best-effort cache refresh for GTK/KDE icon loaders.
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            subprocess.run(
                ["gtk-update-icon-cache", "-f", "-t", str(hicolor)],
                check=False,
                capture_output=True,
                timeout=10,
            )
        return scalable
    except OSError as exc:
        log.warning("could not install desktop app icon: %s", exc)
        return None


def is_dark_color_scheme() -> bool:
    app = QGuiApplication.instance()
    if not isinstance(app, QGuiApplication):
        return True
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return True
    if scheme == Qt.ColorScheme.Light:
        return False
    color = app.palette().color(QPalette.ColorRole.Window)
    return color.lightness() < 128


def tray_icon(*, dark: bool | None = None, variant: str | None = None) -> QIcon:
    """Tray glyph for the current (or forced) colour scheme / settings variant.

    ``variant``: ``auto`` | ``tray-dark`` | ``tray-light`` | ``color``.
    ``dark`` is used only when ``variant`` is ``auto`` or omitted.
    """
    if variant in (ROLE_TRAY_DARK, ROLE_TRAY_LIGHT, ROLE_APP, "color"):
        role = ROLE_APP if variant == "color" else variant
        return icon_for_role(role)
    use_dark = is_dark_color_scheme() if dark is None else dark
    return icon_for_role(ROLE_TRAY_DARK if use_dark else ROLE_TRAY_LIGHT)
