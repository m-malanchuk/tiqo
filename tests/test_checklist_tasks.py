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
    assert task.prompt_completion_note is False


def test_checklist_execution_records_event_without_mutating_task() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    task = tasks.create(1, "Send invoice", kind=TaskKind.CHECKLIST)
    service = TaskService(conn)

    completed = service.complete_checklist(task.id, note="Paid online", now=T0)
    assert completed.completed_at == T0
    assert completed.note == "Paid online"
    events = CompletionRepo(conn).list_for_task(task.id)
    assert len(events) == 1
    assert events[0].kind is CompletionKind.CHECKLIST
    assert events[0].session_id is None

    unchanged = tasks.get(task.id)
    assert unchanged is not None
    assert unchanged.prompt_completion_note is False
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


def test_switching_kind_clears_checklist_prompt_setting() -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    task = tasks.create(1, "Send invoice", kind=TaskKind.CHECKLIST)
    tasks.update(task.id, prompt_completion_note=True)
    checklist = tasks.get(task.id)
    assert checklist is not None and checklist.prompt_completion_note is True

    tasks.update(task.id, kind=TaskKind.TIMED)
    timed = tasks.get(task.id)
    assert timed is not None and timed.kind is TaskKind.TIMED
    assert timed.prompt_completion_note is False

    tasks.update(task.id, kind=TaskKind.CHECKLIST)
    checklist = tasks.get(task.id)
    assert checklist is not None and checklist.prompt_completion_note is False


def test_timed_task_cannot_create_checklist_execution() -> None:
    conn = make_db()
    task = TaskRepo(conn).create(1, "Focus")

    with pytest.raises(ValueError):
        TaskService(conn).complete_checklist(task.id, now=T0)
