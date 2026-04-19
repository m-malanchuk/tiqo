"""Discover timer sound presets under XDG data dirs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.storage.paths import system_sounds_dirs, user_sounds_dir

_EXTENSIONS = {".wav", ".ogg", ".oga", ".flac", ".mp3"}


@dataclass(frozen=True, slots=True)
class SoundPreset:
    """``id`` is the settings value suffix (``preset:<id>`` → stem)."""

    id: str
    label: str
    path: Path


def preset_setting_value(preset_id: str) -> str:
    return f"preset:{preset_id}"


def parse_preset_id(setting: str) -> str | None:
    if setting.startswith("preset:"):
        return setting.removeprefix("preset:")
    return None


def list_sound_presets() -> list[SoundPreset]:
    """User files override system files with the same stem."""
    found: dict[str, SoundPreset] = {}
    # System first, user overwrites.
    for directory in [*system_sounds_dirs(), user_sounds_dir()]:
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.suffix.lower() not in _EXTENSIONS:
                continue
            stem = path.stem
            found[stem] = SoundPreset(id=stem, label=stem, path=path)
    return sorted(found.values(), key=lambda p: p.label.lower())


def resolve_preset_path(setting: str) -> Path | None:
    preset_id = parse_preset_id(setting)
    if not preset_id:
        return None
    for preset in list_sound_presets():
        if preset.id == preset_id:
            return preset.path
    return None
