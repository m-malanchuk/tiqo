"""Manage tiqo's opt-in freedesktop autostart entry."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.storage.paths import user_autostart_path

_PACKAGED_TEMPLATE = Path("/usr/share/tiqo/tiqo-autostart.desktop")


def template_path() -> Path:
    """Return the installed template, or the repository template in dev mode."""
    if _PACKAGED_TEMPLATE.is_file():
        return _PACKAGED_TEMPLATE

    # ``app/services/autostart.py`` lives two levels below the repository root.
    source_template = Path(__file__).resolve().parents[2] / "packaging" / "tiqo-autostart.desktop"
    if source_template.is_file():
        return source_template
    return _PACKAGED_TEMPLATE


def is_enabled() -> bool:
    """Whether the user has an autostart entry for tiqo."""
    return user_autostart_path().is_file()


def set_enabled(enabled: bool) -> bool:
    """Enable or disable autostart and return the resulting state.

    Enabling copies the packaged desktop-entry template into the user's
    autostart directory. Disabling removes only that user-owned entry.
    """
    destination = user_autostart_path()
    if enabled:
        source = template_path()
        if not source.is_file():
            raise FileNotFoundError(f"Autostart template not found: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    elif destination.exists() or destination.is_symlink():
        destination.unlink()
    return is_enabled()
