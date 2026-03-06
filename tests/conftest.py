"""Shared fixtures for in-memory SQLite tests."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from app.domain.models import LIST_FAVORITES_ID, Task
from app.services.timer_engine import TimerEngine
from app.storage.task_repo import TaskRepo

from tests.support.db import make_db


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    connection = make_db()
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def engine(conn: sqlite3.Connection) -> TimerEngine:
    return TimerEngine(conn)


@pytest.fixture
def task(conn: sqlite3.Connection) -> Task:
    return TaskRepo(conn).create(LIST_FAVORITES_ID, "Write code")


@pytest.fixture
def other_task(conn: sqlite3.Connection) -> Task:
    return TaskRepo(conn).create(LIST_FAVORITES_ID, "Review PR")
