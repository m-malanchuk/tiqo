"""Calendar assignments and editable completion snapshots."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import time_machine
from app.application.task_presentation import seed_tasks_for_list
from app.domain.models import LIST_FAVORITES_ID, LIST_TODAY_ID, TaskKind, TimerMode
from app.services.task_service import TaskService
from app.services.timer_engine import TimerEngine
from app.storage.assignment_repo import AssignmentRepo
from app.storage.completion_repo import CompletionRepo
from app.storage.list_repo import ListRepo
from app.storage.recurrence_repo import RecurrenceRepo
from app.storage.session_repo import SessionRepo
from app.storage.task_repo import TaskRepo
from app.storage.work_repo import WorkRepo

from tests.support.db import make_db

T0 = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)


def test_manual_assignment_is_date_specific_and_completed_today_disappears() -> None:
    conn = make_db()
    task = TaskRepo(conn).create(
        LIST_FAVORITES_ID, "Pay bill", kind=TaskKind.CHECKLIST, is_favorite=True
    )
    assignments = AssignmentRepo(conn)
    assignments.assign(task.id, T0.date())
    completions = CompletionRepo(conn)
    with time_machine.travel(T0, tick=False):
        seed = seed_tasks_for_list(
            selected_list_id=LIST_TODAY_ID,
            lists_repo=ListRepo(conn),
            tasks_repo=TaskRepo(conn),
            work_repo=WorkRepo(conn),
            recurrence_repo=RecurrenceRepo(conn),
            assignment_repo=assignments,
            completion_repo=completions,
        )
        assert [row.id for row in seed] == [task.id]
        TaskService(conn).complete_checklist(task.id, now=T0)
        seed_after = seed_tasks_for_list(
            selected_list_id=LIST_TODAY_ID,
            lists_repo=ListRepo(conn),
            tasks_repo=TaskRepo(conn),
            work_repo=WorkRepo(conn),
            recurrence_repo=RecurrenceRepo(conn),
            assignment_repo=assignments,
            completion_repo=completions,
        )
        assert seed_after == []
    with time_machine.travel(T0 + timedelta(days=1), tick=False):
        seed_tomorrow = seed_tasks_for_list(
            selected_list_id=LIST_TODAY_ID,
            lists_repo=ListRepo(conn),
            tasks_repo=TaskRepo(conn),
            work_repo=WorkRepo(conn),
            recurrence_repo=RecurrenceRepo(conn),
            assignment_repo=assignments,
            completion_repo=completions,
        )
        assert seed_tomorrow == []


@pytest.mark.parametrize("mode", [TimerMode.STOPWATCH, TimerMode.COUNTDOWN])
def test_timed_stop_removes_today_task_but_pause_does_not(mode: TimerMode) -> None:
    conn = make_db()
    task = TaskRepo(conn).create(
        LIST_FAVORITES_ID,
        "Timed task",
        default_mode=mode,
        default_target_seconds=60 if mode is TimerMode.COUNTDOWN else None,
    )
    assignments = AssignmentRepo(conn)
    assignments.assign(task.id, T0.date())
    completions = CompletionRepo(conn)
    engine = TimerEngine(conn)

    def today_ids() -> list[int]:
        return [
            row.id
            for row in seed_tasks_for_list(
                selected_list_id=LIST_TODAY_ID,
                lists_repo=ListRepo(conn),
                tasks_repo=TaskRepo(conn),
                work_repo=WorkRepo(conn),
                recurrence_repo=RecurrenceRepo(conn),
                assignment_repo=assignments,
                completion_repo=completions,
            )
        ]

    with time_machine.travel(T0, tick=False) as clock:
        engine.start(task.id, use_task_default=True)
        clock.shift(timedelta(seconds=10))
        engine.pause(task.id)
        assert today_ids() == [task.id]

        engine.resume(task.id)
        clock.shift(timedelta(seconds=10))
        engine.stop(task.id)
        assert today_ids() == []


def test_completion_history_edit_does_not_change_source_session() -> None:
    conn = make_db()
    task = TaskRepo(conn).create(LIST_FAVORITES_ID, "Focus")
    engine = TimerEngine(conn)
    with time_machine.travel(T0, tick=False) as clock:
        session = engine.start(task.id)
        clock.shift(timedelta(seconds=30))
        engine.stop(task.id)
    history = CompletionRepo(conn)
    completion = history.get_for_session(session.id)
    assert completion is not None
    original = history.list_intervals(completion.id)
    assert original
    source_intervals = SessionRepo(conn).list_intervals(session.id)
    assert source_intervals
    edited_start = T0 - timedelta(minutes=5)
    edited_end = T0 - timedelta(minutes=4)
    history.replace_intervals(completion.id, [(edited_start, edited_end)])
    history.update(completion.id, completed_at=edited_end, note="corrected")
    refreshed = history.get(completion.id)
    assert refreshed is not None
    assert refreshed.duration_seconds == 60
    source = engine.session_for_task(task.id)
    assert source is None
    assert history.list_intervals(completion.id)[0].started_at == edited_start
    assert SessionRepo(conn).list_intervals(session.id) == source_intervals


def test_completion_date_follows_edited_end_across_midnight() -> None:
    conn = make_db()
    task = TaskRepo(conn).create(LIST_FAVORITES_ID, "Late focus")
    engine = TimerEngine(conn)
    started = T0.replace(hour=23, minute=59)
    ended = started + timedelta(minutes=3)
    engine.start(task.id, now=started, use_task_default=False)
    engine.stop(task.id, now=ended)

    history = CompletionRepo(conn)
    completion = history.get_for_session(SessionRepo(conn).list_for_task(task.id)[0].id)
    assert completion is not None
    assert completion.completion_date == ended.astimezone().date()

    moved_end = ended + timedelta(days=2)
    history.replace_intervals(completion.id, [(started, moved_end)])
    history.update(completion.id, completed_at=moved_end)
    moved = history.get(completion.id)
    assert moved is not None
    assert moved.completion_date == moved_end.astimezone().date()
