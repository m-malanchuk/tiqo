"""Notifier port — implementations live at the edges (UI/desktop or fakes)."""

from __future__ import annotations

from typing import Protocol


class Notifier(Protocol):
    def notify_timer_finished(self, task_title: str, *, sound: str) -> None:
        """Announce countdown zero. ``sound`` is ``system`` or ``preset:<id>``."""


class NullNotifier:
    """No-op notifier (tests / headless)."""

    def notify_timer_finished(self, task_title: str, *, sound: str) -> None:
        return None


class RecordingNotifier:
    """Test double that records calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def notify_timer_finished(self, task_title: str, *, sound: str) -> None:
        self.calls.append((task_title, sound))
