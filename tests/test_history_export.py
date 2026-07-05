"""Flat CSV export of the current completion-history records."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta

from app.domain.models import LIST_FAVORITES_ID, TaskKind
from app.services.history_export import HistoryExporter
from app.services.task_service import TaskService
from app.services.timer_engine import TimerEngine
from app.storage.completion_repo import CompletionRepo
from app.storage.task_repo import TaskRepo

from tests.support.db import make_db


def test_history_export_keeps_raw_session_and_checklist_fields(tmp_path) -> None:
    conn = make_db()
    tasks = TaskRepo(conn)
    timed = tasks.create(LIST_FAVORITES_ID, "Focus")
    checklist = tasks.create(LIST_FAVORITES_ID, "Send invoice", kind=TaskKind.CHECKLIST)
    engine = TimerEngine(conn)
    started = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
    engine.start(timed.id, now=started, use_task_default=False)
    engine.stop(timed.id, now=started + timedelta(seconds=45))
    TaskService(conn).complete_checklist(checklist.id, now=started)

    records = CompletionRepo(conn).list_all()
    path = HistoryExporter(conn).export(tmp_path / "tiqo-export.csv", records)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert {row["task_title"] for row in rows} == {"Focus", "Send invoice"}
    timed_row = next(row for row in rows if row["task_title"] == "Focus")
    assert timed_row["session_id"]
    assert timed_row["session_mode"] == "stopwatch"
    assert timed_row["session_target_seconds"] == ""
    assert timed_row["duration_seconds"] == "45"
    assert json.loads(timed_row["intervals"])
    binary_row = next(row for row in rows if row["task_title"] == "Send invoice")
    assert binary_row["session_id"] == ""
    assert binary_row["duration_seconds"] == ""
    assert json.loads(binary_row["intervals"]) == []
