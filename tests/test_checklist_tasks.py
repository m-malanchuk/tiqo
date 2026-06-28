"""Binary checklist task behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.models import CompletionKind, TaskKind, TimerMode
from app.services.task_service import TaskService
from app.services.timer_engine import ChecklistTaskError, TimerEngine
from app.storage.completion_repo import CompletionRepo
from app.storage.task_repo import TaskRepo

from tests.support.db import make_db

T0 = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)


def test_checklist_task_has_no_timer_defaults() -> None:
    conn = make_db()
    task = TaskRepo(conn).create(1, "Send invoice", kind=TaskKind.CHECKLIST)

    assert task.kind is TaskKind.CHECKLIST
    assert task.default_mode is TimerMode.STOPWATCH
    assert task.default_target_seconds is None
    assert task.is_completed is False
    assert task.completed_at is None


def test_mark_checklist_done_is_idempotent_and_records_event() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    task = tasks.create(1, "Send invoice", kind=TaskKind.CHECKLIST)
    service = TaskService(conn)

    completed = service.set_checklist_done(task.id, now=T0)
    assert completed.is_completed is True
    assert completed.completed_at == T0
    events = CompletionRepo(conn).list_for_task(task.id)
    assert len(events) == 1
    assert events[0].kind is CompletionKind.CHECKLIST
    assert events[0].session_id is None

    same = service.set_checklist_done(task.id, now=T0 + timedelta(minutes=1))
    assert same.completed_at == T0
    assert len(CompletionRepo(conn).list_for_task(task.id)) == 1


def test_unmark_checklist_keeps_history_but_clears_current_state() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    task = tasks.create(1, "Send invoice", kind=TaskKind.CHECKLIST)
    service = TaskService(conn)

    service.set_checklist_done(task.id, now=T0)
    undone = service.set_checklist_done(task.id, False, now=T0 + timedelta(minutes=1))

    assert undone.is_completed is False
    assert undone.completed_at is None
    assert len(CompletionRepo(conn).list_for_task(task.id)) == 1


def test_repeated_checklist_execution_creates_separate_history_rows() -> None:
    conn = make_db()
    task = TaskRepo(conn).create(1, "Send invoice", kind=TaskKind.CHECKLIST)
    service = TaskService(conn)

    service.complete_checklist(task.id, now=T0)
    service.complete_checklist(task.id, now=T0 + timedelta(days=1))

    events = CompletionRepo(conn).list_for_task(task.id)
    assert len(events) == 2
    assert [event.completion_date for event in events] == [
        T0.date(),
        (T0 + timedelta(days=1)).date(),
    ]


def test_checklist_cannot_start_timer_session() -> None:
    conn = make_db()
    task = TaskRepo(conn).create(1, "Send invoice", kind=TaskKind.CHECKLIST)

    with pytest.raises(ChecklistTaskError):
        TimerEngine(conn).start(task.id)


def test_timed_task_defaults_to_timed_kind() -> None:
    conn = make_db()
    task = TaskRepo(conn).create(1, "Focus")
    assert task.kind is TaskKind.TIMED


def test_switching_kind_clears_stale_checklist_state() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    task = tasks.create(1, "Send invoice", kind=TaskKind.CHECKLIST)
    service = TaskService(conn)
    service.set_checklist_done(task.id, now=T0)

    tasks.update(task.id, kind=TaskKind.TIMED)
    timed = tasks.get(task.id)
    assert timed is not None and timed.kind is TaskKind.TIMED
    assert timed.is_completed is False
    assert timed.completed_at is None

    tasks.update(task.id, kind=TaskKind.CHECKLIST)
    checklist = tasks.get(task.id)
    assert checklist is not None and not checklist.is_completed
