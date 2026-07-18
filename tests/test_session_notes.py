"""Session notes remain on one session across pause/resume and are editable."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.models import LIST_FAVORITES_ID
from app.services.timer_engine import TimerEngine
from app.storage.session_repo import SessionRepo
from app.storage.task_repo import TaskRepo

from tests.support.db import make_db


def test_open_session_note_can_change_while_paused() -> None:
    conn = make_db()
    task = TaskRepo(conn).create(LIST_FAVORITES_ID, "Focus")
    engine = TimerEngine(conn)
    start = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)

    session = engine.start(task.id, now=start, note="first part")
    engine.pause(task.id, now=start + timedelta(minutes=30))
    updated = engine.update_note(task.id, "first part; second part planned")
    resumed = engine.resume(task.id, now=start + timedelta(hours=1))

    assert updated.id == session.id == resumed.id
    stored = SessionRepo(conn).get(session.id)
    assert stored is not None
    assert stored.note == "first part; second part planned"
