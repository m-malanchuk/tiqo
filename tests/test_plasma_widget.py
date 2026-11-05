"""Static contracts for the Plasma widget presentation layer."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
WIDGET_UI = ROOT / "plasma" / "org.tiqo.work" / "contents" / "ui"


def test_checklist_completion_is_rendered_as_repeatable_action() -> None:
    main_qml = (WIDGET_UI / "main.qml").read_text(encoding="utf-8")
    delegate_qml = (WIDGET_UI / "WorkItemDelegate.qml").read_text(encoding="utf-8")

    assert 'const checklistAction = kind === "checklist";' in main_qml
    assert re.search(r"progress:\s*checklistAction\s*\?\s*0", main_qml)
    assert "is_completed: checklistAction ? false" in main_qml
    assert 'text: "☐"' in delegate_qml
