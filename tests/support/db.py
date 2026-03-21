"""Mock / seeded in-memory SQLite for tests."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.domain.models import (
    LIST_FAVORITES_ID,
    LIST_IN_WORK_ID,
    LIST_TODAY_ID,
    EndReason,
    Task,
    TaskList,
)
from app.storage.db import open_memory_database
from app.storage.list_repo import ListRepo
from app.storage.session_repo import SessionRepo
from app.storage.task_repo import TaskRepo


@dataclass(frozen=True, slots=True)
class SeedResult:
    conn: sqlite3.Connection
    favorites: TaskList
    today: TaskList
    in_work: TaskList
    work: TaskList
    tasks: dict[str, Task]


def make_db() -> sqlite3.Connection:
    return open_memory_database()


def seed_demo(
    conn: sqlite3.Connection | None = None,
    *,
    now: datetime | None = None,
) -> SeedResult:
    connection = conn or make_db()
    stamp = now or datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

    lists = ListRepo(connection)
    tasks = TaskRepo(connection)
    sessions = SessionRepo(connection)

    favorites = lists.get(LIST_FAVORITES_ID)
    today = lists.get(LIST_TODAY_ID)
    in_work = lists.get(LIST_IN_WORK_ID)
    assert favorites is not None and today is not None and in_work is not None

    work = lists.create("Работа", position=3)

    coding = tasks.create(
        LIST_FAVORITES_ID,
        "Код",
        description="Основная разработка",
        is_favorite=True,
        created_at=stamp,
    )
    review = tasks.create(LIST_FAVORITES_ID, "Ревью", is_favorite=True, created_at=stamp)
    meeting = tasks.create(work.id, "Стендап", created_at=stamp)

    started = stamp - timedelta(minutes=30)
    ended = started + timedelta(minutes=25)
    open_session = sessions.create(
        coding.id, started_at=started, target_seconds=None, note="фича X"
    )
    sessions.close(open_session.id, ended_at=ended, end_reason=EndReason.STOPPED)

    return SeedResult(
        conn=connection,
        favorites=favorites,
        today=today,
        in_work=in_work,
        work=work,
        tasks={"coding": coding, "review": review, "meeting": meeting},
    )
