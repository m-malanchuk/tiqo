"""TimerEngine scenarios — multi-session + hierarchy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import time_machine
from app.domain.models import LIST_FAVORITES_ID, CompletionKind, EndReason, Task, WorkState
from app.services.timer_engine import HierarchyConflictError, TimerEngine
from app.storage.completion_repo import CompletionRepo
from app.storage.stats_repo import StatsRepo
from app.storage.task_repo import TaskRepo
from app.storage.work_repo import WorkRepo

T0 = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


class FailingWorkRepo(WorkRepo):
    def upsert(self, *args, **kwargs):
        raise RuntimeError("simulated work roster failure")


def test_start_pause_resume(engine: TimerEngine, task: Task, conn) -> None:
    with time_machine.travel(T0, tick=False) as clock:
        session = engine.start(task.id)
        assert session.is_open

        clock.shift(timedelta(seconds=30))
        paused = engine.pause(task.id)
        assert paused.end_reason is None
        assert paused.id == session.id
        assert engine.open_session_for(task.id) is None
        assert engine.session_for_task(task.id) is not None
        work = WorkRepo(conn).get(task.id)
        assert work is not None
        assert work.state is WorkState.PAUSED

        clock.shift(timedelta(seconds=10))
        resumed = engine.resume(task.id)
        assert resumed.is_open
        assert resumed.id == paused.id

        clock.shift(timedelta(seconds=20))
        assert engine.task_elapsed_seconds(task.id) == 50


def test_completed_session_is_recorded_without_copying_session(conn, task: Task) -> None:
    engine = TimerEngine(conn)

    with time_machine.travel(T0, tick=False) as clock:
        engine.start(task.id)
        clock.shift(timedelta(seconds=30))
        closed = engine.stop(task.id)

    assert closed is not None
    completions = CompletionRepo(conn).list_for_task(task.id)
    assert len(completions) == 1
    assert completions[0].kind is CompletionKind.MANUAL_STOP
    assert completions[0].session_id == closed.id


def test_pause_and_crash_recovery_do_not_record_completion(conn, task: Task) -> None:
    engine = TimerEngine(conn)

    with time_machine.travel(T0, tick=False) as clock:
        engine.start(task.id)
        clock.shift(timedelta(seconds=10))
        engine.pause(task.id)
        engine.resume(task.id)
        clock.shift(timedelta(seconds=10))
        engine.heartbeat()
        TimerEngine(conn).recover_crash()

    assert CompletionRepo(conn).list_for_task(task.id) == []


def test_target_reached_uses_distinct_completion_kind(conn, task: Task) -> None:
    engine = TimerEngine(conn)

    with time_machine.travel(T0, tick=False) as clock:
        session = engine.start(task.id, target_seconds=60, use_task_default=False)
        clock.shift(timedelta(seconds=60))
        events = engine.poll_target_reached()
        assert [event.session_id for event in events] == [session.id]
        engine.stop(task.id, completion_kind=CompletionKind.TARGET_REACHED)

    completion = CompletionRepo(conn).list_for_task(task.id)[0]
    assert completion.kind is CompletionKind.TARGET_REACHED


def test_checklist_completion_can_exist_without_a_session(conn, task: Task) -> None:
    completion = CompletionRepo(conn).create(
        task.id,
        session_id=None,
        completed_at=T0,
        kind=CompletionKind.CHECKLIST,
    )

    assert completion.session_id is None
    assert completion.kind is CompletionKind.CHECKLIST


def test_start_rolls_back_session_when_work_update_fails(conn, task: Task) -> None:
    engine = TimerEngine(conn, work=FailingWorkRepo(conn))

    with pytest.raises(RuntimeError, match="simulated"):
        engine.start(task.id, now=T0)

    assert engine.open_session_for(task.id) is None


def test_sibling_tasks_can_run_in_parallel(
    engine: TimerEngine, task: Task, other_task: Task
) -> None:
    with time_machine.travel(T0, tick=False):
        first = engine.start(task.id)
        second = engine.start(other_task.id)
        assert first.is_open and second.is_open
        assert len(engine.open_sessions()) == 2


def test_child_start_autopauses_ancestor(conn, engine: TimerEngine) -> None:
    parent = TaskRepo(conn).create(LIST_FAVORITES_ID, "English")
    child = TaskRepo(conn).create(LIST_FAVORITES_ID, "Grammar")
    TaskRepo(conn).set_parent(child.id, parent.id)

    with time_machine.travel(T0, tick=False):
        engine.start(parent.id)
        engine.start(child.id)
        assert engine.open_session_for(parent.id) is None
        parent_work = WorkRepo(conn).get(parent.id)
        assert parent_work is not None
        assert parent_work.state is WorkState.PAUSED
        assert engine.open_session_for(child.id) is not None


def test_cannot_start_ancestor_while_descendant_running(conn, engine: TimerEngine) -> None:
    parent = TaskRepo(conn).create(LIST_FAVORITES_ID, "English")
    child = TaskRepo(conn).create(LIST_FAVORITES_ID, "Grammar")
    TaskRepo(conn).set_parent(child.id, parent.id)

    with time_machine.travel(T0, tick=False):
        engine.start(child.id)
        with pytest.raises(HierarchyConflictError):
            engine.start(parent.id)


def test_stop_removes_from_work(engine: TimerEngine, task: Task, conn) -> None:
    with time_machine.travel(T0, tick=False):
        engine.start(task.id)
        engine.pause(task.id)
        assert WorkRepo(conn).get(task.id) is not None
        engine.stop(task.id)
        assert WorkRepo(conn).get(task.id) is None


def test_crash_recovery_uses_last_seen(engine: TimerEngine, task: Task, conn) -> None:
    with time_machine.travel(T0, tick=False) as clock:
        engine.start(task.id)
        clock.shift(timedelta(seconds=10))
        engine.heartbeat()
        clock.shift(timedelta(seconds=10))
        engine.heartbeat()
        last_seen = T0 + timedelta(seconds=20)

        recovered_engine = TimerEngine(conn)
        recovered = recovered_engine.recover_crash()
        assert len(recovered) == 1
        assert recovered[0].end_reason == EndReason.CRASH_RECOVERED
        assert recovered[0].ended_at == last_seen
        assert recovered_engine.open_sessions() == []
        recovered_work = WorkRepo(conn).get(task.id)
        assert recovered_work is not None
        assert recovered_work.state is WorkState.PAUSED


def test_mode_switch_mid_session(engine: TimerEngine, task: Task) -> None:
    with time_machine.travel(T0, tick=False) as clock:
        session = engine.start(task.id)
        assert session.target_seconds is None

        clock.shift(timedelta(seconds=100))
        updated = engine.set_mode(task.id, countdown_duration=600)
        assert updated.target_seconds == 700

        clock.shift(timedelta(seconds=50))
        active = engine.open_session_for(task.id)
        assert active is not None and active.target_seconds is not None
        assert active.target_seconds - engine.elapsed_seconds(active) == 550

        stopwatch = engine.set_mode(task.id, target_seconds=None)
        assert stopwatch.target_seconds is None


def test_sleep_clock_jump_forward(engine: TimerEngine, task: Task) -> None:
    with time_machine.travel(T0, tick=False) as clock:
        engine.start(task.id)
        clock.shift(timedelta(seconds=10))
        engine.heartbeat()
        clock.shift(timedelta(hours=8))
        engine.heartbeat()

        active = engine.open_session_for(task.id)
        assert active is not None
        assert engine.elapsed_seconds(active) == int(timedelta(hours=8, seconds=10).total_seconds())
        engine.stop(task.id)


def test_stats_and_rollup(conn, engine: TimerEngine) -> None:
    parent = TaskRepo(conn).create(LIST_FAVORITES_ID, "English")
    child = TaskRepo(conn).create(LIST_FAVORITES_ID, "Grammar")
    TaskRepo(conn).set_parent(child.id, parent.id)

    with time_machine.travel(T0, tick=False) as clock:
        engine.start(child.id)
        clock.shift(timedelta(seconds=40))
        engine.stop(child.id)
        engine.start(parent.id)
        clock.shift(timedelta(seconds=20))
        engine.stop(parent.id)

    assert engine.task_elapsed_seconds(child.id) == 40
    assert engine.task_elapsed_seconds(parent.id) == 20
    assert engine.task_rollup_seconds(parent.id) == 60

    stats = StatsRepo(conn)
    day = T0.date()
    child_stat = stats.get(child.id, day)
    assert child_stat is not None
    assert child_stat.total_seconds == 40
    stats.rebuild_from_sessions()
    rebuilt = stats.get(child.id, day)
    assert rebuilt is not None
    assert rebuilt.total_seconds == 40
