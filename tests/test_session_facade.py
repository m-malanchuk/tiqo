"""SessionFacade IPC surface (no QML)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import time_machine
from app.api.session_facade import SessionFacade
from app.domain.models import LIST_FAVORITES_ID, LIST_IN_WORK_ID, TimerMode
from app.storage.assignment_repo import AssignmentRepo
from app.storage.task_repo import TaskRepo
from PySide6.QtCore import QCoreApplication

from tests.support.db import make_db

T0 = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def qapp() -> QCoreApplication:
    existing = QCoreApplication.instance()
    if existing is not None:
        return existing
    return QCoreApplication([])


def test_facade_list_work_and_pause(qapp: QCoreApplication) -> None:
    _ = qapp
    conn = make_db()
    task = TaskRepo(conn).create(
        LIST_FAVORITES_ID,
        "Focus",
        default_mode=TimerMode.STOPWATCH,
    )
    facade = SessionFacade(conn)
    with time_machine.travel(T0, tick=False):
        facade.engine.start(task.id, use_task_default=True)
        rows = facade.list_work()
        assert len(rows) == 1
        assert rows[0].task_id == task.id
        assert rows[0].state == "running"
        assert rows[0].can_pause is True
        facade.pause(task.id)
        paused = facade.list_work()
        assert paused[0].state == "paused"
        assert paused[0].can_start is True


def test_blocked_ancestor_flag_and_can_start(qapp: QCoreApplication) -> None:
    _ = qapp
    conn = make_db()
    tasks = TaskRepo(conn)
    parent = tasks.create(LIST_FAVORITES_ID, "Parent", default_mode=TimerMode.STOPWATCH)
    child = tasks.create(LIST_FAVORITES_ID, "Child", default_mode=TimerMode.STOPWATCH)
    from app.services.task_service import TaskService

    TaskService(conn).set_parent(child.id, parent.id)
    facade = SessionFacade(conn)
    with time_machine.travel(T0, tick=False):
        facade.engine.start(parent.id, use_task_default=True)
        facade.engine.start(child.id, use_task_default=True)
        rows = {r.task_id: r for r in facade.list_work()}
        assert rows[parent.id].state == "paused"
        assert rows[parent.id].blocked_by_descendant is True
        assert rows[parent.id].can_start is False
        assert rows[child.id].state == "running"
        assert rows[child.id].blocked_by_descendant is False


def test_list_lists_and_tasks_and_today_stats(qapp: QCoreApplication) -> None:
    _ = qapp
    conn = make_db()
    from app.dev.showcase_db import seed_showcase
    from app.domain.models import LIST_TODAY_ID

    seed_showcase(conn)
    facade = SessionFacade(conn)
    lists = {row.list_id: row for row in facade.list_lists()}
    assert LIST_TODAY_ID in lists
    assert LIST_IN_WORK_ID in lists

    today_tasks = facade.list_tasks(LIST_TODAY_ID)
    assert len(today_tasks) >= 1
    assert all(not t.has_children for t in today_tasks)

    work_tasks = facade.list_tasks(LIST_IN_WORK_ID)
    assert len(work_tasks) >= 1
    # «В работе» = current roster only (may include parents).
    work_ids = {t.task_id for t in work_tasks}
    assert work_ids == {r.task_id for r in facade.list_work()}

    stats = facade.today_stats()
    assert stats.total >= 1
    assert stats.done == 0  # showcase history is yesterday+, not today

    work_prog = facade.list_progress(LIST_IN_WORK_ID)
    assert work_prog.total == len(work_tasks)
    assert work_prog.done == 0

    fav_tasks = facade.list_tasks(LIST_FAVORITES_ID)
    fav_prog = facade.list_progress(LIST_FAVORITES_ID)
    assert fav_prog.total == len(fav_tasks)
    assert fav_prog.done == 0
    assert all(not t.has_children for t in fav_tasks)


def test_list_progress_counts_favorite_subtask_leaves(qapp: QCoreApplication) -> None:
    """Favorited parent → leaf children; +1 per Stop; same leaf can count twice."""
    _ = qapp
    conn = make_db()
    tasks = TaskRepo(conn)
    parent = tasks.create(
        LIST_FAVORITES_ID,
        "Parent",
        default_mode=TimerMode.STOPWATCH,
        is_favorite=True,
    )
    child = tasks.create(LIST_FAVORITES_ID, "Child", default_mode=TimerMode.STOPWATCH)
    from app.services.task_service import TaskService

    TaskService(conn).set_parent(child.id, parent.id)

    facade = SessionFacade(conn)
    before = facade.list_progress(LIST_FAVORITES_ID)
    assert before.total >= 1
    assert child.id in {t.task_id for t in facade.list_tasks(LIST_FAVORITES_ID)}
    assert before.done == 0

    with time_machine.travel(T0, tick=False):
        facade.engine.start(child.id, use_task_default=True)
        facade.pause(child.id)
        assert facade.list_progress(LIST_FAVORITES_ID).done == 0
        facade.engine.start(child.id, use_task_default=True)
        facade.stop(child.id)
        assert facade.list_progress(LIST_FAVORITES_ID).done == 1
        # Same task again → counter keeps growing.
        facade.engine.start(child.id, use_task_default=True)
        facade.stop(child.id)
        after = facade.list_progress(LIST_FAVORITES_ID)
    assert after.done == 2
    assert after.total == before.total


def test_today_progress_counts_completed_timed_assignment(qapp: QCoreApplication) -> None:
    _ = qapp
    conn = make_db()
    task = TaskRepo(conn).create(LIST_FAVORITES_ID, "Today focus", is_favorite=True)
    AssignmentRepo(conn).assign(task.id, T0.date())
    facade = SessionFacade(conn)

    with time_machine.travel(T0, tick=False):
        assert facade.today_stats().done == 0
        facade.engine.start(task.id, use_task_default=False)
        facade.engine.stop(task.id)
        stats = facade.today_stats()

    assert stats.done == 1
    assert stats.total == 1


def test_in_work_stop_removes_from_list_tasks(qapp: QCoreApplication) -> None:
    """Stop drops the task from «В работе» ListTasks (not Favorites-style stay)."""
    _ = qapp
    conn = make_db()
    task = TaskRepo(conn).create(
        LIST_FAVORITES_ID,
        "Focus",
        default_mode=TimerMode.STOPWATCH,
        is_favorite=True,
    )
    facade = SessionFacade(conn)
    with time_machine.travel(T0, tick=False):
        facade.engine.start(task.id, use_task_default=True)
        assert task.id in {t.task_id for t in facade.list_tasks(LIST_IN_WORK_ID)}
        facade.stop(task.id)
        assert task.id not in {t.task_id for t in facade.list_tasks(LIST_IN_WORK_ID)}
        # Favorites keeps the task visible after Stop.
        assert task.id in {t.task_id for t in facade.list_tasks(LIST_FAVORITES_ID)}
