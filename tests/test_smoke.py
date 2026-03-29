"""Stage 0 smoke tests — project imports without Qt side effects."""

from __future__ import annotations


def test_app_package_imports() -> None:
    import app
    import app.domain
    import app.services
    import app.storage

    assert app.__name__ == "app"


def test_qml_main_exists() -> None:
    from pathlib import Path

    qml = Path(__file__).resolve().parents[1] / "app" / "ui" / "qml" / "Main.qml"
    assert qml.is_file()
    text = qml.read_text(encoding="utf-8")
    assert 't("app.name")' in text or "tiqo" in text
