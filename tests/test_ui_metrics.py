"""UiMetrics runtime setters."""

from __future__ import annotations

from app.ui.viewmodels.ui_metrics import UiMetrics
from PySide6.QtCore import QCoreApplication


def test_control_height_updates() -> None:
    if QCoreApplication.instance() is None:
        QCoreApplication([])
    metrics = UiMetrics()
    assert metrics.controlHeight == 36
    metrics.setControlHeight(44)
    assert metrics.controlHeight == 44
    metrics.setPadMd(16)
    assert metrics.padMd == 16
