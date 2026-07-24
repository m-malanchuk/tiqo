"""Showcase DB smoke test."""

from __future__ import annotations

from app.application.task_presentation import build_work_rows
from app.dev.showcase_db import seed_showcase
from app.domain.models import WorkState
from app.services.timer_engine import TimerEngine
from app.storage.completion_repo import CompletionRepo
from app.storage.session_repo import SessionRepo
from app.storage.task_repo import TaskRepo
from app.storage.work_repo import WorkRepo

from tests.support.db import make_db


def test_seed_showcase_has_hierarchy_and_work() -> None:
    conn = make_db()
    seed_showcase(conn)
    titles = {t.title: t for t in TaskRepo(conn).list_all()}
    assert "Английский" in titles
    assert "Грамматика" in titles
    assert "Лексика" in titles
    assert "Помодоро" in titles
    assert CompletionRepo(conn).count() == 8
    english = titles["Английский"]
    grammar = titles["Грамматика"]
    pomodoro = titles["Помодоро"]
    assert TaskRepo(conn).parent_of(grammar.id) == english.id

    work_by_task = {w.task_id: w for w in WorkRepo(conn).list_all()}
    assert english.id in work_by_task
    assert work_by_task[english.id].state is WorkState.PAUSED
    assert work_by_task[grammar.id].state is WorkState.RUNNING
    assert work_by_task[pomodoro.id].state is WorkState.RUNNING

    open_sessions = SessionRepo(conn).list_open()
    pomodoro_open = next(s for s in open_sessions if s.task_id == pomodoro.id)
    assert pomodoro_open.target_seconds == 25 * 60

    rows = build_work_rows(
        engine=TimerEngine(conn),
        work_repo=WorkRepo(conn),
        tasks_repo=TaskRepo(conn),
    )
    by_id = {r.task_id: r for r in rows}
    assert by_id[english.id].blocked_by_descendant is True
    assert by_id[grammar.id].blocked_by_descendant is False
    assert by_id[pomodoro.id].is_countdown is True
    progress = by_id[pomodoro.id].progress
    assert progress is not None
    assert 0 < progress < 1
