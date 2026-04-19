"""Sound preset discovery under XDG paths."""

from __future__ import annotations

from pathlib import Path

from app.services.sound_presets import list_sound_presets, preset_setting_value, resolve_preset_path


def test_user_preset_overrides_system(tmp_path: Path, monkeypatch) -> None:
    system = tmp_path / "usr" / "share" / "tiqo" / "sounds"
    user = tmp_path / "home" / ".local" / "share" / "tiqo" / "sounds"
    system.mkdir(parents=True)
    user.mkdir(parents=True)
    (system / "ping.ogg").write_bytes(b"sys")
    (user / "ping.ogg").write_bytes(b"user")
    (user / "chime.wav").write_bytes(b"wav")
    (user / "bell.mp3").write_bytes(b"mp3")

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "home" / ".local" / "share"))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "usr" / "share"))

    presets = {p.id: p for p in list_sound_presets()}
    assert set(presets) >= {"ping", "chime", "bell"}
    assert presets["ping"].path.read_bytes() == b"user"
    assert resolve_preset_path(preset_setting_value("chime")) == presets["chime"].path
