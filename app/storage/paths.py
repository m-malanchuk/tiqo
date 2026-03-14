"""XDG paths for tiqo data."""

from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    root = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return root / "tiqo"


def default_db_path() -> Path:
    return data_dir() / "tiqo.db"


def default_history_export_path() -> Path:
    """Fixed user-facing export name requested by the completed-history UI."""
    return Path.home() / "tiqo-export.csv"


def user_sounds_dir() -> Path:
    """``~/.local/share/tiqo/sounds`` — drop wav/ogg presets here."""
    return data_dir() / "sounds"


def user_autostart_path() -> Path:
    """User-level desktop entry controlling whether tiqo starts at login.

    Autostart entries are deliberately kept outside tiqo's application config
    directory: the desktop environment discovers them in the freedesktop
    ``$XDG_CONFIG_HOME/autostart`` directory.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    root = Path(xdg) if xdg else Path.home() / ".config"
    return root / "autostart" / "tiqo.desktop"


def system_sounds_dirs() -> list[Path]:
    """Packaged presets, e.g. ``/usr/share/tiqo/sounds``."""
    dirs: list[Path] = []
    xdg_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    for raw in xdg_dirs.split(":"):
        raw = raw.strip()
        if not raw:
            continue
        path = Path(raw) / "tiqo" / "sounds"
        if path not in dirs:
            dirs.append(path)
    return dirs
