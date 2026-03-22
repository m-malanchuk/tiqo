"""Stopwatch and countdown sessions must sum into task totals correctly."""

from __future__ import annotations

import os
import time
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import time_machine
from app.domain.models import LIST_FAVORITES_ID, TimerMode
from app.domain.timeutil import seconds_by_local_day
from app.services.timer_engine import TimerEngine
from app.storage.session_repo import SessionRepo
from app.storage.stats_repo import StatsRepo
from app.storage.task_repo import TaskRepo

from tests.support.db import make_db

T0 = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def test_stopwatch_and_countdown_sessions_sum() -> None:
    """Mixed mode sessions on one task accumulate wall-clock seconds."""
    conn = make_db()
    tasks = TaskRepo(conn)
    engine = TimerEngine(conn)
    stats = StatsRepo(conn)

    task = tasks.create(
        LIST_FAVORITES_ID,
        "Study",
        default_mode=TimerMode.STOPWATCH,
    )

    with time_machine.travel(T0, tick=False) as clock:
        # Stopwatch session: 90s
        engine.start(task.id, target_seconds=None, use_task_default=False)
        clock.shift(timedelta(seconds=90))
        engine.pause(task.id)

        # Countdown session (25 min target): run 120s then stop
        engine.start(task.id, target_seconds=25 * 60, use_task_default=False)
        clock.shift(timedelta(seconds=120))
        engine.stop(task.id)

        # Another stopwatch: 45s
        engine.start(task.id, target_seconds=None, use_task_default=False)
        clock.shift(timedelta(seconds=45))
        engine.stop(task.id)

    total = 90 + 120 + 45
    assert engine.task_elapsed_seconds(task.id) == total
    assert engine.task_elapsed_today(task.id, now=T0 + timedelta(seconds=total)) == total

    day = T0.date()
    stat = stats.get(task.id, day)
    assert stat is not None
    assert stat.total_seconds == total
    assert stat.sessions_count == 2

    stats.rebuild_from_sessions()
    rebuilt = stats.get(task.id, day)
    assert rebuilt is not None
    assert rebuilt.total_seconds == total
    assert rebuilt.sessions_count == 2


def test_countdown_overtime_still_counts() -> None:
    """Time after target (overtime) is still tracked in the same session."""
    conn = make_db()
    task = TaskRepo(conn).create(LIST_FAVORITES_ID, "Pomodoro")
    engine = TimerEngine(conn)

    with time_machine.travel(T0, tick=False) as clock:
        engine.start(task.id, target_seconds=60, use_task_default=False)
        clock.shift(timedelta(seconds=60))
        events = engine.poll_target_reached()
        assert len(events) == 1
        clock.shift(timedelta(seconds=25))  # overtime
        engine.stop(task.id)

    assert engine.task_elapsed_seconds(task.id) == 85


def test_open_session_counts_in_live_total() -> None:
    """Running session contributes to task_elapsed_seconds before close."""
    conn = make_db()
    task = TaskRepo(conn).create(LIST_FAVORITES_ID, "Live")
    engine = TimerEngine(conn)

    with time_machine.travel(T0, tick=False) as clock:
        engine.start(task.id, target_seconds=None, use_task_default=False)
        clock.shift(timedelta(seconds=40))
        assert engine.task_elapsed_seconds(task.id) == 40
        engine.pause(task.id)
        clock.shift(timedelta(seconds=100))  # paused — must not add
        assert engine.task_elapsed_seconds(task.id) == 40
        engine.resume(task.id)
        clock.shift(timedelta(seconds=15))
        assert engine.task_elapsed_seconds(task.id) == 55
        engine.stop(task.id)

    assert engine.task_elapsed_seconds(task.id) == 55
    assert SessionRepo(conn).count_for_task(task.id) == 1


def test_rollup_includes_child_stopwatch_and_timer() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    engine = TimerEngine(conn)

    parent = tasks.create(LIST_FAVORITES_ID, "English")
    child = tasks.create(LIST_FAVORITES_ID, "Grammar", parent_task_id=parent.id)

    with time_machine.travel(T0, tick=False) as clock:
        engine.start(parent.id, target_seconds=None, use_task_default=False)
        clock.shift(timedelta(seconds=60))
        engine.stop(parent.id)

        engine.start(child.id, target_seconds=600, use_task_default=False)
        clock.shift(timedelta(seconds=30))
        engine.stop(child.id)

    assert engine.task_elapsed_seconds(parent.id) == 60
    assert engine.task_elapsed_seconds(child.id) == 30
    assert engine.task_rollup_seconds(parent.id) == 90


def test_sibling_tasks_accumulate_independently() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    engine = TimerEngine(conn)
    a = tasks.create(LIST_FAVORITES_ID, "A")
    b = tasks.create(LIST_FAVORITES_ID, "B")

    with time_machine.travel(T0, tick=False) as clock:
        engine.start(a.id, target_seconds=None, use_task_default=False)
        engine.start(b.id, target_seconds=120, use_task_default=False)
        clock.shift(timedelta(seconds=20))
        engine.stop(a.id)
        clock.shift(timedelta(seconds=10))
        engine.stop(b.id)

    assert engine.task_elapsed_seconds(a.id) == 20
    assert engine.task_elapsed_seconds(b.id) == 30


def test_interval_is_split_at_local_midnight() -> None:
    kyiv = ZoneInfo("Europe/Kyiv")
    started = datetime(2024, 6, 15, 23, 55, tzinfo=kyiv)
    ended = datetime(2024, 6, 16, 0, 10, tzinfo=kyiv)

    assert seconds_by_local_day(started, ended, timezone=kyiv) == {
        date(2024, 6, 15): 5 * 60,
        date(2024, 6, 16): 10 * 60,
    }


def test_day_split_handles_dst_transition() -> None:
    kyiv = ZoneInfo("Europe/Kyiv")
    started = datetime(2024, 10, 27, 0, 0, tzinfo=kyiv)
    ended = datetime(2024, 10, 28, 0, 0, tzinfo=kyiv)

    assert seconds_by_local_day(started, ended, timezone=kyiv) == {
        date(2024, 10, 27): 25 * 60 * 60,
    }


def test_incremental_and_rebuilt_stats_split_midnight() -> None:
    previous_tz = os.environ.get("TZ")
    os.environ["TZ"] = "Europe/Kyiv"
    time.tzset()
    try:
        conn = make_db()
        task = TaskRepo(conn).create(LIST_FAVORITES_ID, "Night work")
        engine = TimerEngine(conn)
        kyiv = ZoneInfo("Europe/Kyiv")
        started = datetime(2024, 6, 15, 23, 55, tzinfo=kyiv)
        ended = datetime(2024, 6, 16, 0, 10, tzinfo=kyiv)

        engine.start(task.id, now=started)
        engine.stop(task.id, now=ended)

        stats = StatsRepo(conn)
        first = stats.get(task.id, date(2024, 6, 15))
        second = stats.get(task.id, date(2024, 6, 16))
        assert first is not None and first.total_seconds == 5 * 60
        assert second is not None and second.total_seconds == 10 * 60
        assert engine.task_elapsed_today(task.id, now=ended, today=second.date) == 10 * 60

        stats.rebuild_from_sessions()
        assert stats.get(task.id, first.date) == first
        assert stats.get(task.id, second.date) == second
    finally:
        if previous_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous_tz
        time.tzset()
