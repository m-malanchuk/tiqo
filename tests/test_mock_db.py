"""Mock DB factory tests."""

from __future__ import annotations

from app.domain.models import LIST_FAVORITES_ID
from app.storage.list_repo import ListRepo
from app.storage.task_repo import TaskRepo

from tests.support.db import make_db, seed_demo


def test_make_db_has_system_lists_only() -> None:
    conn = make_db()
    lists = ListRepo(conn).list_all()
    assert len(lists) == 4
    assert TaskRepo(conn).list_by_list(LIST_FAVORITES_ID) == []


def test_seed_demo_creates_tasks_and_session() -> None:
    seed = seed_demo()
    favorites_tasks = TaskRepo(seed.conn).list_by_list(LIST_FAVORITES_ID)
    assert {task.title for task in favorites_tasks} == {"Код", "Ревью"}
    assert seed.tasks["meeting"].list_id == seed.work.id
    assert len(ListRepo(seed.conn).list_all()) == 5  # 4 system + Работа
    assert seed.tasks["coding"].description == "Основная разработка"
