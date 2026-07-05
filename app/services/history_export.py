"""Export the completed-history ledger as a flat, machine-readable CSV."""

from __future__ import annotations

import csv
import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from app.domain.models import TaskCompletion
from app.domain.timeutil import dt_to_db
from app.storage.completion_repo import CompletionRepo
from app.storage.session_repo import SessionRepo
from app.storage.task_repo import TaskRepo

CSV_FIELDS = (
    "completion_id",
    "task_id",
    "task_title",
    "task_kind",
    "session_id",
    "completion_kind",
    "session_mode",
    "session_target_seconds",
    "completion_date",
    "completed_at",
    "started_at",
    "ended_at",
    "duration_seconds",
    "note",
    "intervals",
)


class HistoryExporter:
    """Write completion rows without changing the source task or session."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._completions = CompletionRepo(conn)
        self._sessions = SessionRepo(conn)
        self._tasks = TaskRepo(conn)

    def export(self, path: Path, completions: Iterable[TaskCompletion]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
            writer.writeheader()
            for completion in completions:
                task = self._tasks.get(completion.task_id)
                session = (
                    self._sessions.get(completion.session_id)
                    if completion.session_id is not None
                    else None
                )
                intervals = [
                    {
                        "started_at": dt_to_db(interval.started_at),
                        "ended_at": dt_to_db(interval.ended_at),
                    }
                    for interval in self._completions.list_intervals(completion.id)
                ]
                writer.writerow(
                    {
                        "completion_id": completion.id,
                        "task_id": completion.task_id,
                        "task_title": task.title if task is not None else f"#{completion.task_id}",
                        "task_kind": task.kind.value if task is not None else "timed",
                        "session_id": ""
                        if completion.session_id is None
                        else completion.session_id,
                        "completion_kind": completion.kind.value,
                        "session_mode": (
                            ""
                            if session is None
                            else (
                                "countdown" if session.target_seconds is not None else "stopwatch"
                            )
                        ),
                        "session_target_seconds": (
                            ""
                            if session is None or session.target_seconds is None
                            else session.target_seconds
                        ),
                        "completion_date": completion.completion_date.isoformat(),
                        "completed_at": dt_to_db(completion.completed_at),
                        "started_at": (
                            "" if completion.started_at is None else dt_to_db(completion.started_at)
                        ),
                        "ended_at": (
                            "" if completion.ended_at is None else dt_to_db(completion.ended_at)
                        ),
                        "duration_seconds": (
                            ""
                            if completion.duration_seconds is None
                            else completion.duration_seconds
                        ),
                        "note": completion.note,
                        "intervals": json.dumps(
                            intervals, ensure_ascii=False, separators=(",", ":")
                        ),
                    }
                )
        return path
