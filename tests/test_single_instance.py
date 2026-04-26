"""Single-instance helper smoke test (no GUI event loop needed beyond QCore)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.ui.single_instance import SingleInstance
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication


def test_primary_instance_listens(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QCoreApplication)
    server_name = str(tmp_path / f"tiqo-test-{uuid4().hex}.sock")
    first = SingleInstance(server_name=server_name)
    if not first.ensure_primary():
        pytest.skip(f"local sockets unavailable in this environment: {first.last_error}")
    second = SingleInstance(server_name=server_name)
    assert second.ensure_primary() is False
