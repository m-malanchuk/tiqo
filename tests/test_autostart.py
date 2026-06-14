"""User-level autostart entry management."""

from __future__ import annotations

from pathlib import Path

from app.services import autostart


def test_enable_copies_template_and_disable_removes_entry(monkeypatch, tmp_path: Path) -> None:
    destination = tmp_path / "config" / "autostart" / "tiqo.desktop"
    template = tmp_path / "tiqo-autostart.desktop"
    template.write_text("[Desktop Entry]\nExec=tiqo\n", encoding="utf-8")

    monkeypatch.setattr(autostart, "user_autostart_path", lambda: destination)
    monkeypatch.setattr(autostart, "template_path", lambda: template)

    assert autostart.is_enabled() is False
    assert autostart.set_enabled(True) is True
    assert destination.read_text(encoding="utf-8") == template.read_text(encoding="utf-8")

    assert autostart.set_enabled(False) is False
    assert not destination.exists()


def test_enable_requires_a_template(monkeypatch, tmp_path: Path) -> None:
    destination = tmp_path / "config" / "autostart" / "tiqo.desktop"
    missing = tmp_path / "missing.desktop"
    monkeypatch.setattr(autostart, "user_autostart_path", lambda: destination)
    monkeypatch.setattr(autostart, "template_path", lambda: missing)

    try:
        autostart.set_enabled(True)
    except FileNotFoundError as exc:
        assert str(missing) in str(exc)
    else:  # pragma: no cover - assertion keeps the expected failure explicit
        raise AssertionError("missing autostart template should fail")
