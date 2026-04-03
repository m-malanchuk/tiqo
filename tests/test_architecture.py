"""Executable checks for the dependency direction documented by the project."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / "app"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_dependency_layers_do_not_point_upward() -> None:
    forbidden = {
        "domain": ("app.storage", "app.services", "app.application", "app.ui", "PySide6"),
        "storage": ("app.services", "app.application", "app.ui", "PySide6"),
        "services": ("app.application", "app.ui", "PySide6"),
        "application": ("app.ui", "PySide6"),
    }
    violations: list[str] = []
    for layer, prefixes in forbidden.items():
        for path in (ROOT / layer).rglob("*.py"):
            for module in _imports(path):
                if module.startswith(prefixes):
                    violations.append(f"{path.relative_to(ROOT.parent)} imports {module}")
    assert violations == []
