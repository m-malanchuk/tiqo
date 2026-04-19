"""Countdown / overtime / one-shot notify."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import time_machine
from app.domain.formatting import format_session_clock
from app.domain.models import LIST_FAVORITES_ID, TimerMode
from app.services.notifier import RecordingNotifier
from app.services.timer_engine import TimerEngine
from app.storage.task_repo import TaskRepo
from app.storage.work_repo import WorkRepo
from app.ui.viewmodels.app_view_model import AppViewModel
from PySide6.QtCore import QCoreApplication

from tests.support.db import make_db

T0 = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def qapp() -> QCoreApplication:
    existing = QCoreApplication.instance()
    if existing is not None:
        return existing
    return QCoreApplication([])


def test_format_session_clock_overtime() -> None:
    assert format_session_clock(10, None) == "0:10"
    assert format_session_clock(65, 60) == "+0:05"


def test_poll_target_reached_once(conn) -> None:
    task = TaskRepo(conn).create(LIST_FAVORITES_ID, "Focus")
    engine = TimerEngine(conn)

    with time_machine.travel(T0, tick=False) as clock:
        engine.start(task.id, target_seconds=60, use_task_default=False)
        clock.shift(timedelta(seconds=59))
        assert engine.poll_target_reached() == []

        clock.shift(timedelta(seconds=1))
        first = engine.poll_target_reached()
        assert len(first) == 1
        assert first[0].task_id == task.id

        clock.shift(timedelta(seconds=30))
        assert engine.poll_target_reached() == []
        active = engine.open_session_for(task.id)
        assert active is not None
        assert engine.remaining_seconds(active) == -30


def test_one_minute_timer_notifies_once_and_stops(qapp: QCoreApplication) -> None:
    conn = make_db()
    task = TaskRepo(conn).create(
        LIST_FAVORITES_ID,
        "Pomodoro",
        default_mode=TimerMode.COUNTDOWN,
        default_target_seconds=60,
    )
    notifier = RecordingNotifier()
    vm = AppViewModel(conn, notifier=notifier)

    with time_machine.travel(T0, tick=False) as clock:
        vm.startTask(task.id)
        vm.confirmStart()
        clock.shift(timedelta(seconds=60))
        vm.tick()
        assert len(notifier.calls) == 1
        assert notifier.calls[0][0] == "Pomodoro"
        assert vm.engine.open_session_for(task.id) is None
        assert WorkRepo(conn).get(task.id) is None
        clock.shift(timedelta(seconds=12))
        vm.tick()
        assert len(notifier.calls) == 1


def test_countdown_always_stops_at_zero(qapp: QCoreApplication) -> None:
    conn = make_db()
    task = TaskRepo(conn).create(
        LIST_FAVORITES_ID, "Strict", default_mode=TimerMode.COUNTDOWN, default_target_seconds=60
    )
    notifier = RecordingNotifier()
    vm = AppViewModel(conn, notifier=notifier)

    with time_machine.travel(T0, tick=False) as clock:
        vm.startTask(task.id)
        vm.confirmStart()
        clock.shift(timedelta(seconds=60))
        vm.tick()
        assert len(notifier.calls) == 1
        assert vm.engine.open_session_for(task.id) is None
